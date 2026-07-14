"""Fail-closed fixture composition and rollback for the launcher spike."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .targets import TARGETS, Target


TOOLBAR_START = "    // fixture-region: toolbar:start\n"
TOOLBAR_END = "    // fixture-region: toolbar:end\n"
LAUNCHER_MARKER = 'objectName: "letters-home-launcher"'
KNOWN_UNRELATED_MOD = "fixture-quick-settings-clock-1.qmd"


class PatchError(ValueError):
    """A preflight stop condition with a stable machine-readable code."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class TabletSnapshot:
    target: str
    model: str
    os_version: str
    source_path: str
    source: bytes
    active_qmds: tuple[str, ...]
    appload_version: str | None
    xovi_version: str


@dataclass(frozen=True)
class RollbackManifest:
    target: str
    source_path: str
    active_qmds: tuple[str, ...]
    preinstall_sha256: str
    installed_sha256: str


@dataclass(frozen=True)
class PatchResult:
    target: Target
    phase: str
    preinstall: bytes
    installed: bytes
    rollback: RollbackManifest


def _sha256(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def _replace_once(contents: str, old: str, new: str) -> str:
    if contents.count(old) != 1:
        raise PatchError("fixture_locator_mismatch")
    return contents.replace(old, new, 1)


def _validate_snapshot(snapshot: TabletSnapshot) -> Target:
    try:
        target = TARGETS[snapshot.target]
    except KeyError as error:
        raise PatchError("wrong_model") from error

    if LAUNCHER_MARKER.encode() in snapshot.source:
        raise PatchError("duplicate_install")
    if snapshot.model != target.model:
        raise PatchError("wrong_model")
    if snapshot.os_version != target.os_version:
        raise PatchError("wrong_os")
    if snapshot.source_path != target.resource_path:
        raise PatchError("wrong_resource_path")
    if _sha256(snapshot.source) != target.resource_sha256:
        raise PatchError("wrong_source_hash")
    if snapshot.appload_version is None or target.active_qmd_order[0] not in snapshot.active_qmds:
        raise PatchError("missing_appload")
    if snapshot.appload_version != target.appload_version:
        raise PatchError("wrong_appload_version")
    if snapshot.xovi_version != target.xovi_version:
        raise PatchError("wrong_xovi_version")

    known = set(target.active_qmd_order) | {KNOWN_UNRELATED_MOD}
    if any(mod not in known for mod in snapshot.active_qmds):
        raise PatchError("unknown_active_mod")
    required = tuple(mod for mod in snapshot.active_qmds if mod in target.active_qmd_order)
    if required != target.active_qmd_order:
        raise PatchError("active_mod_order_mismatch")
    return target


def _compose_active_mods(source: bytes, active_qmds: tuple[str, ...]) -> bytes:
    contents = source.decode("utf-8")
    for mod in active_qmds:
        if mod == "appload-0.5.3.qmd":
            contents = _replace_once(
                contents,
                "import QtQuick 2.15\n",
                "import QtQuick 2.15\nimport net.asivery.AppLoad 1.0\n",
            )
        elif mod == "fixture-cjk-font-1.qmd":
            contents = _replace_once(
                contents,
                'property string family: "sans-serif"',
                'property string family: "Noto Sans CJK SC"',
            )
        elif mod == "fixture-cjk-language-1.qmd":
            contents = _replace_once(
                contents,
                'property string locale: "en_US"',
                'property string locale: "zh_CN"',
            )
        elif mod == KNOWN_UNRELATED_MOD:
            # Its declared resource is /qml/QuickSettings.qml, not this resource.
            continue
    return contents.encode("utf-8")


def _launcher_block(phase: str) -> str:
    clicked = "{}"
    if phase == "launch":
        clicked = 'AppLoadLauncher.launchApplication("letters-home", [], {}, false)'
    return (
        "\n"
        "            ToolButton {\n"
        "                id: lettersHomeLauncher\n"
        '                objectName: "letters-home-launcher"\n'
        '                iconSource: "qrc:/letters-home/icons/letter"\n'
        '                accessibleName: "Open Letters Home"\n'
        f"                onClicked: {clicked}\n"
        "            }\n"
    )


def _patch_toolbar(preinstall: bytes, phase: str) -> bytes:
    contents = preinstall.decode("utf-8")
    if contents.count(TOOLBAR_START) != 1 or contents.count(TOOLBAR_END) != 1:
        raise PatchError("fixture_locator_mismatch")
    start = contents.index(TOOLBAR_START) + len(TOOLBAR_START)
    end = contents.index(TOOLBAR_END)
    toolbar = contents[start:end]
    locator = 'property string modelSource: "toolbarProvider.editingTools"'
    anchor = "            // letters-home-insertion-point\n"
    if toolbar.count(locator) != 1 or toolbar.count(anchor) != 1:
        raise PatchError("fixture_locator_mismatch")
    patched_toolbar = toolbar.replace(anchor, _launcher_block(phase) + anchor, 1)
    return (contents[:start] + patched_toolbar + contents[end:]).encode("utf-8")


def apply_toolbar_patch(
    snapshot: TabletSnapshot,
    *,
    phase: str = "inert",
    visual_stability_confirmed: bool = False,
) -> PatchResult:
    """Compose fixture mods and add exactly one staged launcher button."""

    target = _validate_snapshot(snapshot)
    if phase not in {"inert", "launch"}:
        raise PatchError("unknown_phase")
    if phase == "launch" and not visual_stability_confirmed:
        raise PatchError("visual_confirmation_required")

    preinstall = _compose_active_mods(snapshot.source, snapshot.active_qmds)
    installed = _patch_toolbar(preinstall, phase)
    rollback = RollbackManifest(
        target=target.codename,
        source_path=target.resource_path,
        active_qmds=snapshot.active_qmds,
        preinstall_sha256=_sha256(preinstall),
        installed_sha256=_sha256(installed),
    )
    return PatchResult(target, phase, preinstall, installed, rollback)


def uninstall_toolbar_patch(installed: bytes, result: PatchResult) -> bytes:
    """Restore only when the installed bytes still match the rollback record."""

    if _sha256(installed) != result.rollback.installed_sha256:
        raise PatchError("installed_resource_changed")
    if _sha256(result.preinstall) != result.rollback.preinstall_sha256:
        raise PatchError("rollback_unavailable")
    return result.preinstall
