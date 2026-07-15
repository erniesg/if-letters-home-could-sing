"""Asynchronous orchestration for one stock Xochitl notebook encounter."""

from __future__ import annotations

import dataclasses
import re
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from .codex_app_server import CodexResponseTurnError, default_codex_command
from .contracts import MIN_NOTEBOOK_LETTER, Letter, parse_letter_text
from .notebook_session import NotebookSessionStore


FERRARI_PROFILE = "ferrari_3.28.0.162"
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class NotebookCoordinator:
    """Keep Xochitl in charge of pages while the Mac owns bounded AI state."""

    def __init__(
        self,
        *,
        store: NotebookSessionStore,
        tablet,
        renderer,
        generator,
        reviewer,
        default_context: str,
        background: Callable[[Callable[[], None]], None] | None = None,
        health_checks: Mapping[str, Callable[[], bool]] | None = None,
    ):
        self.store = store
        self.tablet = tablet
        self.renderer = renderer
        self.generator = generator
        self.reviewer = reviewer
        self.default_context = default_context.strip()
        self.background = background or self._start_thread
        self.health_checks = dict(
            health_checks
            or {
                "tablet_readable": self._tablet_readable,
                "renderer": self._renderer_ready,
                "codex": self._codex_ready,
            }
        )
        self._submit_lock = threading.Lock()
        self._retrying: set[str] = set()

    @staticmethod
    def _start_thread(work: Callable[[], None]) -> None:
        threading.Thread(target=work, name="letters-home-notebook", daemon=True).start()

    @staticmethod
    def _identifier(value: Any, field: str) -> str:
        if not isinstance(value, str) or _SAFE_ID.fullmatch(value) is None:
            raise ValueError(f"invalid {field}")
        return value

    @staticmethod
    def _profile(payload: Mapping[str, Any]) -> str:
        profile_id = payload.get("profile_id", FERRARI_PROFILE)
        if profile_id != FERRARI_PROFILE:
            raise ValueError("invalid render profile")
        return profile_id

    def start(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise ValueError("invalid start payload")
        self._profile(payload)
        supplied_context = payload.get("conversation_context", "")
        if not isinstance(supplied_context, str) or len(supplied_context) > 4000:
            raise ValueError("invalid conversation context")
        context = supplied_context.strip() or self.default_context
        session_id = self.store.begin(context)

        def generate() -> None:
            try:
                result = self.generator.generate_letter(
                    session_id=session_id,
                    conversation_context=context,
                    on_delta=lambda delta: self.store.append_incoming(session_id, delta),
                )
                letter = parse_letter_text(
                    result.letter.body,
                    minimum=MIN_NOTEBOOK_LETTER,
                )
                self.store.finish_incoming(session_id, final_text=letter.body)
                self.store.set_codex_task(
                    session_id,
                    thread_id=result.thread_id,
                    active_turn_id=None,
                )
            except (OSError, RuntimeError, TypeError, ValueError):
                self.store.fail(session_id, "incoming_letter_failed")

        self.background(generate)
        return {"status": "incoming", "session_id": session_id}

    def seed_state(self) -> dict[str, str]:
        return self.store.seed_state()

    def bind_seed(self, payload: Mapping[str, Any]) -> dict[str, str]:
        if not isinstance(payload, Mapping):
            raise ValueError("invalid seed payload")
        return self.store.bind_seed(
            document_id=self._identifier(
                payload.get("document_id"),
                "seed document id",
            ),
            incoming_page_id=self._identifier(
                payload.get("incoming_page_id"),
                "seed incoming page id",
            ),
            reply_page_id=self._identifier(
                payload.get("reply_page_id"),
                "seed reply page id",
            ),
        )

    def bind(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise ValueError("invalid bind payload")
        session_id = self._identifier(payload.get("session_id"), "session id")
        state = self.store.bind(
            session_id,
            document_id=self._identifier(payload.get("document_id"), "document id"),
            incoming_page_id=self._identifier(
                payload.get("incoming_page_id"),
                "incoming page id",
            ),
            reply_page_id=self._identifier(payload.get("reply_page_id"), "reply page id"),
        )
        return {"status": "bound", **state}

    def mark_first_ink(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise ValueError("invalid first ink payload")
        session_id = self._identifier(payload.get("session_id"), "session id")
        document_id = self._identifier(payload.get("document_id"), "document id")
        reply_page_id = self._identifier(payload.get("reply_page_id"), "reply page id")
        state = self.store.public_state(session_id)
        if (
            state["document_id"] != document_id
            or state["page_ids"].get("reply") != reply_page_id
        ):
            raise ValueError("notebook_binding_mismatch")
        observed_at = payload.get("observed_at")
        if observed_at is not None and (
            not isinstance(observed_at, (int, float)) or isinstance(observed_at, bool)
        ):
            raise ValueError("invalid first ink timestamp")
        return self.store.mark_first_ink(session_id, observed_at=observed_at)

    def _prepare_reply(
        self,
        *,
        document_id: str,
        page_index: int,
        session_id: str,
    ) -> Path:
        transient_errors = {"remarkable_usb_unreachable", "reply_page_render_failed"}
        for attempt in range(3):
            try:
                source_pdf = self.tablet.export_pdf(document_id)
                return self.renderer.render_reply_page(
                    source_pdf,
                    page_index=page_index,
                    session_id=session_id,
                )
            except RuntimeError as error:
                if str(error) not in transient_errors or attempt == 2:
                    raise
                time.sleep(attempt + 1)
        raise RuntimeError("reply_page_render_failed")

    @staticmethod
    def _review_public(review: Any) -> dict[str, Any]:
        if dataclasses.is_dataclass(review):
            payload = dataclasses.asdict(review)
        else:
            payload = {
                "summary": getattr(review, "summary"),
                "corrections": getattr(review, "corrections", []),
                "annotations": getattr(review, "annotations", []),
                "reflective_question": getattr(review, "reflective_question"),
            }
        payload.pop("schema_version", None)
        payload.pop("response_letter", None)
        return payload

    def _run_review(
        self,
        *,
        session_id: str,
        reply_image: Path,
        conversation_context: str,
    ) -> None:
        try:
            if hasattr(self.reviewer, "review_and_respond"):
                result = self.reviewer.review_and_respond(
                    session_id=session_id,
                    reply_image=reply_image,
                    conversation_context=conversation_context,
                    on_review=lambda thread_id, review: self.store.finish_review(
                        session_id,
                        self._review_public(review),
                    ),
                    on_response_delta=lambda delta: self.store.append_response(
                        session_id,
                        delta,
                    ),
                    on_turn_started=lambda phase, thread_id, turn_id: self.store.set_codex_task(
                        session_id,
                        thread_id=thread_id,
                        active_turn_id=turn_id,
                    ),
                )
                self.store.finish_response(
                    session_id,
                    final_text=result.response_letter.body,
                )
                return
            result = self.reviewer.review_reply(
                session_id=session_id,
                reply_image=reply_image,
                conversation_context=conversation_context,
            )
            self.store.finish_review(session_id, self._review_public(result.review))
            self.store.set_codex_task(
                session_id,
                thread_id=result.thread_id,
                active_turn_id=None,
            )
            response_letter = getattr(result.review, "response_letter", None)
            if response_letter:
                letter = parse_letter_text(
                    response_letter,
                    minimum=MIN_NOTEBOOK_LETTER,
                )
                self.store.append_response(session_id, letter.body)
                self.store.finish_response(session_id, final_text=letter.body)
        except CodexResponseTurnError:
            self.store.response_failed(session_id)
        except (OSError, RuntimeError, TypeError, ValueError):
            state = self.store.public_state(session_id)
            if state["review"]:
                self.store.response_failed(session_id)
            else:
                self.store.fail(session_id, "review_failed")

    def _run_response_retry(self, session_id: str, thread_id: str) -> None:
        try:
            letter = self.reviewer.respond_in_thread(
                thread_id=thread_id,
                on_response_delta=lambda delta: self.store.append_response(
                    session_id,
                    delta,
                ),
                on_turn_started=lambda phase, current_thread_id, turn_id: self.store.set_codex_task(
                    session_id,
                    thread_id=current_thread_id,
                    active_turn_id=turn_id,
                ),
            )
            self.store.finish_response(session_id, final_text=letter.body)
        except (CodexResponseTurnError, OSError, RuntimeError, TypeError, ValueError):
            self.store.response_failed(session_id)
        finally:
            with self._submit_lock:
                self._retrying.discard(session_id)

    def submit(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        required = {
            "session_id",
            "document_id",
            "reply_page_id",
            "reply_page_index",
            "marked_page_id",
            "response_page_id",
            "profile_id",
            "conversation_context",
        }
        if not isinstance(payload, Mapping) or not required.issubset(payload):
            raise ValueError("submission is missing required fields")
        self._profile(payload)
        session_id = self._identifier(payload["session_id"], "session id")
        document_id = self._identifier(payload["document_id"], "document id")
        reply_page_id = self._identifier(payload["reply_page_id"], "reply page id")
        marked_page_id = self._identifier(payload["marked_page_id"], "marked page id")
        response_page_id = self._identifier(payload["response_page_id"], "response page id")
        if payload["reply_page_index"] != 1:
            raise ValueError("only the huipi page can be submitted")
        context = payload["conversation_context"]
        if not isinstance(context, str) or len(context) > 4000:
            raise ValueError("invalid conversation context")

        with self._submit_lock:
            current = self.store.public_state(session_id)
            if (
                current["document_id"] != document_id
                or current["page_ids"].get("reply") != reply_page_id
            ):
                raise ValueError("notebook_binding_mismatch")
            if current["submitted_at"] is not None:
                if (
                    current["page_ids"].get("marked") != marked_page_id
                    or current["page_ids"].get("response") != response_page_id
                ):
                    raise ValueError("notebook_submit_page_mismatch")
                return {"status": current["phase"], **current}

            reply_image = self._prepare_reply(
                document_id=document_id,
                page_index=1,
                session_id=session_id,
            )
            state = self.store.begin_review(
                session_id,
                marked_page_id=marked_page_id,
                response_page_id=response_page_id,
            )
            self.background(
                lambda: self._run_review(
                    session_id=session_id,
                    reply_image=reply_image,
                    conversation_context=context.strip(),
                )
            )
            return {"status": "reviewing", **state}

    def retry_response(self, session_id: str) -> dict[str, Any]:
        session_id = self._identifier(session_id, "session id")
        with self._submit_lock:
            state = self.store.public_state(session_id)
            if (
                state["phase"] != "review-ready"
                or state["error"] != "response_failed"
                or not state["thread_id"]
            ):
                raise ValueError("notebook_response_retry_not_ready")
            if session_id not in self._retrying:
                self._retrying.add(session_id)
                self.background(
                    lambda: self._run_response_retry(session_id, state["thread_id"])
                )
            return {"status": "response-retrying", **state}

    def state(self, session_id: str) -> dict[str, Any]:
        return self.store.public_state(self._identifier(session_id, "session id"))

    def _tablet_readable(self) -> bool:
        documents = getattr(self.tablet, "_documents", None)
        if not callable(documents):
            return False
        documents()
        return True

    @staticmethod
    def _renderer_ready() -> bool:
        return shutil.which("pdftoppm") is not None

    @staticmethod
    def _codex_ready() -> bool:
        default_codex_command()
        return True

    def health(self) -> dict[str, Any]:
        values = {}
        for name in ("tablet_readable", "renderer", "codex"):
            try:
                values[name] = bool(self.health_checks[name]())
            except (KeyError, OSError, RuntimeError, ValueError):
                values[name] = False
        ok = all(values.values())
        return {
            "status": "ok" if ok else "unavailable",
            "listener": True,
            **values,
        }
