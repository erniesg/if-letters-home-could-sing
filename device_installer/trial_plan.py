"""Emit the exact held boundary for a future physical-device trial."""

from __future__ import annotations

import argparse
import json
from typing import Optional, Sequence

from toolbar_launcher.targets import TARGETS


HUMAN_DECISION_REQUIRED = 4
MAC_BRIDGE_DESTINATION = "10.11.99.16:8765"


def approval_plan(target_name: str) -> dict[str, object]:
    """Describe read-only discovery without contacting or mutating a tablet."""

    target = TARGETS[target_name]
    return {
        "schema_version": 1,
        "action": "stop_for_owner_approval",
        "authorization": {
            "network_access": False,
            "read_only_device_discovery": False,
            "mutation": False,
            "provider_calls": False,
        },
        "requested_read_only_window_minutes": 5,
        "target": {
            "codename": target.codename,
            "model": target.model,
        },
        "fixture_expectations": {
            "os_version": target.os_version,
            "resource_id": target.resource_id,
            "resource_path": target.resource_path,
            "resource_sha256": target.resource_sha256,
            "appload_version": target.appload_version,
            "xovi_version": target.xovi_version,
            "qmldiff_commit": target.qmldiff_commit,
            "qrr_commit": target.qrr_commit,
            "active_qmd_order": list(target.active_qmd_order),
            "warning": "fixture expectations are not observations of the physical device",
        },
        "backed_up_observations": {
            "hashtab_sha256": target.hashtab_sha256,
            "resource_sha256": target.backed_up_resource_sha256,
            "source": "verified full-device backup for this target",
            "warning": "backed-up observations must be re-confirmed on the connected device",
            "xochitl_sha256": target.xochitl_sha256,
        },
        "observed_device_state": None,
        "read_only_discovery_fields": [
            "connection endpoint selected by the owner",
            "exact model and codename",
            "OS build",
            "Xovi and AppLoad versions",
            "QRR resource id, path, bytes, and SHA-256",
            "active QMD filenames and order",
            "actual AppLoad and QMD/RCC destinations",
            "file owners, groups, and modes",
            "free space",
            "current backup paths, timestamps, and SHA-256 values",
            "Xochitl and CJK patch health without restart",
        ],
        "proposed_destinations": {
            "mac_bridge": MAC_BRIDGE_DESTINATION,
            "sidebar_launch_qmd": "pending_read_only_discovery",
            "document_submit_qmd": "pending_read_only_discovery",
            "existing_appload_payload": "leave unchanged; native launcher never opens it",
            "basis": "recovered exact 3.28 Sidebar.qml and DocumentView.qml resources",
        },
        "proposed_first_mutation": {
            "authorized": False,
            "phase": "replace sidebar handler with native document launch and add page-2 submit action",
            "launch_action": "Mac bridge to stock legacydevice/window/main",
            "requires_second_owner_approval": False,
        },
        "expected_downtime": {
            "read_only_discovery_seconds": 0,
            "mutation_seconds": None,
            "reboot_expected": False,
            "note": "mutation duration cannot be approved until discovery fixes the actual paths and restart requirement",
        },
        "rollback": {
            "authorized": False,
            "require_byte_identical_restore": True,
            "commands": "pending observed paths and backup hashes",
        },
        "controlled_trial_checks": [
            "main-sidebar placement below Import files and CJK coexistence",
            "Xochitl stability",
            "full-bleed incoming letter and blank huipi in stock DocumentView",
            "stock pen, marker, eraser, undo, close, toolbar, and swipe-down behavior",
            "submit creates a persisted Codex task on the Mac",
            "returned reviewed copy opens at page 3 with anchored marginalia",
            "pen input and first-ink timing",
            "mock heart rate through atomic submit",
            "submit, duplicate submit, timeout, and retry",
            "suspend and resume",
            "portrait and landscape orientation",
            "uninstall and byte-identical rollback",
        ],
        "stop_conditions": [
            "any model, OS, version, resource, QMD, path, mode, or backup mismatch",
            "unexpected file change or missing rollback",
            "CJK, input, refresh, or Xochitl instability",
        ],
        "forbidden_during_held_phase": [
            "tablet login or file transfer",
            "Xochitl stop or restart",
            "reboot",
            "QMD or RCC installation",
            "stock reMarkable screenshot helper while Xovi is running",
        ],
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=tuple(sorted(TARGETS)), required=True)
    arguments = parser.parse_args(argv)
    print(json.dumps(approval_plan(arguments.device), indent=2, sort_keys=True))
    return HUMAN_DECISION_REQUIRED


if __name__ == "__main__":
    raise SystemExit(main())
