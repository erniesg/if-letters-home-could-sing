"""Independent, fixture-pinned launcher targets for the two tablets."""

from __future__ import annotations

from dataclasses import dataclass


OS_VERSION = "3.28.0.162"
RESOURCE_PATH = "/qml/device/view/navigator/Sidebar.qml"
RESOURCE_ID = "[[4911547370760691430]]"
# Sanitized fixture bytes are intentionally distinct from proprietary source.
RESOURCE_SHA256 = "03d6744e13fab8b4d268029e4b9529d90f71196e4a5f3caf68e990edaf522578"
BACKED_UP_RESOURCE_SHA256 = "5cfd661e6c68c343513d9ca034042ee3f5cdc3ab0df77ea0396838c77135adc0"
APPLOAD_VERSION = "0.5.3"
XOVI_VERSION = "0.3.3"
QMLDIFF_COMMIT = "25681c3cc7addb93fdbb41ceac1f1bdce8b2625d"
QRR_COMMIT = "7874154dba6793cc68a15fae0fb9dd272c4ed20a"
ACTIVE_QMD_ORDER = (
    "appload-0.5.3.qmd",
    "fixture-cjk-font-1.qmd",
    "fixture-cjk-language-1.qmd",
)


@dataclass(frozen=True)
class Target:
    codename: str
    model: str
    fixture_path: str
    xochitl_sha256: str
    hashtab_sha256: str
    os_version: str = OS_VERSION
    resource_path: str = RESOURCE_PATH
    resource_id: str = RESOURCE_ID
    resource_sha256: str = RESOURCE_SHA256
    backed_up_resource_sha256: str = BACKED_UP_RESOURCE_SHA256
    appload_version: str = APPLOAD_VERSION
    xovi_version: str = XOVI_VERSION
    qmldiff_commit: str = QMLDIFF_COMMIT
    qrr_commit: str = QRR_COMMIT
    active_qmd_order: tuple[str, ...] = ACTIVE_QMD_ORDER


# Keep independent records even while sanitized and recovered sidebar bytes match.
TARGETS = {
    "chiappa": Target(
        codename="chiappa",
        model="reMarkable Paper Pro (Chiappa)",
        fixture_path="fixtures/chiappa/Sidebar.qml",
        xochitl_sha256="9e3e0372a15da25b148ac17667feb566014440e079c3e3ee504112d556ad2e10",
        hashtab_sha256="313aaf72896b152c7668bcd83fa9ed23e1c5b9d24eacc1a34bebf66ce66d68b1",
    ),
    "ferrari": Target(
        codename="ferrari",
        model="reMarkable Paper Pro Move (Ferrari)",
        fixture_path="fixtures/ferrari/Sidebar.qml",
        xochitl_sha256="10082aeb857c69c3f404ab189d7403318ba97d0c169e756ae9a5b3532b248a4a",
        hashtab_sha256="ebbb415d5e875a67a84416c3029e6ce7e94861a32bb8d390fd01fe0403d492cd",
    ),
}
