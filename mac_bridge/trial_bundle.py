"""Build a redacted, hash-pinned Ferrari native QMLDiff trial bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from toolbar_launcher.targets import TARGETS


ROOT = Path(__file__).resolve().parents[1]
QMD_NAMES = (
    "10-letters-home-inert.qmd",
    "20-letters-home-launch.qmd",
    "30-letters-home-submit.qmd",
)
DOCUMENT_VIEW_RESOURCE_ID = "[[1224665461898798997]]"
DOCUMENT_VIEW_SOURCE_SHA256 = "a2102689b1feb4604e98ece588ee4606a64a7b0599bda2a3e8fac431f0fa74a5"


class TrialBundleError(ValueError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_trial_bundle(output: Path, *, target_name: str) -> Path:
    """Package reviewed patches only; never contact or mutate a tablet."""

    if target_name != "ferrari":
        raise TrialBundleError("chiappa_exact_resource_unverified")
    output = Path(output).resolve()
    if output.exists():
        raise TrialBundleError("trial_bundle_destination_exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.building-", dir=output.parent))
    try:
        qmd_destination = staging / "qmldiff"
        qmd_destination.mkdir()
        entries = []
        for name in QMD_NAMES:
            source = ROOT / "toolbar_launcher" / "qmldiff" / name
            destination = qmd_destination / name
            shutil.copy2(source, destination)
            entries.append(
                {
                    "name": name,
                    "sha256": _sha256(destination),
                    "size_bytes": destination.stat().st_size,
                }
            )
        target = TARGETS[target_name]
        manifest = {
            "schema_version": 1,
            "target": {
                "codename": target.codename,
                "model": target.model,
                "os_version": target.os_version,
                "xochitl_sha256": target.xochitl_sha256,
                "hashtab_sha256": target.hashtab_sha256,
            },
            "sidebar": {
                "resource_id": target.resource_id,
                "backed_up_source_sha256": target.backed_up_resource_sha256,
            },
            "document_view": {
                "resource_id": DOCUMENT_VIEW_RESOURCE_ID,
                "recovered_source_sha256": DOCUMENT_VIEW_SOURCE_SHA256,
            },
            "bridge": {"host": "10.11.99.2", "port": 8765},
            "qmds": entries,
            "requires_live_preflight": True,
            "mutation_authorized_by_manifest": False,
            "rollback": "restore the backed-up Letters Home QMD set and restart Xochitl once",
        }
        manifest_path = staging / "native-trial-manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        staging.replace(output)
        return output / manifest_path.name
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("ferrari", "chiappa"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        path = build_trial_bundle(args.output, target_name=args.target)
    except TrialBundleError as error:
        parser.error(str(error))
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
