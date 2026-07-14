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
from toolbar_launcher.launcher import KNOWN_UNRELATED_MOD, TOOLBAR_END, TOOLBAR_START


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


def without_toolbar(contents):
    text = contents.decode("utf-8")
    before, remainder = text.split(TOOLBAR_START, 1)
    _, after = remainder.split(TOOLBAR_END, 1)
    return before + "<toolbar/>" + after


class TargetContractTests(unittest.TestCase):
    def test_ferrari_and_chiappa_are_independent_exact_targets(self):
        self.assertEqual(set(TARGETS), {"ferrari", "chiappa"})
        self.assertIsNot(TARGETS["ferrari"], TARGETS["chiappa"])
        for name, target in TARGETS.items():
            with self.subTest(target=name):
                source = source_for(name)
                self.assertEqual(hashlib.sha256(source).hexdigest(), target.resource_sha256)
                self.assertEqual(target.os_version, "3.28.0.162")
                self.assertEqual(target.resource_path, "/qml/DocumentView.qml")
                self.assertEqual(target.resource_id, "[[2857280009207495592]]")
                self.assertEqual(target.appload_version, "0.5.3")
                self.assertEqual(target.xovi_version, "0.3.3")
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
            self.assertIn("AFFECT [[2857280009207495592]]", patch)
            self.assertIn("toolbarProvider.editingTools", patch)
            self.assertIn(TARGETS["chiappa"].resource_sha256, patch)
        self.assertNotIn("launchApplication", inert)
        self.assertIn(
            'AppLoadLauncher.launchApplication("letters-home", [], {}, false)',
            launch,
        )

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

    def test_matching_targets_change_only_the_toolbar_subtree(self):
        for name in TARGETS:
            with self.subTest(target=name):
                result = apply_toolbar_patch(snapshot_for(name))
                self.assertEqual(without_toolbar(result.preinstall), without_toolbar(result.installed))
                installed = result.installed.decode("utf-8")
                self.assertEqual(installed.count('objectName: "letters-home-launcher"'), 1)
                self.assertIn('objectName: "pen-tool"', installed)
                self.assertIn('objectName: "eraser-tool"', installed)
                self.assertIn('property string family: "Noto Sans CJK SC"', installed)
                self.assertIn('property string locale: "zh_CN"', installed)
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
        self.assertIn(
            'AppLoadLauncher.launchApplication("letters-home", [], {}, false)',
            launched.installed.decode("utf-8"),
        )

    def test_uninstall_restores_byte_identical_preinstall_resource_and_cjk(self):
        result = apply_toolbar_patch(snapshot_for())
        restored = uninstall_toolbar_patch(result.installed, result)
        self.assertEqual(restored, result.preinstall)
        self.assertEqual(hashlib.sha256(restored).hexdigest(), result.rollback.preinstall_sha256)
        self.assertIn(b"Noto Sans CJK SC", restored)
        self.assertIn(b"zh_CN", restored)

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
            b'objectName: "pen-tool"',
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
