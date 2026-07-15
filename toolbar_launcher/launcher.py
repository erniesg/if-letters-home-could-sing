"""Fail-closed fixture composition and rollback for the launcher spike."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .targets import TARGETS, Target


SIDEBAR_START = "    // fixture-region: sidebar:start\n"
SIDEBAR_END = "    // fixture-region: sidebar:end\n"
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
    # The declared AppLoad, CJK, and quick-settings fixtures target resources
    # other than Sidebar.qml. Preserve their order in rollback metadata without
    # inventing changes to this resource.
    for mod in active_qmds:
        if mod not in {*TARGETS["chiappa"].active_qmd_order, KNOWN_UNRELATED_MOD}:
            raise PatchError("unknown_active_mod")
    return source


def _launcher_block(phase: str) -> str:
    clicked = "{}"
    if phase == "launch":
        clicked = """{
                lettersHomeLauncher.enabled = false;
                lettersHomeLauncher.text = "Preparing letter…";
                lettersHomeLaunchWatchdog.restart();
                const request = new XMLHttpRequest();
                request.open("POST", "http://10.11.99.16:8765/v1/sessions/start");
                request.setRequestHeader("Content-Type", "application/json");
                request.onreadystatechange = function() {
                    if (request.readyState !== XMLHttpRequest.DONE) {
                        return;
                    }
                    if (request.status !== 200) {
                        lettersHomeLauncher.failLaunch("mac_bridge_unavailable");
                        return;
                    }
                    const response = JSON.parse(request.responseText);
                    lettersHomeLauncher.sessionId = response.session_id;
                    lettersHomeLauncher.requestSeed();
                };
                request.send(JSON.stringify({ profile_id: "ferrari_3.28.0.162" }));
            }"""
    native_support = ""
    if phase == "launch":
        native_support = """
            property string sessionId: ""
            property string documentId: ""
            property int readinessAttempts: 0

            function failLaunch(reason) {
                lettersHomeReadyTimer.stop();
                lettersHomeLaunchWatchdog.stop();
                console.warn("[LettersHome] native launch failed", reason);
                text = "Letters Home";
                enabled = true;
            }

            function requestSeed() {
                const request = new XMLHttpRequest();
                request.open("GET", "http://10.11.99.16:8765/v1/notebook-seed");
                request.onreadystatechange = function() {
                    if (request.readyState !== XMLHttpRequest.DONE) return;
                    if (request.status !== 200) {
                        lettersHomeLauncher.failLaunch("mac_bridge_unavailable");
                        return;
                    }
                    const response = JSON.parse(request.responseText);
                    root.windowNavigator.open("library-ui/window/create-notebook", {
                        currentFolderId: NavigationManager.activeContext.explorer.currentFolderId,
                        lettersHomeSeed: response.status !== "ready",
                        lettersHomeClone: response.status === "ready",
                        lettersHomeSeedDocumentId: response.document_id || "",
                        lettersHomeDocumentName: "Letters Home " + sessionId,
                        onCreated: function(createdId) {
                            lettersHomeLauncher.documentId = createdId;
                            lettersHomeReadyTimer.start();
                        },
                        onFailed: function(reason) {
                            lettersHomeLauncher.failLaunch(reason);
                        }
                    });
                };
                request.send();
            }

            function postBinding(document) {
                const bindRequest = new XMLHttpRequest();
                bindRequest.open("POST", "http://10.11.99.16:8765/v1/sessions/bind");
                bindRequest.setRequestHeader("Content-Type", "application/json");
                bindRequest.onreadystatechange = function() {
                    if (bindRequest.readyState !== XMLHttpRequest.DONE) return;
                    if (bindRequest.status !== 200) {
                        lettersHomeLauncher.failLaunch("native_bind_failed");
                        return;
                    }
                    lettersHomeLauncher.text = "Letters Home";
                    lettersHomeLauncher.enabled = true;
                    lettersHomeLaunchWatchdog.stop();
                    root.toggle();
                    root.windowNavigator.open("legacydevice/window/main", {
                        documentId: lettersHomeLauncher.documentId
                    });
                };
                bindRequest.send(JSON.stringify({
                    session_id: sessionId,
                    document_id: documentId,
                    incoming_page_id: document.idForPage(0),
                    reply_page_id: document.idForPage(1)
                }));
            }

            Timer {
                id: lettersHomeReadyTimer
                interval: 250
                repeat: true
                onTriggered: {
                    lettersHomeLauncher.readinessAttempts += 1;
                    const document = Library.entryForId(lettersHomeLauncher.documentId);
                    if (document && document.pageCount >= 2) {
                        stop();
                        lettersHomeLauncher.postBinding(document);
                    } else if (lettersHomeLauncher.readinessAttempts >= 20) {
                        lettersHomeLauncher.failLaunch("native_notebook_not_ready");
                    }
                }
            }

            Timer {
                id: lettersHomeLaunchWatchdog
                interval: 2000
                repeat: false
                onTriggered: lettersHomeLauncher.failLaunch("native_launch_timeout")
            }
"""
    return (
        "\n"
        "        ArkControls.SidebarItem {\n"
        "            id: lettersHomeLauncher\n"
        '            objectName: "letters-home-launcher"\n'
        '            text: qsTr("Letters Home")\n'
        '            iconSource: "qrc:/letters-home/icons/letter"\n'
        "            highlighted: false\n"
        "            enabled: true\n"
        "            Layout.preferredHeight: Common.Values.navigatorSidebarItemHeight\n"
        "            Layout.preferredWidth: parent.width\n"
        f"            onClicked: {clicked}\n"
        f"{native_support}"
        "        }\n"
    )


def _patch_sidebar(preinstall: bytes, phase: str) -> bytes:
    contents = preinstall.decode("utf-8")
    if contents.count(SIDEBAR_START) != 1 or contents.count(SIDEBAR_END) != 1:
        raise PatchError("fixture_locator_mismatch")
    start = contents.index(SIDEBAR_START) + len(SIDEBAR_START)
    end = contents.index(SIDEBAR_END)
    sidebar = contents[start:end]
    locator = "        id: filterColumn\n"
    anchor = "        // letters-home-insertion-point\n"
    integrations = "            id: integrations\n"
    if (
        sidebar.count(locator) != 1
        or sidebar.count(anchor) != 1
        or sidebar.count(integrations) != 1
    ):
        raise PatchError("fixture_locator_mismatch")
    if sidebar.index(anchor) < sidebar.index(integrations):
        raise PatchError("fixture_locator_mismatch")
    patched_sidebar = sidebar.replace(anchor, _launcher_block(phase) + anchor, 1)
    patched = contents[:start] + patched_sidebar + contents[end:]
    return patched.encode("utf-8")


def apply_toolbar_patch(
    snapshot: TabletSnapshot,
    *,
    phase: str = "inert",
    visual_stability_confirmed: bool = False,
) -> PatchResult:
    """Compose fixture mods and add one staged home-sidebar launcher item."""

    target = _validate_snapshot(snapshot)
    if phase not in {"inert", "launch"}:
        raise PatchError("unknown_phase")
    if phase == "launch" and not visual_stability_confirmed:
        raise PatchError("visual_confirmation_required")

    preinstall = _compose_active_mods(snapshot.source, snapshot.active_qmds)
    installed = _patch_sidebar(preinstall, phase)
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
