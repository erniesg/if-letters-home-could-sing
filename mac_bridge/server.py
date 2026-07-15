"""Private USB-link HTTP bridge used by the two exact QMLDiff actions."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping

from .codex_app_server import CodexAppServerClient
from .native_packet import NativePacketRenderer
from .remarkable_usb import RemarkableUsbDocuments
from .service import ReceiptStore, SessionRegistry, SessionStarter, SubmissionService

# Observed Mac-side address on the Ferrari USB /27 link (en11).
DEFAULT_USB_BIND = "10.11.99.16"


class CodexLetterRunner:
    def __init__(self, *, cwd: Path, imagegen_skill: Path):
        self.cwd = cwd
        self.imagegen_skill = imagegen_skill

    def generate_letter(self, *, session_id: str, conversation_context: str):
        return CodexAppServerClient(cwd=self.cwd).generate_letter(
            session_id=session_id,
            conversation_context=conversation_context,
            imagegen_skill=self.imagegen_skill,
        )


class CodexReviewRunner:
    def __init__(self, *, cwd: Path):
        self.cwd = cwd

    def review_reply(self, *, session_id: str, reply_image: Path, conversation_context: str):
        return CodexAppServerClient(cwd=self.cwd).review_reply(
            session_id=session_id,
            reply_image=reply_image,
            conversation_context=conversation_context,
        )


class BridgeApplication:
    def __init__(self, *, starter: SessionStarter, submissions: SubmissionService):
        self.starter = starter
        self.submissions = submissions

    def dispatch(self, path: str, payload: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
        if path == "/v1/sessions/start":
            return 200, self.starter.start(payload)
        if path == "/v1/sessions/submit":
            return 200, self.submissions.submit(payload)
        return 404, {"error": "not_found"}


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "LettersHomeBridge/1"

    def log_message(self, format, *args):
        # Request bodies contain participant context and must never enter access logs.
        return

    def _write(self, status: int, payload: Mapping[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._write(200, {"status": "ok"})
            return
        self._write(404, {"error": "not_found"})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_POST(self):
        length = self.headers.get("Content-Length")
        try:
            size = int(length or "0")
        except ValueError:
            self._write(400, {"error": "invalid_request"})
            return
        if size <= 0 or size > 64 * 1024:
            self._write(413, {"error": "request_too_large"})
            return
        try:
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError
            application = self.server.application
            status, response = application.dispatch(self.path, payload)
        except (json.JSONDecodeError, ValueError):
            self._write(400, {"error": "invalid_request"})
            return
        except RuntimeError as error:
            code = str(error)
            safe = code if code.replace("_", "").isalnum() else "roundtrip_failed"
            self._write(502, {"error": safe})
            return
        self._write(status, response)


class BridgeServer(ThreadingHTTPServer):
    def __init__(self, address, application: BridgeApplication):
        super().__init__(address, BridgeHandler)
        self.application = application


def build_application(
    *,
    repo_root: Path,
    imagegen_skill: Path,
    conversation_context: str,
) -> BridgeApplication:
    tablet = RemarkableUsbDocuments()
    renderer = NativePacketRenderer()
    registry = SessionRegistry()
    starter = SessionStarter(
        tablet=tablet,
        renderer=renderer,
        generator=CodexLetterRunner(cwd=repo_root, imagegen_skill=imagegen_skill),
        registry=registry,
        default_context=conversation_context,
    )
    submissions = SubmissionService(
        tablet=tablet,
        renderer=renderer,
        reviewer=CodexReviewRunner(cwd=repo_root),
        registry=registry,
        receipts=ReceiptStore(Path.home() / ".local/share/letters-home/receipts.json"),
    )
    return BridgeApplication(starter=starter, submissions=submissions)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the private Letters Home Mac bridge")
    parser.add_argument("--bind", default=DEFAULT_USB_BIND)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--imagegen-skill",
        type=Path,
        default=Path.home() / ".codex/skills/.system/imagegen/SKILL.md",
    )
    parser.add_argument("--conversation-context-file", type=Path)
    args = parser.parse_args(argv)
    context = (
        args.conversation_context_file.read_text(encoding="utf-8")
        if args.conversation_context_file
        else "care across distance, health, education, remittance received, and returning home"
    )
    application = build_application(
        repo_root=args.repo_root.resolve(),
        imagegen_skill=args.imagegen_skill.resolve(),
        conversation_context=context,
    )
    server = BridgeServer((args.bind, args.port), application)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
