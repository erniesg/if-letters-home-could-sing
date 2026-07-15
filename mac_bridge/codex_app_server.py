"""Persisted Codex task client over the local app-server JSON-RPC protocol."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol

from .contracts import REVIEW_OUTPUT_SCHEMA, Review, parse_review


DEFAULT_REVIEWER_PROMPT = """You are reading a handwritten contemporary huipi on a fictional qiao pi correspondence.
Act as a kind Chinese-language teacher and attentive correspondent. Ground every note in what is actually visible.
Offer concise corrections, uncertain readings, tone guidance, affirmations, and one reflective question.
Never score or grade. Never invent a full transcription. Mark uncertain handwriting as uncertain.
The participant's original ink is immutable. Return only the requested JSON object."""


class RpcChannel(Protocol):
    def request(self, method: str, params: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def notify(self, method: str, params: Mapping[str, Any]) -> None: ...

    def events(self) -> Iterable[Mapping[str, Any]]: ...


def resolve_codex_executable(candidates: Iterable[Path]) -> Path:
    """Select the first executable candidate without assuming one exists in CI."""

    for candidate in candidates:
        candidate = Path(candidate)
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise RuntimeError("codex_app_server_unavailable")


def default_codex_command() -> tuple[str, ...]:
    """Use the desktop-bundled Codex first so protocol and signed-in model stay aligned."""

    executable = resolve_codex_executable(
        (
            Path("/Applications/ChatGPT.app/Contents/Resources/codex"),
            Path(shutil.which("codex") or ""),
        )
    )
    return (str(executable), "app-server", "--stdio")


class SubprocessJsonRpcChannel:
    """Line-delimited JSON-RPC connection to one local `codex app-server`."""

    def __init__(self, command: tuple[str, ...] | None = None):
        command = command or default_codex_command()
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._next_id = 1
        self._buffered_events: list[Mapping[str, Any]] = []

    def _send(self, payload: Mapping[str, Any]) -> None:
        if self.process.stdin is None:
            raise RuntimeError("codex app-server stdin is unavailable")
        self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def _read(self) -> Mapping[str, Any]:
        if self.process.stdout is None:
            raise RuntimeError("codex app-server stdout is unavailable")
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("codex app-server closed before completing the task")
        payload = json.loads(line)
        if not isinstance(payload, Mapping):
            raise RuntimeError("codex app-server returned an invalid message")
        return payload

    def request(self, method: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        while True:
            payload = self._read()
            if payload.get("id") == request_id:
                if "error" in payload:
                    error = payload["error"]
                    message = error.get("message", str(error)) if isinstance(error, Mapping) else str(error)
                    raise RuntimeError(message)
                result = payload.get("result", {})
                if not isinstance(result, Mapping):
                    raise RuntimeError(f"{method} returned an invalid result")
                return result
            if "method" in payload:
                self._buffered_events.append(payload)

    def notify(self, method: str, params: Mapping[str, Any]) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def events(self) -> Iterable[Mapping[str, Any]]:
        while self._buffered_events:
            yield self._buffered_events.pop(0)
        while True:
            yield self._read()

    def close(self) -> None:
        if self.process.stdin:
            self.process.stdin.close()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


@dataclass(frozen=True)
class CodexReviewResult:
    thread_id: str
    review: Review


@dataclass(frozen=True)
class CodexImageResult:
    thread_id: str
    image_path: Path


class CodexAppServerClient:
    """Create one visible, non-ephemeral Codex task for a durable reply submit."""

    def __init__(
        self,
        *,
        channel: RpcChannel | None = None,
        cwd: Path,
        reviewer_prompt: str = DEFAULT_REVIEWER_PROMPT,
    ):
        self.channel = channel or SubprocessJsonRpcChannel()
        self._owns_channel = channel is None
        self.cwd = Path(cwd).resolve()
        self.reviewer_prompt = reviewer_prompt.strip()
        self.model: str | None = None

    def _initialize(self) -> None:
        self.channel.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "if-letters-home-could-sing",
                    "title": "Letters Home bridge",
                    "version": "1",
                }
            },
        )
        self.channel.notify("initialized", {})
        catalog = self.channel.request(
            "model/list",
            {"includeHidden": False, "limit": 100},
        )
        models = catalog.get("data")
        if not isinstance(models, list):
            raise RuntimeError("Codex model catalog is unavailable")
        compatible = [
            model
            for model in models
            if isinstance(model, Mapping)
            and "image" in model.get("inputModalities", [])
            and isinstance(model.get("model") or model.get("id"), str)
        ]
        selected = next((model for model in compatible if model.get("isDefault")), None)
        selected = selected or (compatible[0] if compatible else None)
        if selected is None:
            raise RuntimeError("Codex has no image-capable model")
        self.model = selected.get("model") or selected["id"]

    def _start_thread(self, *, session_id: str, purpose: str, developer_instructions: str) -> str:
        if not self.model:
            raise RuntimeError("Codex client was not initialized")
        started = self.channel.request(
            "thread/start",
            {
                "cwd": str(self.cwd),
                "ephemeral": False,
                "sandbox": "read-only",
                "approvalPolicy": "never",
                "model": self.model,
                "threadSource": f"letters-home-{purpose}",
                "personality": "pragmatic",
                "developerInstructions": developer_instructions,
            },
        )
        thread = started.get("thread")
        thread_id = thread.get("id") if isinstance(thread, Mapping) else None
        if not isinstance(thread_id, str) or not thread_id:
            raise RuntimeError("thread/start did not return a Codex thread id")
        self.channel.request(
            "thread/name/set",
            {
                "threadId": thread_id,
                "name": f"Letters Home {purpose} · {session_id}",
            },
        )
        return thread_id

    def generate_letter(
        self,
        *,
        session_id: str,
        conversation_context: str,
        imagegen_skill: Path,
    ) -> CodexImageResult:
        """Create one visible Codex image task and return its saved raster path."""

        imagegen_skill = Path(imagegen_skill).resolve()
        if not imagegen_skill.is_file():
            raise ValueError("imagegen skill does not exist")
        channel = self.channel
        try:
            self._initialize()
            thread_id = self._start_thread(
                session_id=session_id,
                purpose="incoming",
                developer_instructions=(
                    "Use the attached image-generation skill once. Do not use shell or unrelated tools. "
                    "Create a fictional image only and preserve the saved output path."
                ),
            )
            prompt = f"""Use gpt-image-2 to create one full-bleed, wide fictional qiao pi-inspired family letter image.
Compose for a 1696 × 960 source canvas; the trusted Mac will crop 3 px from top and bottom for Ferrari.
Material direction: warm fibrous paper, fold memory, restrained red rules, muted blue-black handwritten Chinese.
The emotional content should correspond to this conversation context without copying it verbatim:
{conversation_context.strip() or 'care across distance, health, education, remittance received, and returning home'}

Do not use any real personal name, accession number, signature, seal, museum logo, authenticity claim,
archival master, application toolbar, device frame, drop shadow, or outer margin. This is visibly fictional."""
            started_turn = channel.request(
                "turn/start",
                {
                    "threadId": thread_id,
                    "input": [
                        {"type": "text", "text": prompt},
                        {"type": "skill", "name": "imagegen", "path": str(imagegen_skill)},
                    ],
                },
            )
            turn = started_turn.get("turn")
            turn_id = turn.get("id") if isinstance(turn, Mapping) else None
            if not isinstance(turn_id, str) or not turn_id:
                raise RuntimeError("turn/start did not return a Codex turn id")
            saved_path = None
            for event in channel.events():
                method = event.get("method")
                params = event.get("params")
                if not isinstance(params, Mapping) or params.get("threadId") != thread_id:
                    continue
                if method == "item/completed" and params.get("turnId") == turn_id:
                    item = params.get("item")
                    if isinstance(item, Mapping) and item.get("type") == "imageGeneration":
                        candidate = item.get("savedPath")
                        if isinstance(candidate, str) and candidate:
                            saved_path = Path(candidate).resolve()
                if method == "turn/completed":
                    completed = params.get("turn")
                    if not isinstance(completed, Mapping) or completed.get("id") != turn_id:
                        continue
                    if completed.get("status") != "completed":
                        error = completed.get("error")
                        message = error.get("message", str(error)) if isinstance(error, Mapping) else str(error)
                        raise RuntimeError(message or "Codex image turn failed")
                    break
            if saved_path is None or not saved_path.is_file():
                raise RuntimeError("Codex image task completed without a saved image")
            return CodexImageResult(thread_id, saved_path)
        finally:
            if self._owns_channel and hasattr(channel, "close"):
                channel.close()

    def review_reply(
        self,
        *,
        session_id: str,
        reply_image: Path,
        conversation_context: str,
    ) -> CodexReviewResult:
        reply_image = Path(reply_image).resolve()
        if not reply_image.is_file():
            raise ValueError("reply image does not exist")
        channel = self.channel
        try:
            self._initialize()
            thread_id = self._start_thread(
                session_id=session_id,
                purpose="review",
                developer_instructions=(
                    "Do not use shell, network, or file-write tools. Analyze the attached reply image "
                    "and return only JSON matching the supplied output schema."
                ),
            )
            prompt = (
                f"{self.reviewer_prompt}\n\n"
                "Conversation context for reciprocity only; do not quote it as if handwritten:\n"
                f"{conversation_context.strip() or 'No prior context supplied.'}"
            )
            started_turn = channel.request(
                "turn/start",
                {
                    "threadId": thread_id,
                    "input": [
                        {"type": "text", "text": prompt},
                        {"type": "localImage", "path": str(reply_image), "detail": "original"},
                    ],
                    "outputSchema": REVIEW_OUTPUT_SCHEMA,
                },
            )
            turn = started_turn.get("turn")
            turn_id = turn.get("id") if isinstance(turn, Mapping) else None
            if not isinstance(turn_id, str) or not turn_id:
                raise RuntimeError("turn/start did not return a Codex turn id")

            final_text = None
            for event in channel.events():
                method = event.get("method")
                params = event.get("params")
                if not isinstance(params, Mapping) or params.get("threadId") != thread_id:
                    continue
                if method == "item/completed" and params.get("turnId") == turn_id:
                    item = params.get("item")
                    if (
                        isinstance(item, Mapping)
                        and item.get("type") == "agentMessage"
                        and item.get("phase") in {None, "final_answer"}
                        and isinstance(item.get("text"), str)
                    ):
                        final_text = item["text"]
                if method == "turn/completed":
                    completed = params.get("turn")
                    if not isinstance(completed, Mapping) or completed.get("id") != turn_id:
                        continue
                    if completed.get("status") != "completed":
                        error = completed.get("error")
                        message = error.get("message", str(error)) if isinstance(error, Mapping) else str(error)
                        raise RuntimeError(message or "Codex review turn failed")
                    break
            if final_text is None:
                raise RuntimeError("Codex review completed without a final structured response")
            try:
                payload = json.loads(final_text)
            except json.JSONDecodeError as error:
                raise RuntimeError("Codex review was not valid JSON") from error
            return CodexReviewResult(thread_id, parse_review(payload))
        finally:
            if self._owns_channel and hasattr(channel, "close"):
                channel.close()
