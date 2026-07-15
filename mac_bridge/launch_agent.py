"""Deterministic, secret-free LaunchAgent contract for the paired Mac bridge."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import shutil
import tempfile
from pathlib import Path
from typing import Callable

from .codex_app_server import resolve_codex_executable


LABEL = "com.erniesg.letters-home.bridge"
SANITIZED_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


class LaunchAgentError(ValueError):
    """A stable, non-secret setup failure."""


def _absolute(path: Path) -> Path:
    path = Path(path)
    if not path.is_absolute() or "\x00" in str(path):
        raise LaunchAgentError("launch_agent_path_invalid")
    return path


def render_launch_agent(
    *,
    repo_root: Path,
    python: Path,
    home: Path,
    conversation_context_file: Path | None = None,
) -> dict[str, object]:
    """Return a LaunchAgent that inherits no caller environment or secret."""

    repo_root = _absolute(repo_root)
    python = _absolute(python)
    home = _absolute(home)
    context = (
        _absolute(conversation_context_file)
        if conversation_context_file is not None
        else None
    )
    arguments = [
        "/usr/bin/env",
        "-i",
        f"HOME={home}",
        f"PATH={SANITIZED_PATH}",
        f"PYTHONPATH={repo_root}",
        str(python),
        "-m",
        "mac_bridge.server",
        "--repo-root",
        str(repo_root),
    ]
    if context is not None:
        arguments.extend(("--conversation-context-file", str(context)))
    state = home / ".local" / "share" / "letters-home"
    return {
        "Label": LABEL,
        "ProgramArguments": arguments,
        "WorkingDirectory": str(repo_root),
        "ProcessType": "Interactive",
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 5,
        "StandardOutPath": str(state / "bridge.stdout.log"),
        "StandardErrorPath": str(state / "bridge.stderr.log"),
    }


def launch_agent_bytes(**kwargs) -> bytes:
    return plistlib.dumps(
        render_launch_agent(**kwargs),
        fmt=plistlib.FMT_XML,
        sort_keys=True,
    )


def write_launch_agent(path: Path, **kwargs) -> Path:
    """Atomically write a mode-0600 plist; the caller owns its parent."""

    path = _absolute(path)
    data = launch_agent_bytes(**kwargs)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return path


def runtime_preflight(
    *,
    repo_root: Path,
    python: Path,
    codex: Path | None = None,
    pdftoppm: Path | None = None,
    module_available: Callable[[str], bool] | None = None,
) -> dict[str, str]:
    """Validate the executable runtime without starting Codex or the bridge."""

    repo_root = _absolute(repo_root)
    python = _absolute(python)
    if not (repo_root / "mac_bridge" / "server.py").is_file():
        raise LaunchAgentError("missing_runtime_dependency:repo")
    if not python.is_file() or not os.access(python, os.X_OK):
        raise LaunchAgentError("missing_runtime_dependency:python")
    # Kept as an injectable compatibility argument so callers can prove the
    # native path does not depend on the legacy PDF renderer's Python packages.
    del module_available
    if pdftoppm is None:
        discovered = shutil.which("pdftoppm")
        pdftoppm = Path(discovered) if discovered else None
    if pdftoppm is None or not pdftoppm.is_file() or not os.access(pdftoppm, os.X_OK):
        raise LaunchAgentError("missing_runtime_dependency:pdftoppm")
    if codex is None:
        codex = resolve_codex_executable(
            (
                Path("/Applications/ChatGPT.app/Contents/Resources/codex"),
                Path(shutil.which("codex") or ""),
            )
        )
    codex = Path(codex)
    if not codex.is_file() or not os.access(codex, os.X_OK):
        raise LaunchAgentError("missing_runtime_dependency:codex")
    return {
        "status": "ok",
        "python": str(python),
        "codex": str(codex),
        "pdftoppm": str(pdftoppm),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render or check the Letters Home bridge job")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render = subparsers.add_parser("render")
    render.add_argument("--repo-root", type=Path, required=True)
    render.add_argument("--python", type=Path, required=True)
    render.add_argument("--home", type=Path, required=True)
    render.add_argument("--conversation-context-file", type=Path)
    render.add_argument("--output", type=Path, required=True)

    check = subparsers.add_parser("check")
    check.add_argument("--repo-root", type=Path, required=True)
    check.add_argument("--python", type=Path, required=True)
    check.add_argument("--codex", type=Path)
    check.add_argument("--pdftoppm", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "render":
            write_launch_agent(
                args.output,
                repo_root=args.repo_root,
                python=args.python,
                home=args.home,
                conversation_context_file=args.conversation_context_file,
            )
            print(json.dumps({"status": "ok", "output": str(args.output)}, sort_keys=True))
        else:
            print(
                json.dumps(
                    runtime_preflight(
                        repo_root=args.repo_root,
                        python=args.python,
                        codex=args.codex,
                        pdftoppm=args.pdftoppm,
                    ),
                    sort_keys=True,
                )
            )
    except (LaunchAgentError, RuntimeError) as error:
        print(json.dumps({"status": "error", "error": str(error)}, sort_keys=True))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
