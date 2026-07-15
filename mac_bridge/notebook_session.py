"""Durable, privacy-bounded state for one native notebook encounter."""

from __future__ import annotations

import copy
import json
import os
import re
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Mapping

from .contracts import MIN_NOTEBOOK_LETTER
from .letter_grid import FERRARI_GRID, SentenceStream, glyph_dicts


PHASES = {
    "incoming",
    "ready",
    "reviewing",
    "review-ready",
    "response-streaming",
    "complete",
    "failed",
}
_SAFE_ERROR = re.compile(r"^[a-z0-9][a-z0-9_:-]{0,95}$")


class NotebookSessionStore:
    """Persist only identifiers and bounded render state, never provider input."""

    def __init__(self, path: Path, *, minimum_letter: int = MIN_NOTEBOOK_LETTER):
        self.path = Path(path)
        self.minimum_letter = minimum_letter
        self._lock = threading.RLock()
        self._contexts: dict[str, str] = {}
        self._streams: dict[tuple[str, str], SentenceStream] = {}
        self._sessions = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1 or not isinstance(payload.get("sessions"), dict):
            raise ValueError("notebook_session_state_invalid")
        sessions = payload["sessions"]
        if any(
            not isinstance(session_id, str)
            or not isinstance(state, dict)
            or state.get("phase") not in PHASES
            for session_id, state in sessions.items()
        ):
            raise ValueError("notebook_session_state_invalid")
        return sessions

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{uuid.uuid4().hex}.tmp")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(
                    {"schema_version": 1, "sessions": self._sessions},
                    handle,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _state(self, session_id: str) -> dict[str, Any]:
        try:
            return self._sessions[session_id]
        except KeyError as error:
            raise KeyError("unknown notebook session") from error

    @staticmethod
    def _bump(state: dict[str, Any]) -> None:
        state["version"] += 1

    def begin(
        self,
        conversation_context: str,
        *,
        now: float | None = None,
        ttl_seconds: float = 24 * 60 * 60,
        session_id: str | None = None,
    ) -> str:
        now = time.time() if now is None else float(now)
        session_id = session_id or uuid.uuid4().hex
        with self._lock:
            if session_id in self._sessions:
                raise ValueError("notebook_session_exists")
            self._sessions[session_id] = {
                "session_id": session_id,
                "phase": "incoming",
                "version": 1,
                "created_at": now,
                "expires_at": now + float(ttl_seconds),
                "document_id": None,
                "page_ids": {},
                "incoming_text": "",
                "incoming_complete": False,
                "review": {},
                "response_text": "",
                "response_complete": False,
                "error": None,
                "first_ink_at": None,
                "submitted_at": None,
                "capture_window": "idle",
                "thread_id": None,
                "active_turn_id": None,
            }
            self._contexts[session_id] = str(conversation_context)
            self._write()
        return session_id

    def bind(
        self,
        session_id: str,
        *,
        document_id: str,
        incoming_page_id: str,
        reply_page_id: str,
    ) -> dict[str, Any]:
        requested_pages = {"incoming": incoming_page_id, "reply": reply_page_id}
        with self._lock:
            state = self._state(session_id)
            if state["document_id"] is not None:
                if state["document_id"] != document_id or any(
                    state["page_ids"].get(name) != value
                    for name, value in requested_pages.items()
                ):
                    raise ValueError("notebook_session_already_bound")
                return self._public(state)
            state["document_id"] = document_id
            state["page_ids"].update(requested_pages)
            if state["incoming_complete"]:
                state["phase"] = "ready"
            self._bump(state)
            self._write()
            return self._public(state)

    def _stream(self, session_id: str, field: str) -> SentenceStream:
        key = (session_id, field)
        stream = self._streams.get(key)
        if stream is None:
            stream = SentenceStream(FERRARI_GRID, minimum=self.minimum_letter)
            existing = self._state(session_id)[field]
            if existing:
                stream.append(existing)
            self._streams[key] = stream
        return stream

    def append_incoming(self, session_id: str, delta: str) -> dict[str, Any]:
        with self._lock:
            state = self._state(session_id)
            if state["incoming_complete"] or state["phase"] == "failed":
                return self._public(state)
            published = self._stream(session_id, "incoming_text").append(delta)
            if published != state["incoming_text"]:
                state["incoming_text"] = published
                self._bump(state)
                self._write()
            return self._public(state)

    def finish_incoming(
        self,
        session_id: str,
        *,
        final_text: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            state = self._state(session_id)
            if state["incoming_complete"]:
                return self._public(state)
            if final_text is not None:
                stream = SentenceStream(FERRARI_GRID, minimum=self.minimum_letter)
                stream.append(final_text)
                self._streams[(session_id, "incoming_text")] = stream
            else:
                stream = self._stream(session_id, "incoming_text")
            state["incoming_text"] = stream.finalize()
            state["incoming_complete"] = True
            if state["document_id"] is not None:
                state["phase"] = "ready"
            self._bump(state)
            self._write()
            return self._public(state)

    def mark_first_ink(
        self,
        session_id: str,
        *,
        observed_at: float | None = None,
    ) -> dict[str, Any]:
        observed_at = time.time() if observed_at is None else float(observed_at)
        with self._lock:
            state = self._state(session_id)
            if (
                state["document_id"] is None
                or "reply" not in state["page_ids"]
                or state["submitted_at"] is not None
                or state["phase"] == "failed"
            ):
                raise ValueError("notebook_reply_not_ready")
            if state["first_ink_at"] is not None:
                return self._public(state)
            state["first_ink_at"] = observed_at
            state["capture_window"] = "open"
            self._bump(state)
            self._write()
            return self._public(state)

    def begin_review(
        self,
        session_id: str,
        *,
        marked_page_id: str,
        response_page_id: str,
        observed_at: float | None = None,
    ) -> dict[str, Any]:
        observed_at = time.time() if observed_at is None else float(observed_at)
        requested = {"marked": marked_page_id, "response": response_page_id}
        with self._lock:
            state = self._state(session_id)
            existing = {name: state["page_ids"].get(name) for name in requested}
            if state["submitted_at"] is not None:
                if existing != requested:
                    raise ValueError("notebook_submit_page_mismatch")
                return self._public(state)
            if state["phase"] != "ready":
                raise ValueError("notebook_reply_not_ready")
            state["page_ids"].update(requested)
            state["submitted_at"] = observed_at
            state["capture_window"] = "closed"
            state["phase"] = "reviewing"
            self._bump(state)
            self._write()
            return self._public(state)

    def finish_review(
        self,
        session_id: str,
        review: Mapping[str, Any],
    ) -> dict[str, Any]:
        clean_review = json.loads(json.dumps(review, ensure_ascii=False))
        with self._lock:
            state = self._state(session_id)
            if state["phase"] not in {"reviewing", "review-ready"}:
                raise ValueError("notebook_review_not_active")
            if state["phase"] == "review-ready" and state["review"] == clean_review:
                return self._public(state)
            state["review"] = clean_review
            state["phase"] = "review-ready"
            self._bump(state)
            self._write()
            return self._public(state)

    def append_response(self, session_id: str, delta: str) -> dict[str, Any]:
        with self._lock:
            state = self._state(session_id)
            if state["response_complete"] or state["phase"] == "failed":
                return self._public(state)
            if state["phase"] not in {"review-ready", "response-streaming"}:
                raise ValueError("notebook_response_not_ready")
            published = self._stream(session_id, "response_text").append(delta)
            changed = published != state["response_text"]
            if changed:
                state["response_text"] = published
            if state["phase"] != "response-streaming":
                state["phase"] = "response-streaming"
                changed = True
            if changed:
                self._bump(state)
                self._write()
            return self._public(state)

    def finish_response(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            state = self._state(session_id)
            if state["response_complete"]:
                return self._public(state)
            state["response_text"] = self._stream(
                session_id,
                "response_text",
            ).finalize()
            state["response_complete"] = True
            state["active_turn_id"] = None
            state["phase"] = "complete"
            self._bump(state)
            self._write()
            return self._public(state)

    def set_codex_task(
        self,
        session_id: str,
        *,
        thread_id: str,
        active_turn_id: str | None,
    ) -> dict[str, Any]:
        with self._lock:
            state = self._state(session_id)
            if (
                state["thread_id"] == thread_id
                and state["active_turn_id"] == active_turn_id
            ):
                return self._public(state)
            if state["thread_id"] not in {None, thread_id}:
                raise ValueError("notebook_codex_task_mismatch")
            state["thread_id"] = thread_id
            state["active_turn_id"] = active_turn_id
            self._bump(state)
            self._write()
            return self._public(state)

    def fail(self, session_id: str, error_code: str) -> dict[str, Any]:
        if not _SAFE_ERROR.fullmatch(error_code):
            raise ValueError("unsafe_notebook_error_code")
        with self._lock:
            state = self._state(session_id)
            if state["phase"] == "failed" and state["error"] == error_code:
                return self._public(state)
            state["phase"] = "failed"
            state["error"] = error_code
            state["active_turn_id"] = None
            self._bump(state)
            self._write()
            return self._public(state)

    def public_state(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            return self._public(self._state(session_id))

    def _public(self, state: Mapping[str, Any]) -> dict[str, Any]:
        incoming_text = state["incoming_text"]
        response_text = state["response_text"]
        return {
            "session_id": state["session_id"],
            "phase": state["phase"],
            "version": state["version"],
            "document_id": state["document_id"],
            "page_ids": copy.deepcopy(state["page_ids"]),
            "incoming": {
                "text": incoming_text,
                "glyphs": glyph_dicts(incoming_text),
            },
            "review": copy.deepcopy(state["review"]),
            "response": {
                "text": response_text,
                "glyphs": glyph_dicts(response_text),
            },
            "error": state["error"],
            "first_ink_at": state["first_ink_at"],
            "submitted_at": state["submitted_at"],
            "capture_window": state["capture_window"],
            "thread_id": state["thread_id"],
            "active_turn_id": state["active_turn_id"],
            "created_at": state["created_at"],
            "expires_at": state["expires_at"],
        }

    def render_directory(self, session_id: str) -> Path:
        with self._lock:
            self._state(session_id)
        return self.path.parent / "notebook-renders" / session_id

    def expire(self, *, now: float | None = None) -> tuple[str, ...]:
        now = time.time() if now is None else float(now)
        with self._lock:
            expired = tuple(
                sorted(
                    session_id
                    for session_id, state in self._sessions.items()
                    if state["expires_at"] <= now
                )
            )
            if not expired:
                return ()
            for session_id in expired:
                del self._sessions[session_id]
                self._contexts.pop(session_id, None)
                self._streams.pop((session_id, "incoming_text"), None)
                self._streams.pop((session_id, "response_text"), None)
            self._write()
        for session_id in expired:
            shutil.rmtree(
                self.path.parent / "notebook-renders" / session_id,
                ignore_errors=True,
            )
        return expired
