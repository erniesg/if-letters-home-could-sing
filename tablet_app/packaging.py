"""Build the source tree into the directory shape consumed by AppLoad."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(__file__).resolve().parent / "appload"
REQUIRED_MANIFEST_FIELDS = {
    "id",
    "name",
    "loadsBackend",
    "entry",
    "canHaveMultipleFrontends",
    "supportsScaling",
}


def validate_source() -> None:
    manifest = json.loads((SOURCE / "manifest.json").read_text())
    if set(manifest) != REQUIRED_MANIFEST_FIELDS:
        raise ValueError("AppLoad manifest fields do not match the maintained contract")
    if manifest["id"] != "letters-home" or manifest["entry"] != "/ui/Main.qml":
        raise ValueError("AppLoad manifest id or entry does not match the QML endpoint")
    if manifest["loadsBackend"] is not True:
        raise ValueError("the fixture app must load its local backend")

    qrc = ET.parse(SOURCE / "application.qrc").getroot()
    aliases = {item.attrib.get("alias") for item in qrc.iter("file")}
    required = {
        "ui/Main.qml",
        "ui/StationeryLayer.qml",
        "ui/InkLayer.qml",
        "ui/MarginaliaLayer.qml",
        "assets/incoming-qiaopi-001.png",
    }
    if not required.issubset(aliases):
        raise ValueError("the Qt resource manifest is missing required UI assets")

    qml = (SOURCE / "ui" / "Main.qml").read_text()
    for contract_fragment in (
        "import net.asivery.AppLoad 1.0",
        'applicationID: "letters-home"',
        "signal close",
        "function unloading()",
    ):
        if contract_fragment not in qml:
            raise ValueError(f"root QML is missing {contract_fragment}")


def build_bundle(output: Path, rcc: str) -> None:
    validate_source()
    if output.exists():
        raise FileExistsError(f"refusing to replace existing output: {output}")
    (output / "backend" / "runtime").mkdir(parents=True)
    shutil.copy2(SOURCE / "manifest.json", output / "manifest.json")
    shutil.copy2(
        ROOT / "fixtures" / "generated" / "incoming-qiaopi-001.png",
        output / "icon.png",
    )
    shutil.copy2(SOURCE / "backend" / "entry", output / "backend" / "entry")
    runtime_app = output / "backend" / "runtime" / "tablet_app"
    runtime_app.mkdir()
    for filename in ("__init__.py", "adapter.py", "protocol.py"):
        shutil.copy2(ROOT / "tablet_app" / filename, runtime_app / filename)
    shutil.copytree(
        ROOT / "experience_core",
        output / "backend" / "runtime" / "experience_core",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    shutil.copytree(
        ROOT / "heart_rate",
        output / "backend" / "runtime" / "heart_rate",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    runtime_contracts = output / "backend" / "runtime" / "contracts"
    shutil.copytree(ROOT / "contracts" / "v1", runtime_contracts / "v1")
    shutil.copy2(
        ROOT / "contracts" / "review.example.json",
        runtime_contracts / "review.example.json",
    )
    subprocess.run(
        [rcc, "--binary", "-o", str(output / "resources.rcc"), str(SOURCE / "application.qrc")],
        cwd=SOURCE,
        check=True,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--rcc", default=shutil.which("rcc") or shutil.which("rcc6"))
    arguments = parser.parse_args(argv)
    try:
        validate_source()
        if arguments.check:
            print("AppLoad source contract is valid")
            return 0
        if not arguments.output:
            parser.error("--output is required unless --check is used")
        if not arguments.rcc:
            print("AppLoad packaging blocked: Qt rcc is unavailable", file=sys.stderr)
            return 2
        build_bundle(arguments.output, arguments.rcc)
    except (FileExistsError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"AppLoad packaging failed: {type(error).__name__}", file=sys.stderr)
        return 1
    print(f"built AppLoad bundle: {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
