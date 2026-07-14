"""Exact-source AppLoad adaptation for reMarkable Paper Pro firmware 3.28."""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from typing import Union


APPLOAD_VERSION = "0.5.3"
APPLOAD_COMMIT = "5bb34a362f09f753f18bd6261558f8e2737aacdb"
PAPER_PRO_FIRMWARE = "3.28.0.162"
XOVI_COMMIT = "2b99649f5e4fd6288be7792a8570bd16418adb70"
TOOLCHAIN_IMAGE = (
    "eeems/remarkable-toolchain@"
    "sha256:37699143ba448dc5b55c914a18af93466f5a55fc31cce388ef9efa49e30ed457"
)
SOURCE_DATE_EPOCH = 1779378487
UPSTREAM_QMD_SHA256 = "adb0604ec314bf49a2194e8982df7a865f673561383b43584fa2fd236f433815"
ADAPTED_QMD_SHA256 = "8a15eada28010751f7b4ae50ae8853837335820d3346887478b4b9736c073c6e"
UPSTREAM_RESOURCES_QRC_SHA256 = "ba92f47b52e2af86d33b1953f71f441a7f4fffd26d0ec3e6765c8749d35af70d"
ADAPTED_RESOURCES_QRC_SHA256 = "093e26c241b2b776228de174c0dce1feab5bb46dcc517ea30b2f3b7313191aee"
UPSTREAM_WINDOW_QML_SHA256 = "848b234015d2d8671648b6b661e57cdd3b51d80c537c38cb053e503cf3a95c30"
ADAPTED_WINDOW_QML_SHA256 = "6a16bb0c322ce00fdc960418b85944b3978bbc6706d1e276a26d7108ec787638"
LETTERS_HOME_ICON_SHA256 = "c0437e3f3d8eb9436d3be8be54c5afa86bfd14370a78c3907c16a1803d5ccb30"

_REMOVED_SCREEN_MODE_LOCATOR = (
    "        LOCATE BEFORE [[7081372714662.10578197394989910333]]\n"
)
_PAPER_PRO_ROOT_ITEM_LOCATOR = (
    "        LOCATE AFTER [[8397993708429497603]]#[[7713531976371484]]\n"
)
_OBSOLETE_SIDEBAR_RESOURCE = "AFFECT [[4911547370760691430]]\n"
_END_AFFECT = "END AFFECT\n"
_RCC_END = "</RCC>\n"
_LETTERS_HOME_ICON_RESOURCE = (
    '\t<qresource prefix="/letters-home/icons">\n'
    '\t\t<file alias="letter">icons/letters-home.svg</file>\n'
    "\t</qresource>\n"
)
_WINDOW_CHROME_REPLACEMENTS = (
    (
        "    property bool forceTopBarVisible: false\n",
        "    property bool forceTopBarVisible: false\n"
        '    property bool chromeSuppressed: appName === "Letters Home"\n',
    ),
    (
        "        if(fullscreen && !forceTopBarVisible) {\n",
        "        if(fullscreen && !forceTopBarVisible && !chromeSuppressed) {\n",
    ),
    (
        "        visible: !fullscreen || forceTopBarVisible\n",
        "        visible: !chromeSuppressed && (!fullscreen || forceTopBarVisible)\n",
    ),
)


class AdaptationError(ValueError):
    """Fail-closed refusal for an unexpected upstream runtime source."""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _adapt_text(upstream: str) -> str:
    if _sha256(upstream) != UPSTREAM_QMD_SHA256:
        raise AdaptationError("upstream_qmd_hash_mismatch")

    if upstream.count(_REMOVED_SCREEN_MODE_LOCATOR) != 1:
        raise AdaptationError("screen_mode_locator_mismatch")
    adapted = upstream.replace(
        _REMOVED_SCREEN_MODE_LOCATOR,
        _PAPER_PRO_ROOT_ITEM_LOCATOR,
        1,
    )

    start = adapted.find(_OBSOLETE_SIDEBAR_RESOURCE)
    if start < 0:
        raise AdaptationError("obsolete_sidebar_patch_missing")
    end = adapted.find(_END_AFFECT, start)
    if end < 0:
        raise AdaptationError("obsolete_sidebar_patch_unterminated")
    end += len(_END_AFFECT)
    if adapted[end : end + 2] != "\n\n":
        raise AdaptationError("obsolete_sidebar_patch_boundary_mismatch")
    adapted = adapted[:start] + adapted[end + 2 :]

    if _sha256(adapted) != ADAPTED_QMD_SHA256:
        raise AdaptationError("adapted_qmd_hash_mismatch")
    return adapted


def adapt_resources_qrc(upstream: str) -> str:
    """Add the exact Letters Home envelope alias to AppLoad's resources."""

    if _sha256(upstream) != UPSTREAM_RESOURCES_QRC_SHA256:
        raise AdaptationError("upstream_resources_qrc_hash_mismatch")
    if upstream.count(_RCC_END) != 1:
        raise AdaptationError("upstream_resources_qrc_boundary_mismatch")
    adapted = upstream.replace(
        _RCC_END,
        _LETTERS_HOME_ICON_RESOURCE + _RCC_END,
        1,
    )
    if _sha256(adapted) != ADAPTED_RESOURCES_QRC_SHA256:
        raise AdaptationError("adapted_resources_qrc_hash_mismatch")
    return adapted


def adapt_window_qml(upstream: str) -> str:
    """Suppress AppLoad pull-down chrome only for Letters Home."""

    if _sha256(upstream) != UPSTREAM_WINDOW_QML_SHA256:
        raise AdaptationError("upstream_window_qml_hash_mismatch")
    adapted = upstream
    for old, new in _WINDOW_CHROME_REPLACEMENTS:
        if adapted.count(old) != 1:
            raise AdaptationError("upstream_window_qml_boundary_mismatch")
        adapted = adapted.replace(old, new, 1)
    if _sha256(adapted) != ADAPTED_WINDOW_QML_SHA256:
        raise AdaptationError("adapted_window_qml_hash_mismatch")
    return adapted


def prepare_source_tree(source: Path, icon: Path, output: Path) -> Path:
    """Copy an exact upstream tree and apply the reviewed adaptations."""

    if output.exists():
        raise FileExistsError(f"refusing to replace existing output: {output}")
    if hashlib.sha256(icon.read_bytes()).hexdigest() != LETTERS_HOME_ICON_SHA256:
        raise AdaptationError("letters_home_icon_hash_mismatch")

    upstream_qmd = source / "xovi" / "template" / "appload.qmd"
    upstream_qrc = source / "resources" / "resources.qrc"
    upstream_window = source / "resources" / "qml" / "window.qml"
    adapted_qmd = _adapt_text(upstream_qmd.read_text(encoding="utf-8"))
    adapted_qrc = adapt_resources_qrc(upstream_qrc.read_text(encoding="utf-8"))
    adapted_window = adapt_window_qml(upstream_window.read_text(encoding="utf-8"))

    shutil.copytree(
        source,
        output,
        ignore=shutil.ignore_patterns(".git", "temporary", "appload.so"),
    )
    (output / "xovi" / "template" / "appload.qmd").write_text(
        adapted_qmd,
        encoding="utf-8",
    )
    (output / "resources" / "resources.qrc").write_text(
        adapted_qrc,
        encoding="utf-8",
    )
    (output / "resources" / "qml" / "window.qml").write_text(
        adapted_window,
        encoding="utf-8",
    )
    icon_destination = output / "resources" / "icons" / "letters-home.svg"
    icon_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(icon, icon_destination)
    for resource_path in (output / "resources").rglob("*"):
        if resource_path.is_file():
            os.utime(resource_path, (SOURCE_DATE_EPOCH, SOURCE_DATE_EPOCH))
    return output


def adapt_qmd(
    source: Union[str, Path], output: Path | None = None
) -> str | Path:
    """Adapt exact AppLoad source text, or write it to a new output path."""

    if isinstance(source, Path):
        upstream = source.read_text(encoding="utf-8")
    else:
        if output is not None:
            raise TypeError("an output path requires a Path source")
        upstream = source

    adapted = _adapt_text(upstream)
    if output is None:
        return adapted
    if output.exists():
        raise FileExistsError(f"refusing to replace existing output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(adapted, encoding="utf-8")
    return output
