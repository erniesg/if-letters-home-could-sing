"""Idempotent orchestration from native reply submit to reviewed document."""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from .codex_app_server import CodexLetterResult, CodexReviewResult
from .contracts import MAX_LETTER, Letter, parse_letter_text


STREAM_CHARACTER = re.compile(r"[\u3400-\u9fff，。！？；：“”‘’、—…（）《》\n\r ]")


class TabletDocuments(Protocol):
    def export_pdf(self, document_id: str) -> bytes: ...

    def upload_pdf(self, payload: bytes, *, filename: str) -> str: ...


class ReplyRenderer(Protocol):
    def render_reply_page(self, source_pdf: bytes, *, page_index: int, session_id: str) -> Path: ...

    def build_reviewed_packet(
        self,
        source_pdf: bytes,
        review,
        *,
        profile_id: str,
        incoming_letter: Letter,
    ) -> tuple[bytes, int]: ...


class ReplyReviewer(Protocol):
    def review_reply(
        self,
        *,
        session_id: str,
        reply_image: Path,
        conversation_context: str,
    ) -> CodexReviewResult: ...


class LetterGenerator(Protocol):
    def generate_letter(
        self,
        *,
        session_id: str,
        conversation_context: str,
        on_delta: Callable[[str], None],
    ) -> CodexLetterResult: ...


class SessionRegistry:
    """Ephemeral private context plus bounded fictional text streaming state."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path).expanduser() if path else None
        self._context: dict[str, str] = {}
        self._state: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        if self.path and self.path.is_file():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    for session_id, raw in loaded.items():
                        if not isinstance(session_id, str) or not isinstance(raw, dict):
                            continue
                        letter = parse_letter_text(raw.get("text"))
                        thread_id = raw.get("thread_id")
                        if not isinstance(thread_id, str) or not thread_id:
                            continue
                        self._state[session_id] = {
                            "status": "ready",
                            "version": max(1, int(raw.get("version", 1))),
                            "text": letter.body,
                            "letter": letter,
                            "thread_id": thread_id,
                        }
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                self._state = {}

    def _persist_ready(self) -> None:
        if not self.path:
            return
        payload = {
            session_id: {
                "status": "ready",
                "version": state["version"],
                "text": state["text"],
                "thread_id": state["thread_id"],
            }
            for session_id, state in self._state.items()
            if state.get("status") == "ready" and state.get("thread_id")
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix="sessions-",
            suffix=".json",
            dir=self.path.parent,
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def put(self, session_id: str, conversation_context: str) -> None:
        with self._lock:
            self._context[session_id] = conversation_context

    def get(self, session_id: str) -> str:
        with self._lock:
            return self._context.get(session_id, "")

    def begin(self, session_id: str, conversation_context: str) -> None:
        with self._lock:
            self._context[session_id] = conversation_context
            self._state[session_id] = {
                "status": "streaming",
                "version": 0,
                "text": "",
                "letter": None,
            }

    def append(self, session_id: str, delta: str) -> None:
        if not isinstance(delta, str) or not delta:
            return
        cleaned = "".join(STREAM_CHARACTER.findall(delta)).strip()
        if not cleaned:
            return
        with self._lock:
            state = self._state.get(session_id)
            if not state or state["status"] != "streaming":
                return
            remaining = max(0, MAX_LETTER - len(state["text"]))
            if remaining == 0:
                return
            state["text"] += cleaned[:remaining]
            state["version"] += 1

    def complete(self, session_id: str, letter: Letter, thread_id: str) -> None:
        with self._lock:
            state = self._state.get(session_id)
            if not state:
                raise RuntimeError("session_not_found")
            state.update(
                status="ready",
                version=state["version"] + 1,
                text=letter.body,
                letter=letter,
                thread_id=thread_id,
            )
            self._persist_ready()

    def fail(self, session_id: str, error_code: str = "incoming_letter_failed") -> None:
        with self._lock:
            state = self._state.get(session_id)
            if state:
                state.update(status="failed", version=state["version"] + 1, error=error_code)

    def public_state(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            state = self._state.get(session_id)
            if not state:
                raise ValueError("session_not_found")
            response = {
                "status": state["status"],
                "session_id": session_id,
                "version": state["version"],
                "text": state["text"],
            }
            if state.get("error"):
                response["error"] = state["error"]
            return response

    def letter(self, session_id: str) -> Letter:
        with self._lock:
            state = self._state.get(session_id)
            letter = state.get("letter") if state else None
            if not isinstance(letter, Letter):
                raise RuntimeError("incoming_letter_not_ready")
            return letter


class ReceiptStore:
    """Persist only idempotency identifiers, never participant content."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path).expanduser() if path else None
        self._receipts: dict[str, dict[str, Any]] = {}
        if self.path and self.path.is_file():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self._receipts = {
                        key: value
                        for key, value in loaded.items()
                        if isinstance(key, str) and isinstance(value, dict)
                    }
            except (OSError, json.JSONDecodeError):
                self._receipts = {}

    def get(self, session_id: str) -> dict[str, Any] | None:
        receipt = self._receipts.get(session_id)
        return dict(receipt) if receipt else None

    def put(self, session_id: str, receipt: Mapping[str, Any]) -> None:
        self._receipts[session_id] = dict(receipt)
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix="receipts-", suffix=".json", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(self._receipts, handle, sort_keys=True, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


class SessionStarter:
    def __init__(
        self,
        *,
        tablet: TabletDocuments,
        renderer,
        generator: LetterGenerator,
        registry: SessionRegistry,
        default_context: str,
        background: Callable[[Callable[[], None]], None] | None = None,
    ):
        self.tablet = tablet
        self.renderer = renderer
        self.generator = generator
        self.registry = registry
        self.default_context = default_context
        self.background = background or self._start_thread

    @staticmethod
    def _start_thread(work: Callable[[], None]) -> None:
        threading.Thread(target=work, name="letters-home-incoming", daemon=True).start()

    def start(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        profile_id = payload.get("profile_id", "ferrari_3.28.0.162")
        if profile_id not in {"ferrari_3.28.0.162", "chiappa_3.28.0.162"}:
            raise ValueError("invalid render profile")
        supplied_context = payload.get("conversation_context", "")
        if not isinstance(supplied_context, str) or len(supplied_context) > 4000:
            raise ValueError("invalid conversation context")
        conversation_context = supplied_context.strip() or self.default_context.strip()
        session_id = uuid.uuid4().hex
        packet = self.renderer.build_initial_packet(None, profile_id=profile_id)
        document_id = self.tablet.upload_pdf(
            packet,
            filename=f"Letters Home {session_id}.pdf",
        )
        self.registry.begin(session_id, conversation_context)

        def generate() -> None:
            try:
                result = self.generator.generate_letter(
                    session_id=session_id,
                    conversation_context=conversation_context,
                    on_delta=lambda delta: self.registry.append(session_id, delta),
                )
                self.registry.complete(session_id, result.letter, result.thread_id)
            except (OSError, RuntimeError, ValueError):
                self.registry.fail(session_id)

        self.background(generate)
        return {
            "status": "streaming",
            "session_id": session_id,
            "document_id": document_id,
        }


class SubmissionService:
    """Run one durable review per pseudonymous session id."""

    def __init__(
        self,
        *,
        tablet: TabletDocuments,
        renderer: ReplyRenderer,
        reviewer: ReplyReviewer,
        registry: SessionRegistry | None = None,
        receipts: ReceiptStore | None = None,
    ):
        self.tablet = tablet
        self.renderer = renderer
        self.reviewer = reviewer
        self.registry = registry or SessionRegistry()
        self.receipts = receipts or ReceiptStore()
        self._lock = threading.Lock()

    def _prepare_reply(self, *, document_id: str, page_index: int, session_id: str):
        transient_errors = {"remarkable_usb_unreachable", "reply_page_render_failed"}
        for attempt in range(3):
            try:
                source_pdf = self.tablet.export_pdf(document_id)
                reply_image = self.renderer.render_reply_page(
                    source_pdf,
                    page_index=page_index,
                    session_id=session_id,
                )
                return source_pdf, reply_image
            except RuntimeError as error:
                if str(error) not in transient_errors or attempt == 2:
                    raise
                time.sleep(attempt + 1)
        raise RuntimeError("reply_page_render_failed")

    def submit(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        required = (
            "session_id",
            "document_id",
            "reply_page_index",
            "profile_id",
            "conversation_context",
        )
        if not isinstance(payload, Mapping) or any(field not in payload for field in required):
            raise ValueError("submission is missing required fields")
        session_id = payload["session_id"]
        document_id = payload["document_id"]
        page_index = payload["reply_page_index"]
        profile_id = payload["profile_id"]
        conversation_context = payload["conversation_context"]
        if not isinstance(session_id, str) or not session_id or len(session_id) > 128:
            raise ValueError("invalid session id")
        if not isinstance(document_id, str) or not document_id:
            raise ValueError("invalid document id")
        if page_index != 1:
            raise ValueError("only the huipi page can be submitted")
        if profile_id not in {"ferrari_3.28.0.162", "chiappa_3.28.0.162"}:
            raise ValueError("invalid render profile")
        if not isinstance(conversation_context, str) or len(conversation_context) > 4000:
            raise ValueError("invalid conversation context")
        with self._lock:
            previous = self.receipts.get(session_id)
            if previous:
                return previous
            context = conversation_context.strip() or self.registry.get(session_id)
            source_pdf, reply_image = self._prepare_reply(
                document_id=document_id,
                page_index=page_index,
                session_id=session_id,
            )
            codex_result = self.reviewer.review_reply(
                session_id=session_id,
                reply_image=reply_image,
                conversation_context=context,
            )
            reviewed_pdf, review_page_index = self.renderer.build_reviewed_packet(
                source_pdf,
                codex_result.review,
                profile_id=profile_id,
                incoming_letter=self.registry.letter(session_id),
            )
            reviewed_document_id = self.tablet.upload_pdf(
                reviewed_pdf,
                filename=f"Letters Home Review {session_id}.pdf",
            )
            receipt = {
                "status": "reviewed",
                "session_id": session_id,
                "codex_thread_id": codex_result.thread_id,
                "document_id": reviewed_document_id,
                "review_page_index": review_page_index,
            }
            self.receipts.put(session_id, receipt)
            return receipt
