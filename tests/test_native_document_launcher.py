import hashlib
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock
from xml.etree import ElementTree

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
    def test_ferrari_template_package_sources_match_the_native_zip_import_contract(self):
        source = ROOT / "toolbar_launcher" / "templates" / "letters-home-ferrari"
        manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
        svg = ElementTree.parse(source / "image.svg").getroot()
        png = (source / "image.png").read_bytes()

        self.assertEqual(
            manifest,
            {
                "categories": ["Creative", "Lines", "Grids"],
                "iconCode": "\ue99a",
                "name": "letters-home-ferrari",
            },
        )
        self.assertEqual(svg.attrib["width"], "954")
        self.assertEqual(svg.attrib["height"], "1696")
        self.assertEqual(svg.attrib["viewBox"], "0 0 954 1696")
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", png[16:24]), (954, 1696))

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
            contract["symbols"]["LibraryController.createDocumentFromExisting"],
            "[[4393738620531550914]]",
        )
        self.assertEqual(
            contract["symbols"]["library-ui/window/create-notebook"],
            "[[5959403860571066977]]",
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
                self.assertEqual(
                    entry["destination"],
                    "/home/root/xovi/exthome/qt-resource-rebuilder/" + entry["name"],
                )
                self.assertEqual(
                    entry["rollback_action"],
                    "restore_pretrial_or_remove_if_absent",
                )
            self.assertEqual(len(manifest["templates"]), 1)
            template = manifest["templates"][0]
            self.assertEqual(template["name"], "letters-home-ferrari.rmt")
            self.assertEqual(template["mode"], "0644")
            self.assertTrue(template["app_owned"])
            self.assertEqual(template["rollback_action"], "remove_if_hash_matches")
            self.assertEqual(
                template["destination"],
                "/home/root/.local/share/remarkable/templates/custom/letters-home-ferrari.rmt",
            )
            bundled_template = output / "templates" / template["name"]
            self.assertTrue(bundled_template.is_file())
            self.assertEqual(template["sha256"], hashlib.sha256(bundled_template.read_bytes()).hexdigest())
            with zipfile.ZipFile(bundled_template) as archive:
                self.assertEqual(
                    sorted(archive.namelist()),
                    ["image.png", "image.svg", "manifest.json"],
                )
                self.assertEqual(
                    json.loads(archive.read("manifest.json")),
                    {
                        "categories": ["Creative", "Lines", "Grids"],
                        "iconCode": "\ue99a",
                        "name": "letters-home-ferrari",
                    },
                )
                png_sha256 = hashlib.sha256(archive.read("image.png")).hexdigest()
                svg_sha256 = hashlib.sha256(archive.read("image.svg")).hexdigest()
            self.assertEqual(
                template["generated_outputs"],
                [
                    {
                        "destination": "/home/root/.local/share/remarkable/templates/import/letters-home-ferrari.png",
                        "rollback_action": "remove_if_hash_matches",
                        "sha256": png_sha256,
                    },
                    {
                        "destination": "/home/root/.local/share/remarkable/templates/import/letters-home-ferrari.svg",
                        "rollback_action": "remove_if_hash_matches",
                        "sha256": svg_sha256,
                    },
                ],
            )
            self.assertEqual(
                manifest["document_view"]["resource_id"],
                "[[1224665461898798997]]",
            )
            native_api = manifest["native_api_contract"]
            contract_path = output / "contracts" / native_api["name"]
            self.assertTrue(contract_path.is_file())
            self.assertEqual(
                native_api["sha256"],
                hashlib.sha256(contract_path.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                native_api["resources"]["pages_actions"],
                "[[11797611520953530268]]",
            )
            self.assertEqual(
                native_api["symbols"]["DocumentController.copyPages"],
                "[[12188519148798835813]]",
            )
            self.assertEqual(
                native_api["recovered_source_sha256"]["create_notebook"],
                "808163f296c9f272710bd07082b868039b948983c051a28a54bea13380c0316d",
            )
            self.assertEqual(
                manifest["workflow"],
                {
                    "document_model": "one_native_notebook",
                    "initial_pages": ["incoming_letter", "huipi"],
                    "completed_pages": [
                        "incoming_letter",
                        "huipi",
                        "reversible_marginalia",
                        "response_letter",
                    ],
                    "pdf_import": False,
                    "reviewed_document_upload": False,
                    "participant_ink_replaced": False,
                },
            )
            self.assertEqual(
                manifest["bridge"]["launch_agent_label"],
                "com.erniesg.letters-home.bridge",
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
        self.assertIn("http://10.11.99.16:8765/v1/notebook-seed", installed)
        self.assertIn("library-ui/window/create-notebook", installed)
        self.assertNotIn("LibraryController.", installed)
        self.assertNotIn("DocumentController.", installed)
        self.assertIn("document.idForPage(0)", installed)
        self.assertIn("document.idForPage(1)", installed)
        self.assertIn('root.windowNavigator.open("legacydevice/window/main"', installed)
        self.assertIn("documentId: lettersHomeLauncher.documentId", installed)
        self.assertIn('lettersHomeLauncher.text = "Preparing letter…"', installed)
        self.assertNotIn("Mac unavailable", installed)
        self.assertIn('lettersHomeLauncher.text = "Letters Home"', installed)
        self.assertNotIn("upload", installed.lower())
        self.assertNotIn("AppLoadLauncher", installed)
        self.assertNotIn("import net.asivery.AppLoad", installed)

    def test_warm_launcher_clones_a_native_seed_in_the_stock_controller_scope(self):
        launch = (PACKAGE / "qmldiff" / "20-letters-home-launch.qmd").read_text()
        sidebar_region, factory_region = launch.split(
            "AFFECT [[8651031636888757197]]",
            1,
        )

        self.assertIn("library-ui/window/create-notebook", sidebar_region)
        self.assertIn("/v1/notebook-seed", launch)
        self.assertIn("lettersHomeSeed", launch)
        self.assertIn("interval: 2000", sidebar_region)
        self.assertNotIn("LibraryController.", sidebar_region)
        self.assertNotIn("DocumentController.", sidebar_region)
        self.assertNotIn("Library.entryForId", sidebar_region)
        self.assertIn("DocumentController.copyPages", factory_region)
        self.assertIn(
            "LibraryController.createDocumentFromExisting",
            factory_region,
        )
        self.assertIn("try {", factory_region)
        self.assertIn("onFailed", factory_region)

    def test_streamed_batches_reveal_one_immutable_glyph_per_tick(self):
        submit = (PACKAGE / "qmldiff" / "30-letters-home-submit.qmd").read_text()

        self.assertIn("property int visibleIncomingGlyphCount: 0", submit)
        self.assertIn("property int visibleResponseGlyphCount: 0", submit)
        self.assertIn("interval: 90", submit)
        self.assertIn("visibleIncomingGlyphCount += 1", submit)
        self.assertIn("visibleResponseGlyphCount += 1", submit)
        self.assertIn(
            "incomingGlyphs.slice(0, lettersHomeLayer.visibleIncomingGlyphCount)",
            submit,
        )
        self.assertIn(
            "responseGlyphs.slice(0, lettersHomeLayer.visibleResponseGlyphCount)",
            submit,
        )

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
        self.assertIn("/v1/notebook-seed", launch)
        self.assertIn("LibraryController.createDocument", launch)
        self.assertIn("NavigationManager.activeContext", launch)
        self.assertIn("activeContext.explorer.currentFolderId", launch)
        self.assertNotIn('LibraryController.createDocument(""', launch)
        self.assertIn("DocumentController.setTemplateForPage", launch)
        self.assertIn("DocumentController.addPageWithTemplateAndPageSize", launch)
        self.assertIn("LibraryController.createDocumentFromExisting", launch)
        self.assertIn("DocumentController.copyPages", launch)
        self.assertIn("ready.idForPage(0)", launch)
        self.assertIn("ready.idForPage(1)", launch)
        self.assertIn("interval: 50", launch)
        self.assertIn("interval: 2000", launch)
        self.assertIn("lettersHomeCloneAttempts >= 20", launch)
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

    def test_active_native_notebook_flow_never_imports_or_replaces_a_pdf(self):
        source = "\n".join(
            (PACKAGE / "qmldiff" / name).read_text(encoding="utf-8")
            for name in (
                "20-letters-home-launch.qmd",
                "30-letters-home-submit.qmd",
            )
        )

        self.assertIn("LibraryController.createDocument", source)
        self.assertIn("DocumentController.copyPages", source)
        self.assertIn("DocumentController.addPageWithTemplateAndPageSize", source)
        self.assertNotIn("createNotebookFromExistingPages", source)
        self.assertNotIn("reviewed_document_id", source)
        self.assertNotIn("application/pdf", source)
        self.assertNotIn("/upload", source.lower())


if __name__ == "__main__":
    unittest.main()
