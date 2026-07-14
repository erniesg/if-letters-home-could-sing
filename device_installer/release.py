"""Build an auditable, fixture-only AppLoad and sidebar-launcher release."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Mapping

from tablet_app.packaging import build_bundle
from toolbar_launcher.targets import TARGETS, Target


ROOT = Path(__file__).resolve().parents[1]
INSTALLER_VERSION = "1.0.0-fixture.1"
MANIFEST_NAME = "payload-manifest.json"
PAYLOAD_DIRECTORY = "payload"
ACTIVE_INSTALL_QMD = "10-letters-home-inert.qmd"
INSTALL_LAYOUT = (
    {
        "name": "app",
        "payload": "appload/letters-home",
        "destination": "opt/etc/draft/appload/apps/letters-home",
    },
    {
        "name": "toolbar",
        "payload": "toolbar",
        "destination": "opt/xovi/extensions/letters-home",
    },
)


class ReleaseError(ValueError):
    """A deterministic release-build refusal."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def sha256(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def target_manifest(target: Target) -> dict[str, object]:
    """Return one independent exact-target record for the release manifest."""

    return {
        "active_qmd_order": list(target.active_qmd_order),
        "appload_version": target.appload_version,
        "codename": target.codename,
        "model": target.model,
        "os_version": target.os_version,
        "qmldiff_commit": target.qmldiff_commit,
        "qrr_commit": target.qrr_commit,
        "resource_id": target.resource_id,
        "resource_path": target.resource_path,
        "resource_sha256": target.resource_sha256,
        "xovi_version": target.xovi_version,
    }


def build_release(output: Path, rcc: str) -> Path:
    """Build a release atomically and pin every resulting payload file."""

    output = output.resolve()
    if output.exists():
        raise ReleaseError("release_destination_exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.building-", dir=output.parent)
    )
    try:
        payload = staging / PAYLOAD_DIRECTORY
        app = payload / "appload" / "letters-home"
        build_bundle(app, rcc)
        shutil.copytree(ROOT / "toolbar_launcher" / "qmldiff", payload / "toolbar")

        for path in payload.rglob("*"):
            if path.is_file():
                mode = 0o755 if path == app / "backend" / "entry" else 0o644
                path.chmod(mode)

        files = [_file_record(path, payload) for path in sorted(payload.rglob("*")) if path.is_file()]
        payload_size = sum(int(item["size_bytes"]) for item in files)
        manifest = {
            "active_install_qmd": ACTIVE_INSTALL_QMD,
            "fixture_only": True,
            "install_layout": list(INSTALL_LAYOUT),
            "installer_version": INSTALLER_VERSION,
            "minimum_free_bytes": max(1_048_576, payload_size * 2),
            "payload_files": files,
            "required_dependencies": {
                "appload": TARGETS["chiappa"].appload_version,
                "xovi": TARGETS["chiappa"].xovi_version,
            },
            "schema_version": 1,
            "targets": {
                name: target_manifest(target)
                for name, target in sorted(TARGETS.items())
            },
        }
        manifest_path = staging / MANIFEST_NAME
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifest_path.chmod(0o644)
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return output / MANIFEST_NAME


def load_release_manifest(release: Path) -> Mapping[str, object]:
    try:
        manifest = json.loads((release / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseError("invalid_release_manifest") from error
    if not isinstance(manifest, dict):
        raise ReleaseError("invalid_release_manifest")
    return manifest


def _file_record(path: Path, payload: Path) -> dict[str, object]:
    mode = stat.S_IMODE(path.stat().st_mode)
    return {
        "mode": f"{mode:04o}",
        "path": path.relative_to(payload).as_posix(),
        "sha256": sha256(path.read_bytes()),
        "size_bytes": path.stat().st_size,
    }
