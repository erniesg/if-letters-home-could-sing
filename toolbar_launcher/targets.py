"""Independent, fixture-pinned launcher targets for the two tablets."""

from __future__ import annotations

from dataclasses import dataclass


OS_VERSION = "3.28.0.162"
RESOURCE_PATH = "/qml/DocumentView.qml"
RESOURCE_ID = "[[2857280009207495592]]"
RESOURCE_SHA256 = "095e19d24d23ee8d2cbc67f9a08d3af5a13e27644eb7a361fb6d0aa10f136c4e"
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
    os_version: str = OS_VERSION
    resource_path: str = RESOURCE_PATH
    resource_id: str = RESOURCE_ID
    resource_sha256: str = RESOURCE_SHA256
    appload_version: str = APPLOAD_VERSION
    xovi_version: str = XOVI_VERSION
    qmldiff_commit: str = QMLDIFF_COMMIT
    qrr_commit: str = QRR_COMMIT
    active_qmd_order: tuple[str, ...] = ACTIVE_QMD_ORDER


# These remain separate records even though the backed-up fixture bytes match.
TARGETS = {
    "chiappa": Target(
        codename="chiappa",
        model="reMarkable Paper Pro (Chiappa)",
        fixture_path="fixtures/chiappa/DocumentView.qml",
    ),
    "ferrari": Target(
        codename="ferrari",
        model="reMarkable Paper Pro Move (Ferrari)",
        fixture_path="fixtures/ferrari/DocumentView.qml",
    ),
}
