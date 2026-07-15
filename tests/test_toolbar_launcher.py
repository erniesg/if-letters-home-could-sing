import hashlib
import unittest
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

from toolbar_launcher import (
    TARGETS,
    PatchError,
    TabletSnapshot,
    apply_toolbar_patch,
    uninstall_toolbar_patch,
)
from toolbar_launcher.launcher import KNOWN_UNRELATED_MOD


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "toolbar_launcher"


def source_for(target_name):
    return (PACKAGE / TARGETS[target_name].fixture_path).read_bytes()


def snapshot_for(target_name="chiappa", **changes):
    target = TARGETS[target_name]
    values = {
        "target": target_name,
        "model": target.model,
        "os_version": target.os_version,
        "source_path": target.resource_path,
        "source": source_for(target_name),
        "active_qmds": target.active_qmd_order,
        "appload_version": target.appload_version,
        "xovi_version": target.xovi_version,
    }
    values.update(changes)
    return TabletSnapshot(**values)


SIDEBAR_START = "    // fixture-region: sidebar:start\n"
SIDEBAR_END = "    // fixture-region: sidebar:end\n"


def without_sidebar(contents):
    text = contents.decode("utf-8")
    before, remainder = text.split(SIDEBAR_START, 1)
    _, after = remainder.split(SIDEBAR_END, 1)
    return before + "<sidebar/>" + after


class TargetContractTests(unittest.TestCase):
    def test_ferrari_and_chiappa_are_independent_exact_targets(self):
        self.assertEqual(set(TARGETS), {"ferrari", "chiappa"})
        self.assertIsNot(TARGETS["ferrari"], TARGETS["chiappa"])
        for name, target in TARGETS.items():
            with self.subTest(target=name):
                source = source_for(name)
                self.assertEqual(hashlib.sha256(source).hexdigest(), target.resource_sha256)
                self.assertEqual(
                    target.backed_up_resource_sha256,
                    "5cfd661e6c68c343513d9ca034042ee3f5cdc3ab0df77ea0396838c77135adc0",
                )
                self.assertEqual(target.os_version, "3.28.0.162")
                self.assertEqual(
                    target.resource_path,
                    "/qml/device/view/navigator/Sidebar.qml",
                )
                self.assertEqual(target.resource_id, "[[4911547370760691430]]")
                self.assertEqual(Path(target.fixture_path).name, "Sidebar.qml")
                self.assertEqual(target.appload_version, "0.5.3")
                self.assertEqual(target.xovi_version, "0.3.3")
                self.assertEqual(
                    target.xochitl_sha256,
                    {
                        "chiappa": "9e3e0372a15da25b148ac17667feb566014440e079c3e3ee504112d556ad2e10",
                        "ferrari": "10082aeb857c69c3f404ab189d7403318ba97d0c169e756ae9a5b3532b248a4a",
                    }[name],
                )
                self.assertEqual(
                    target.hashtab_sha256,
                    {
                        "chiappa": "313aaf72896b152c7668bcd83fa9ed23e1c5b9d24eacc1a34bebf66ce66d68b1",
                        "ferrari": "ebbb415d5e875a67a84416c3029e6ce7e94861a32bb8d390fd01fe0403d492cd",
                    }[name],
                )
                self.assertEqual(
                    target.active_qmd_order,
                    (
                        "appload-0.5.3.qmd",
                        "fixture-cjk-font-1.qmd",
                        "fixture-cjk-language-1.qmd",
                    ),
                )

    def test_qmldiff_artifacts_are_version_and_resource_hash_pinned(self):
        inert = (PACKAGE / "qmldiff" / "10-letters-home-inert.qmd").read_text()
        launch = (PACKAGE / "qmldiff" / "20-letters-home-launch.qmd").read_text()
        for patch in (inert, launch):
            self.assertIn("VERSION 3.28.0.162", patch)
            self.assertIn("AFFECT [[4911547370760691430]]", patch)
            self.assertIn(
                "[[8397993708429497603]] > "
                "[[14125623155555875541]]#[[15885405667098360701]]",
                patch,
            )
            self.assertIn(TARGETS["chiappa"].resource_sha256, patch)
            self.assertNotIn("toolbarProvider.editingTools", patch)
            self.assertNotIn("[[2857280009207495592]]", patch)
            self.assertNotIn("[[3819512207256720568]]", patch)
        self.assertIn(
            "LOCATE AFTER [[5882927607508357618]]#[[16045040163728568448]]",
            inert,
        )
        self.assertIn("[[5882927607508357618]]#lettersHomeLauncher", launch)
        self.assertIn("~&6504315758&~", inert)  # text
        self.assertIn("~&484431552542639914&~", inert)  # highlighted
        self.assertNotIn("~&214642559243&~", inert)  # title
        self.assertNotIn("~&11921478716705041271&~", inert)  # navigationHandler
        self.assertNotIn("launchApplication", inert)
        self.assertNotIn("AppLoadLauncher", launch)
        self.assertNotIn("launchApplication", launch)
        self.assertIn("http://10.11.99.2:8765/v1/sessions/start", launch)
        self.assertIn("legacydevice/window/main", launch)

    def test_open_document_toolbar_fixture_is_not_a_launcher_target(self):
        self.assertFalse(any((PACKAGE / "fixtures").glob("*/DocumentView.qml")))
        self.assertNotIn("DocumentView.qml", TARGETS["chiappa"].fixture_path)

    def test_launcher_icon_has_the_expected_qt_resource_alias(self):
        qrc = ET.parse(PACKAGE / "qmldiff" / "letter-icon.qrc").getroot()
        resource = qrc.find("qresource")
        item = resource.find("file")
        self.assertEqual(resource.attrib["prefix"], "/letters-home/icons")
        self.assertEqual(item.attrib["alias"], "letter")
        self.assertTrue((PACKAGE / "qmldiff" / item.text).is_file())


class FixturePatchTests(unittest.TestCase):
    def assert_error(self, code, snapshot, **options):
        with self.assertRaises(PatchError) as context:
            apply_toolbar_patch(snapshot, **options)
        self.assertEqual(context.exception.code, code)

    def test_matching_targets_change_only_the_main_sidebar_subtree(self):
        for name in TARGETS:
            with self.subTest(target=name):
                result = apply_toolbar_patch(snapshot_for(name))
                self.assertEqual(
                    without_sidebar(result.preinstall),
                    without_sidebar(result.installed),
                )
                installed = result.installed.decode("utf-8")
                self.assertEqual(installed.count('objectName: "letters-home-launcher"'), 1)
                self.assertIn("FocusScope {", installed)
                self.assertIn('objectName: "filterMyFiles"', installed)
                self.assertIn('objectName: "filterTags"', installed)
                self.assertIn('objectName: "integrations"', installed)
                self.assertIn('objectName: "filterTrashed"', installed)
                self.assertLess(
                    installed.index('objectName: "integrations"'),
                    installed.index('objectName: "letters-home-launcher"'),
                )
                self.assertLess(
                    installed.index('objectName: "letters-home-launcher"'),
                    installed.index('objectName: "filterTrashed"'),
                )
                self.assertIn('text: qsTr("Letters Home")', installed)
                self.assertIn(
                    "Layout.preferredHeight: Common.Values.navigatorSidebarItemHeight",
                    installed,
                )
                self.assertNotIn('title: qsTr("Letters Home")', installed)
                self.assertNotIn("toolbarProvider.editingTools", installed)
                self.assertNotIn("launchApplication", installed)

    def test_patch_is_deterministic_and_unrelated_mods_remain_unmodified(self):
        baseline = apply_toolbar_patch(snapshot_for())
        with_unrelated = apply_toolbar_patch(
            snapshot_for(active_qmds=TARGETS["chiappa"].active_qmd_order + (KNOWN_UNRELATED_MOD,))
        )
        repeated = apply_toolbar_patch(snapshot_for())
        self.assertEqual(baseline.installed, repeated.installed)
        self.assertEqual(baseline.installed, with_unrelated.installed)

    def test_launch_phase_requires_visual_stability_confirmation(self):
        snapshot = snapshot_for()
        self.assert_error("visual_confirmation_required", snapshot, phase="launch")
        launched = apply_toolbar_patch(
            snapshot,
            phase="launch",
            visual_stability_confirmed=True,
        )
        self.assertEqual(launched.phase, "launch")
        installed = launched.installed.decode("utf-8")
        self.assertIn("http://10.11.99.2:8765/v1/sessions/start", installed)
        self.assertIn("legacydevice/window/main", installed)
        self.assertNotIn("AppLoadLauncher", installed)

    def test_uninstall_restores_byte_identical_preinstall_sidebar(self):
        result = apply_toolbar_patch(snapshot_for())
        restored = uninstall_toolbar_patch(result.installed, result)
        self.assertEqual(restored, result.preinstall)
        self.assertEqual(hashlib.sha256(restored).hexdigest(), result.rollback.preinstall_sha256)
        self.assertIn(b'objectName: "filterMyFiles"', restored)
        self.assertNotIn(b'objectName: "letters-home-launcher"', restored)

    def test_uninstall_stops_if_installed_resource_changed(self):
        result = apply_toolbar_patch(snapshot_for())
        with self.assertRaises(PatchError) as context:
            uninstall_toolbar_patch(result.installed + b"\n", result)
        self.assertEqual(context.exception.code, "installed_resource_changed")

    def test_preflight_refusal_matrix(self):
        target = TARGETS["chiappa"]
        cases = {
            "wrong_model": snapshot_for(model=TARGETS["ferrari"].model),
            "wrong_os": snapshot_for(os_version="3.28.0.163"),
            "wrong_resource_path": snapshot_for(source_path="/qml/Other.qml"),
            "wrong_source_hash": snapshot_for(source=source_for("chiappa") + b"\n"),
            "missing_appload": snapshot_for(
                active_qmds=target.active_qmd_order[1:],
                appload_version=None,
            ),
            "wrong_appload_version": snapshot_for(appload_version="0.5.2"),
            "wrong_xovi_version": snapshot_for(xovi_version="0.3.2"),
            "unknown_active_mod": snapshot_for(
                active_qmds=target.active_qmd_order + ("unknown-toolbar.qmd",)
            ),
            "active_mod_order_mismatch": snapshot_for(
                active_qmds=(
                    target.active_qmd_order[0],
                    target.active_qmd_order[2],
                    target.active_qmd_order[1],
                )
            ),
        }
        duplicate = source_for("chiappa").replace(
            b'objectName: "filterMyFiles"',
            b'objectName: "letters-home-launcher"',
            1,
        )
        cases["duplicate_install"] = snapshot_for(source=duplicate)

        for code, snapshot in cases.items():
            with self.subTest(code=code):
                self.assert_error(code, snapshot)

    def test_target_records_cannot_be_interchanged_even_with_equal_bytes(self):
        ferrari = snapshot_for("ferrari")
        self.assert_error(
            "wrong_model",
            replace(ferrari, target="chiappa"),
        )


if __name__ == "__main__":
    unittest.main()
