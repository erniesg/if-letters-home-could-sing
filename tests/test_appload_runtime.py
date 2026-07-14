import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from device_installer.appload_runtime import (
    ADAPTED_QMD_SHA256,
    APPLOAD_COMMIT,
    APPLOAD_VERSION,
    ADAPTED_RESOURCES_QRC_SHA256,
    PAPER_PRO_FIRMWARE,
    TOOLCHAIN_IMAGE,
    UPSTREAM_RESOURCES_QRC_SHA256,
    UPSTREAM_QMD_SHA256,
    AdaptationError,
    adapt_qmd,
    adapt_resources_qrc,
    prepare_source_tree,
)


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_FIXTURE = ROOT / "tests" / "fixtures" / "appload-v0.5.3-upstream.qmd"
UPSTREAM_RESOURCES_FIXTURE = (
    ROOT / "tests" / "fixtures" / "appload-v0.5.3-upstream-resources.qrc"
)


class AppLoadRuntimeAdaptationTests(unittest.TestCase):
    def test_pin_names_the_exact_upstream_and_firmware(self):
        self.assertEqual(APPLOAD_VERSION, "0.5.3")
        self.assertEqual(APPLOAD_COMMIT, "5bb34a362f09f753f18bd6261558f8e2737aacdb")
        self.assertEqual(PAPER_PRO_FIRMWARE, "3.28.0.162")
        self.assertIn("@sha256:", TOOLCHAIN_IMAGE)
        self.assertEqual(
            hashlib.sha256(UPSTREAM_FIXTURE.read_bytes()).hexdigest(),
            UPSTREAM_QMD_SHA256,
        )

    def test_adaptation_is_exact_and_removes_only_obsolete_sidebar_patch(self):
        adapted = adapt_qmd(UPSTREAM_FIXTURE.read_text(encoding="utf-8"))

        self.assertEqual(
            hashlib.sha256(adapted.encode("utf-8")).hexdigest(),
            ADAPTED_QMD_SHA256,
        )
        self.assertNotIn("AFFECT [[4911547370760691430]]", adapted)
        self.assertNotIn("LOCATE BEFORE [[7081372714662.10578197394989910333]]", adapted)
        self.assertIn(
            "LOCATE AFTER [[8397993708429497603]]#[[7713531976371484]]",
            adapted,
        )
        self.assertIn("AFFECT [[17477757197668945522]]", adapted)
        self.assertIn("REMOVE [[8545339034058226003]]", adapted)

    def test_tampered_upstream_is_rejected_before_adaptation(self):
        with self.assertRaisesRegex(AdaptationError, "upstream_qmd_hash_mismatch"):
            adapt_qmd(UPSTREAM_FIXTURE.read_text(encoding="utf-8") + "\n")

    def test_resource_adaptation_embeds_the_launcher_envelope_alias(self):
        upstream = UPSTREAM_RESOURCES_FIXTURE.read_text(encoding="utf-8")
        self.assertEqual(hashlib.sha256(upstream.encode()).hexdigest(), UPSTREAM_RESOURCES_QRC_SHA256)
        adapted = adapt_resources_qrc(upstream)
        self.assertEqual(hashlib.sha256(adapted.encode()).hexdigest(), ADAPTED_RESOURCES_QRC_SHA256)
        self.assertIn('<qresource prefix="/letters-home/icons">', adapted)
        self.assertIn('<file alias="letter">icons/letters-home.svg</file>', adapted)

    def test_file_adapter_refuses_to_replace_an_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "adapted.qmd"
            output.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(FileExistsError, "refusing to replace"):
                adapt_qmd(UPSTREAM_FIXTURE, output)
            self.assertEqual(output.read_text(encoding="utf-8"), "keep")

    def test_prepare_source_tree_adapts_runtime_and_embeds_checked_icon(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "upstream"
            (source / "xovi" / "template").mkdir(parents=True)
            (source / "resources").mkdir()
            shutil.copy2(UPSTREAM_FIXTURE, source / "xovi" / "template" / "appload.qmd")
            shutil.copy2(UPSTREAM_RESOURCES_FIXTURE, source / "resources" / "resources.qrc")
            output = root / "adapted"

            prepare_source_tree(
                source,
                ROOT / "toolbar_launcher" / "qmldiff" / "letter.svg",
                output,
            )

            self.assertEqual(
                hashlib.sha256((output / "xovi" / "template" / "appload.qmd").read_bytes()).hexdigest(),
                ADAPTED_QMD_SHA256,
            )
            self.assertEqual(
                hashlib.sha256((output / "resources" / "resources.qrc").read_bytes()).hexdigest(),
                ADAPTED_RESOURCES_QRC_SHA256,
            )
            self.assertTrue((output / "resources" / "icons" / "letters-home.svg").is_file())


if __name__ == "__main__":
    unittest.main()
