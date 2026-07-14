"""Synthetic Ferrari and Chiappa filesystem fixtures for installer tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from toolbar_launcher.targets import TARGETS

from .release import ROOT


DEVICE_RECORD = ".letters-home-fixture-device.json"
ACTIVE_QMDS_RECORD = "xovi/active-qmds.json"
DEPENDENCIES_RECORD = "xovi/dependencies.json"
BACKUP_MARKER = "backups/verified.json"
BACKUP_RESOURCE = "backups/Sidebar.qml"
DEFAULT_FREE_BYTES = 64 * 1024 * 1024


def create_fake_device(
    root: Path,
    target_name: str,
    *,
    free_space_bytes: int = DEFAULT_FREE_BYTES,
) -> Path:
    """Create a sanitized filesystem fixture; never discovers real hardware."""

    try:
        target = TARGETS[target_name]
    except KeyError as error:
        raise ValueError("unknown fixture target") from error
    if root.exists():
        raise FileExistsError(root)

    for directory in (
        root / "backups",
        root / "opt" / "etc" / "draft" / "appload" / "apps",
        root / "opt" / "xovi" / "extensions",
        root / "qml",
        root / "xovi",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    source = ROOT / "toolbar_launcher" / target.fixture_path
    resource = root / target.resource_path.lstrip("/")
    resource.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, resource)
    shutil.copy2(source, root / BACKUP_RESOURCE)
    _write_json(
        root / DEVICE_RECORD,
        {
            "appload_version": target.appload_version,
            "fixture_only": True,
            "free_space_bytes": free_space_bytes,
            "model": target.model,
            "os_version": target.os_version,
            "schema_version": 1,
            "target": target_name,
            "xovi_version": target.xovi_version,
        },
    )
    _write_json(root / ACTIVE_QMDS_RECORD, {"qmds": list(target.active_qmd_order)})
    _write_json(
        root / DEPENDENCIES_RECORD,
        {
            "appload": target.appload_version,
            "xovi": target.xovi_version,
        },
    )
    _write_json(
        root / BACKUP_MARKER,
        {
            "backup_path": BACKUP_RESOURCE,
            "model": target.model,
            "os_version": target.os_version,
            "resource_path": target.resource_path,
            "resource_sha256": target.resource_sha256,
            "target": target_name,
            "verified": True,
        },
    )
    return root


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o644)
