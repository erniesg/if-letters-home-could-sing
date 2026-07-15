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
NATIVE_API_CONTRACTS = {
    "ferrari": ROOT
    / "contracts"
    / "native-notebook-api.ferrari-3.28.0.162.json",
}
QMD_NAMES = (
    "10-letters-home-inert.qmd",
    "20-letters-home-launch.qmd",
    "30-letters-home-submit.qmd",
)
TEMPLATE_ASSETS = (
    (
        "letters-home-ferrari.template",
        "/usr/share/remarkable/templates/letters-home-ferrari.template",
    ),
)
DOCUMENT_VIEW_RESOURCE_ID = "[[1224665461898798997]]"
DOCUMENT_VIEW_SOURCE_SHA256 = "a2102689b1feb4604e98ece588ee4606a64a7b0599bda2a3e8fac431f0fa74a5"


class TrialBundleError(ValueError):
    pass


def load_native_api_contract(target_name: str) -> dict[str, object]:
    """Load a saved exact-resource contract or fail closed."""

    try:
        target = TARGETS[target_name]
        path = NATIVE_API_CONTRACTS[target_name]
        contract = json.loads(path.read_text(encoding="utf-8"))
        resources = contract["resources"]
        recovered_sources = contract["recovered_source_sha256"]
        symbols = contract["symbols"]
        required_resources = {
            "sidebar",
            "document_view",
            "create_notebook",
            "create_notebook_window",
            "pages",
            "pages_actions",
        }
        required_symbols = {
            "DocumentController.addPageWithTemplateAndPageSize",
            "DocumentController.copyPages",
            "DocumentController.setTemplateForPage",
            "LibraryController.createDocument",
            "NavigationManager.activeContext.explorer.currentFolderId",
            "createNotebook",
            "createNotebookFromExistingPages",
            "currentFolderId",
            "documentName",
            "document.idForPage",
            "onNotebookClicked",
            "root.createNotebook",
        }
        if (
            contract["target"] != target_name
            or contract["os_version"] != target.os_version
            or contract["hashtab_sha256"] != target.hashtab_sha256
            or not isinstance(resources, dict)
            or not required_resources.issubset(resources)
            or not isinstance(recovered_sources, dict)
            or not required_resources.issubset(recovered_sources)
            or any(
                not isinstance(value, str) or len(value) != 64
                for value in recovered_sources.values()
            )
            or not isinstance(symbols, dict)
            or not required_symbols.issubset(symbols)
        ):
            raise ValueError
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise TrialBundleError("native_notebook_api_unverified") from error
    return contract


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_app_owned_destination(
    destination: Path,
    *,
    expected_sha256: str,
) -> str:
    """Classify one app-owned path without overwriting unknown device bytes."""

    destination = Path(destination)
    if not destination.exists():
        return "install"
    if not destination.is_file() or _sha256(destination) != expected_sha256:
        raise TrialBundleError("template_destination_conflict")
    return "already_installed"


def build_trial_bundle(output: Path, *, target_name: str) -> Path:
    """Package reviewed patches only; never contact or mutate a tablet."""

    if target_name != "ferrari":
        raise TrialBundleError("chiappa_exact_resource_unverified")
    load_native_api_contract(target_name)
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
        template_destination = staging / "templates"
        template_destination.mkdir()
        template_entries = []
        for name, device_destination in TEMPLATE_ASSETS:
            source = ROOT / "toolbar_launcher" / "templates" / name
            destination = template_destination / name
            shutil.copy2(source, destination)
            destination.chmod(0o644)
            template_entries.append(
                {
                    "name": name,
                    "sha256": _sha256(destination),
                    "size_bytes": destination.stat().st_size,
                    "mode": "0644",
                    "destination": device_destination,
                    "app_owned": True,
                    "rollback_action": "remove_if_hash_matches",
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
            "bridge": {"host": "10.11.99.16", "port": 8765},
            "qmds": entries,
            "templates": template_entries,
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
