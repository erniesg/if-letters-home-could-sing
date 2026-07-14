"""Emit the exact held boundary for a future physical-device trial."""

from __future__ import annotations

import argparse
import json
from typing import Optional, Sequence

from toolbar_launcher.targets import TARGETS


HUMAN_DECISION_REQUIRED = 4
APPLOAD_APPLICATION_DESTINATION = "/home/root/xovi/exthome/appload/letters-home"


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
            "appload_application": APPLOAD_APPLICATION_DESTINATION,
            "basis": "maintained AppLoad v0.5.3 README",
            "toolbar_qmd": "pending_read_only_discovery",
            "toolbar_rcc": "pending_read_only_discovery",
        },
        "proposed_first_mutation": {
            "authorized": False,
            "phase": "inert toolbar icon only",
            "launch_action": False,
            "requires_second_owner_approval": True,
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
            "inert launcher placement and CJK coexistence",
            "Xochitl stability",
            "incoming letter, blank huipi reply, and reversible marginalia pages",
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
