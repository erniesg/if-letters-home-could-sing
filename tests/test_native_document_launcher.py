import unittest
import hashlib
import io
import json
import tempfile
from pathlib import Path
from unittest import mock

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
    def test_ferrari_template_is_native_full_size_and_declares_the_10_by_18_grid(self):
        template_path = (
            ROOT / "toolbar_launcher" / "templates" / "letters-home-ferrari.template"
        )
        self.assertTrue(template_path.is_file(), "native Ferrari template is missing")
        template = json.loads(template_path.read_text(encoding="utf-8"))
        constants = {
            next(iter(item)): next(iter(item.values()))
            for item in template["constants"]
        }

        self.assertEqual(template["name"], "Letters Home")
        self.assertEqual(template["formatVersion"], 1)
        self.assertEqual(template["orientation"], "portrait")
        self.assertEqual(
            {
                key: constants[key]
                for key in (
                    "targetWidth",
                    "targetHeight",
                    "gridColumns",
                    "gridRows",
                    "gridLeft",
                    "gridTop",
                    "gridRight",
                    "gridBottom",
                )
            },
            {
                "targetWidth": 954,
                "targetHeight": 1696,
                "gridColumns": 10,
                "gridRows": 18,
                "gridLeft": 72,
                "gridTop": 104,
                "gridRight": 882,
                "gridBottom": 1592,
            },
        )
        item_ids = {item.get("id") for item in template["items"]}
        self.assertTrue(
            {"paper", "fold-memory", "border", "vertical-guides", "horizontal-guides"}.issubset(
                item_ids
            )
        )

    def test_ferrari_native_notebook_api_contract_pins_required_resources_and_symbols(self):
        contract_path = (
            ROOT / "contracts" / "native-notebook-api.ferrari-3.28.0.162.json"
        )
        self.assertTrue(contract_path.is_file(), "native notebook API contract is missing")
        contract = json.loads(contract_path.read_text(encoding="utf-8"))

        self.assertEqual(contract["os_version"], "3.28.0.162")
        self.assertEqual(
            contract["hashtab_sha256"],
            TARGETS["ferrari"].hashtab_sha256,
        )
        self.assertEqual(
            contract["resources"],
            {
                "sidebar": "[[4911547370760691430]]",
                "document_view": "[[1224665461898798997]]",
                "create_notebook": "[[8651031636888757197]]",
                "create_notebook_window": "[[16344100773210839301]]",
                "pages": "[[4530443761526121003]]",
                "pages_actions": "[[11797611520953530268]]",
            },
        )
        self.assertEqual(
            contract["symbols"]["LibraryController.createDocument"],
            "[[16080285492618834883]]",
        )
        self.assertEqual(
            contract["symbols"]["DocumentController.addPageWithTemplateAndPageSize"],
            "[[14285801537390842371]]",
        )
        self.assertEqual(
            contract["symbols"]["DocumentController.setTemplateForPage"],
            "[[7540657167845513638]]",
        )
        self.assertEqual(
            contract["symbols"]["createNotebookFromExistingPages"],
            "[[5450413349604854157]]",
        )
        self.assertEqual(
            contract["symbols"]["DocumentController.copyPages"],
            "[[12188519148798835813]]",
        )
        self.assertEqual(
            contract["symbols"]["document.idForPage"],
            "[[532004573879022759]]",
        )
        self.assertEqual(
            contract["symbols"]["NavigationManager.activeContext.explorer.currentFolderId"],
            "[[7073776824345929404]]",
        )
        self.assertEqual(
            contract["recovered_source_sha256"]["pages_actions"],
            "c920f49ff948a4ecff63ff9da8c62b5ea5249623d8f777d8551aa4ea299c8a9d",
        )

    def test_native_notebook_api_loader_rejects_unverified_target_and_hash(self):
        from mac_bridge import trial_bundle

        self.assertTrue(
            hasattr(trial_bundle, "load_native_api_contract"),
            "native notebook API loader is missing",
        )
        with self.assertRaisesRegex(
            trial_bundle.TrialBundleError,
            "native_notebook_api_unverified",
        ):
            trial_bundle.load_native_api_contract("chiappa")

        with tempfile.TemporaryDirectory() as temporary_directory:
            contract_path = Path(temporary_directory) / "contract.json"
            contract_path.write_text(
                json.dumps(
                    {
                        "target": "ferrari",
                        "os_version": "3.28.0.162",
                        "hashtab_sha256": "0" * 64,
                        "resources": {},
                        "symbols": {},
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.dict(
                trial_bundle.NATIVE_API_CONTRACTS,
                {"ferrari": contract_path},
                clear=True,
            ):
                with self.assertRaisesRegex(
                    trial_bundle.TrialBundleError,
                    "native_notebook_api_unverified",
                ):
                    trial_bundle.load_native_api_contract("ferrari")

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
            self.assertEqual(len(manifest["templates"]), 1)
            template = manifest["templates"][0]
            self.assertEqual(template["name"], "letters-home-ferrari.template")
            self.assertEqual(template["mode"], "0644")
            self.assertTrue(template["app_owned"])
            self.assertEqual(template["rollback_action"], "remove_if_hash_matches")
            self.assertEqual(
                template["destination"],
                "/usr/share/remarkable/templates/letters-home-ferrari.template",
            )
            bundled_template = output / "templates" / template["name"]
            self.assertTrue(bundled_template.is_file())
            self.assertEqual(template["sha256"], hashlib.sha256(bundled_template.read_bytes()).hexdigest())
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
        self.assertIn("http://10.11.99.16:8765/v1/sessions/bind", installed)
        self.assertIn("LibraryController.createDocument", installed)
        self.assertIn("DocumentController.setTemplateForPage", installed)
        self.assertIn("DocumentController.addPageWithTemplateAndPageSize", installed)
        self.assertIn('"letters-home-ferrari"', installed)
        self.assertIn("document.idForPage(0)", installed)
        self.assertIn("document.idForPage(1)", installed)
        self.assertIn('root.windowNavigator.open("legacydevice/window/main"', installed)
        self.assertIn("documentId: lettersHomeLauncher.documentId", installed)
        self.assertIn('lettersHomeLauncher.text = "Preparing letter…"', installed)
        self.assertNotIn("Mac unavailable", installed)
        self.assertIn('lettersHomeLauncher.text = "Letters Home"', installed)
        self.assertNotIn("response.document_id", installed)
        self.assertNotIn("upload", installed.lower())
        self.assertNotIn("AppLoadLauncher", installed)
        self.assertNotIn("import net.asivery.AppLoad", installed)

    def test_qmldiff_runs_one_native_notebook_without_replacing_stock_input(self):
        launch = (PACKAGE / "qmldiff" / "20-letters-home-launch.qmd").read_text()
        submit = (PACKAGE / "qmldiff" / "30-letters-home-submit.qmd").read_text()

        for patch in (launch, submit):
            self.assertNotIn("AppLoadLauncher", patch)
            self.assertNotIn("launchApplication", patch)
            self.assertNotIn("GesturesWindow", patch)
            self.assertNotIn("window.qml", patch)
        self.assertIn("legacydevice/window/main", launch)
        self.assertIn("/v1/sessions/start", launch)
        self.assertIn("/v1/sessions/bind", launch)
        self.assertIn("LibraryController.createDocument", launch)
        self.assertIn("NavigationManager.activeContext.explorer.currentFolderId", launch)
        self.assertNotIn('LibraryController.createDocument(""', launch)
        self.assertIn("DocumentController.setTemplateForPage", launch)
        self.assertIn("DocumentController.addPageWithTemplateAndPageSize", launch)
        self.assertIn("document.idForPage(0)", launch)
        self.assertIn("document.idForPage(1)", launch)
        self.assertIn("interval: 250", launch)
        self.assertIn("readinessAttempts >= 20", launch)
        self.assertIn("AFFECT [[1224665461898798997]]", submit)
        self.assertIn("/v1/sessions/submit", submit)
        self.assertIn("/v1/sessions/ink-start", submit)
        self.assertIn("Letters Home", submit)
        self.assertIn("currentPage", submit)
        self.assertIn("DocumentController.copyPages", submit)
        self.assertIn("DocumentController.addPageWithTemplateAndPageSize", submit)
        self.assertIn('phase === "response-streaming"', submit)
        self.assertIn("incoming.glyphs", submit)
        self.assertIn("response.glyphs", submit)
        self.assertIn("modelData.x", submit)
        self.assertIn("modelData.y", submit)
        self.assertNotIn('split("").join("\\n")', submit)
        self.assertNotIn("charactersPerColumn", submit)
        self.assertNotIn("implicitWidth", submit)
        self.assertNotIn("response.document_id", launch + submit)
        self.assertNotIn("upload", (launch + submit).lower())
        self.assertNotIn("createNotebookFromExistingPages", submit)
        self.assertIn('console.warn("[LettersHome] submit failed"', submit)
        self.assertIn("/v1/sessions/", submit)
        self.assertIn("interval: 750", submit)
        self.assertIn("onSessionKeyChanged", submit)
        self.assertIn("item/agentMessage/delta", (ROOT / "docs" / "issues" / "010-native-codex-roundtrip.md").read_text())
        self.assertNotIn("MouseArea", submit)
        self.assertNotIn("TapHandler", submit)
        self.assertEqual(submit.count("target: root.penHandler"), 1)
        self.assertIn("function onStrokeCompleted()", submit)
        self.assertIn("root.currentPageId === lettersHomeLayer.replyPageId", submit)
        self.assertIn("A reply has arrived", submit)
        self.assertIn("Your ink is safe", submit)
        self.assertNotIn("Try Send to Codex again", submit)
        self.assertNotIn("toolbarProvider.editingTools", submit)
        self.assertNotIn("GesturesWindow", submit)
        self.assertIn("toolbar.innerWidth + 42", submit)
        self.assertIn("toolbar.innerHeight + 54", submit)
        self.assertIn("participantNavigated", submit)
        self.assertIn("guardPageId", submit)

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
