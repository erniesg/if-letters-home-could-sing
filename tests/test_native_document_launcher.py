import importlib.util
import io
import json
import tempfile
import unittest
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
    def test_only_grounded_high_confidence_corrections_become_red_ellipse_marks(self):
        from mac_bridge.contracts import parse_review
        from mac_bridge.native_packet import correction_marks
        from tests.test_native_codex_bridge import VALID_REVIEW

        review = parse_review(VALID_REVIEW)
        marks = correction_marks(review, width=954, height=1696)

        self.assertEqual(len(marks), 1)
        self.assertEqual(marks[0].shape, "ellipse")
        self.assertEqual(marks[0].color, "#b52222")
        self.assertEqual(marks[0].label, "末")
        self.assertGreater(marks[0].x2, marks[0].x1)
        self.assertGreater(marks[0].y2, marks[0].y1)

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
        self.assertIn('console.warn("[LettersHome] submit failed"', submit)
        self.assertIn("/v1/sessions/", submit)
        self.assertIn("interval: 750", submit)
        self.assertIn("onSessionKeyChanged", submit)
        self.assertIn("index * lettersHomeStream.letterColumnGap - implicitWidth / 2", submit)
        self.assertIn("item/agentMessage/delta", (ROOT / "docs" / "issues" / "010-native-codex-roundtrip.md").read_text())
        self.assertNotIn("MouseArea", submit)
        self.assertNotIn("TapHandler", submit)
        self.assertIn("A reply has arrived", submit)
        self.assertIn("Your ink is safe", submit)
        self.assertNotIn("Try Send to Codex again", submit)
        self.assertIn(
            "~&233726547792244&~: ~&6504329801&~",
            submit,
        )
        self.assertIn('indexOf("Letters Home Review ") !== 0', submit)

    def test_native_packet_contract_is_full_bleed_on_both_devices(self):
        from mac_bridge.native_packet import packet_spec

        for profile_id, dimensions in {
            "ferrari_3.28.0.162": (954, 1696),
            "chiappa_3.28.0.162": (1620, 2160),
        }.items():
            with self.subTest(profile_id=profile_id):
                packet = packet_spec(profile_id)
                self.assertEqual((packet.width, packet.height), dimensions)
                self.assertEqual([page.kind for page in packet.pages], ["incoming", "huipi"])
                for page in packet.pages:
                    self.assertEqual((page.x, page.y), (0, 0))
                    self.assertEqual((page.width, page.height), dimensions)
                    self.assertEqual(page.chrome_margin, 0)

    @unittest.skipUnless(
        importlib.util.find_spec("pypdf") and importlib.util.find_spec("reportlab"),
        "requires the trusted-mac extra",
    )
    def test_ferrari_renderer_emits_two_full_page_portrait_media_boxes(self):
        from pypdf import PdfReader

        from mac_bridge.contracts import Letter
        from mac_bridge.native_packet import NativePacketRenderer

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary = Path(temporary_directory)
            packet = NativePacketRenderer(work_dir=temporary).build_initial_packet(
                Letter("阿妹，见字如面。家中一切安好，勿念。"),
                profile_id="ferrari_3.28.0.162",
            )
            pages = PdfReader(io.BytesIO(packet)).pages

        self.assertEqual(len(pages), 2)
        self.assertEqual(
            [(int(page.mediabox.width), int(page.mediabox.height)) for page in pages],
            [(954, 1696), (954, 1696)],
        )
        self.assertIn("阿", pages[0].extract_text())
        self.assertNotIn("阿", pages[1].extract_text())

    @unittest.skipUnless(
        importlib.util.find_spec("pypdf") and importlib.util.find_spec("reportlab"),
        "requires the trusted-mac extra",
    )
    def test_reviewed_packet_opens_on_full_size_marked_copy_then_response_letter(self):
        from pypdf import PdfReader

        from mac_bridge.contracts import Letter, parse_review
        from mac_bridge.native_packet import NativePacketRenderer
        from tests.test_native_codex_bridge import VALID_REVIEW

        incoming = Letter("阿妹，见字如面。家中一切安好，勿念。")
        with tempfile.TemporaryDirectory() as temporary_directory:
            renderer = NativePacketRenderer(work_dir=Path(temporary_directory))
            source = renderer.build_initial_packet(None, profile_id="ferrari_3.28.0.162")
            reviewed, review_page_index = renderer.build_reviewed_packet(
                source,
                parse_review(VALID_REVIEW),
                profile_id="ferrari_3.28.0.162",
                incoming_letter=incoming,
            )
            pages = PdfReader(io.BytesIO(reviewed)).pages

        self.assertEqual(review_page_index, 2)
        self.assertGreaterEqual(len(pages), 5)
        self.assertIn("阿", pages[0].extract_text())
        self.assertIn("末", pages[2].extract_text())
        self.assertIn("见", pages[3].extract_text())
        self.assertEqual(
            [(int(page.mediabox.width), int(page.mediabox.height)) for page in pages[:4]],
            [(954, 1696)] * 4,
        )


if __name__ == "__main__":
    unittest.main()
