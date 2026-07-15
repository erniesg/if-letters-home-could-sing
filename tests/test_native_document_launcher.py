import unittest
import json
import tempfile
from pathlib import Path

from toolbar_launcher import TARGETS, TabletSnapshot, apply_toolbar_patch


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "toolbar_launcher"


def source_for(target_name):
    return (PACKAGE / TARGETS[target_name].fixture_path).read_bytes()


def snapshot_for(target_name="ferrari"):
    target = TARGETS[target_name]
    return TabletSnapshot(
        target=target_name,
        model=target.model,
        os_version=target.os_version,
        source_path=target.resource_path,
        source=source_for(target_name),
        active_qmds=target.active_qmd_order,
        appload_version=target.appload_version,
        xovi_version=target.xovi_version,
    )


class NativeLauncherContractTests(unittest.TestCase):
    def test_ferrari_trial_bundle_pins_every_native_qmd_and_refuses_chiappa(self):
        from mac_bridge.trial_bundle import TrialBundleError, build_trial_bundle

        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "trial"
            manifest_path = build_trial_bundle(output, target_name="ferrari")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            bundled = output / "qmldiff"
            self.assertEqual(
                [entry["name"] for entry in manifest["qmds"]],
                [
                    "10-letters-home-inert.qmd",
                    "20-letters-home-launch.qmd",
                    "30-letters-home-submit.qmd",
                ],
            )
            for entry in manifest["qmds"]:
                self.assertTrue((bundled / entry["name"]).is_file())
                self.assertEqual(len(entry["sha256"]), 64)
            self.assertEqual(
                manifest["document_view"]["resource_id"],
                "[[1224665461898798997]]",
            )
            self.assertTrue(manifest["requires_live_preflight"])

        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(TrialBundleError, "chiappa_exact_resource_unverified"):
                build_trial_bundle(Path(temporary_directory) / "trial", target_name="chiappa")

    def test_sidebar_uses_mac_bridge_then_opens_stock_document_view(self):
        result = apply_toolbar_patch(
            snapshot_for(),
            phase="launch",
            visual_stability_confirmed=True,
        )
        installed = result.installed.decode("utf-8")

        self.assertIn("http://10.11.99.16:8765/v1/sessions/start", installed)
        self.assertIn('root.windowNavigator.open("legacydevice/window/main"', installed)
        self.assertIn("documentId: response.document_id", installed)
        self.assertIn('lettersHomeLauncher.text = "Preparing letter…"', installed)
        self.assertNotIn("Mac unavailable", installed)
        self.assertIn('lettersHomeLauncher.text = "Letters Home"', installed)
        self.assertNotIn("AppLoadLauncher", installed)
        self.assertNotIn("import net.asivery.AppLoad", installed)

    def test_qmldiff_launch_and_submit_patches_never_open_an_appload_window(self):
        launch = (PACKAGE / "qmldiff" / "20-letters-home-launch.qmd").read_text()
        submit = (PACKAGE / "qmldiff" / "30-letters-home-submit.qmd").read_text()

        for patch in (launch, submit):
            self.assertNotIn("AppLoadLauncher", patch)
            self.assertNotIn("launchApplication", patch)
            self.assertNotIn("GesturesWindow", patch)
            self.assertNotIn("window.qml", patch)
        self.assertIn("legacydevice/window/main", launch)
        self.assertIn("/v1/sessions/start", launch)
        self.assertIn("AFFECT [[1224665461898798997]]", submit)
        self.assertIn("/v1/sessions/submit", submit)
        self.assertIn("Letters Home", submit)
        self.assertIn("currentPage", submit)
        self.assertIn("review_page_index", submit)
        self.assertIn('sessionId.substring(sessionId.length - 4).toLowerCase() === ".pdf"', submit)
        self.assertIn(
            "~&233726547792244&~: ~&6504329801&~",
            submit,
        )
        self.assertIn('indexOf("Letters Home Review ") !== 0', submit)

    def test_native_packet_contract_is_full_bleed_on_both_devices(self):
        from mac_bridge.native_packet import packet_spec

        for profile_id, dimensions in {
            "ferrari_3.28.0.162": (1696, 954),
            "chiappa_3.28.0.162": (2160, 1620),
        }.items():
            with self.subTest(profile_id=profile_id):
                packet = packet_spec(profile_id)
                self.assertEqual((packet.width, packet.height), dimensions)
                self.assertEqual([page.kind for page in packet.pages], ["incoming", "huipi"])
                for page in packet.pages:
                    self.assertEqual((page.x, page.y), (0, 0))
                    self.assertEqual((page.width, page.height), dimensions)
                    self.assertEqual(page.chrome_margin, 0)


if __name__ == "__main__":
    unittest.main()
