"""Command-line entry point for fixture release and recovery exercises."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Optional, Sequence

from . import (
    FixtureInstaller,
    InstallError,
    ReleaseError,
    build_release,
    create_fake_device,
)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build-release")
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--rcc", default=shutil.which("rcc") or shutil.which("rcc6"))

    create = commands.add_parser("create-fixture")
    create.add_argument("--root", type=Path, required=True)
    create.add_argument("--target", choices=("ferrari", "chiappa"), required=True)

    for name in ("preflight", "install", "uninstall", "recover"):
        command = commands.add_parser(name)
        command.add_argument("--release", type=Path, required=True)
        command.add_argument("--fixture-root", type=Path, required=True)

    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "build-release":
            if not arguments.rcc:
                print("fixture release build blocked: Qt rcc is unavailable", file=sys.stderr)
                return 2
            manifest = build_release(arguments.output, arguments.rcc)
            print(f"built fixture release manifest: {manifest}")
            return 0
        if arguments.command == "create-fixture":
            create_fake_device(arguments.root, arguments.target)
            print(f"created synthetic {arguments.target} fixture: {arguments.root}")
            return 0

        installer = FixtureInstaller(arguments.release, arguments.fixture_root)
        if arguments.command == "preflight":
            result = installer.preflight()
            action = "already_installed" if result.already_installed else "ready"
            print(f"fixture preflight: target={result.target}; action={action}")
        else:
            result = getattr(installer, arguments.command)()
            print(f"fixture {arguments.command}: target={result.target}; action={result.action}")
        return 0
    except (InstallError, ReleaseError, FileExistsError, OSError, ValueError) as error:
        code = getattr(error, "code", type(error).__name__)
        print(f"fixture operation refused: {code}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
