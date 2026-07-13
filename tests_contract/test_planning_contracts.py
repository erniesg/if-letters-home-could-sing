import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ISSUE_DIR = ROOT / "docs" / "issues"
REQUIRED_HEADINGS = {
    "Goal",
    "Acceptance tests",
    "Validation command",
    "Allowed secrets",
    "Artifact outputs",
    "Stop conditions",
    "Human clarification protocol",
    "Recommended response",
    "Trade-offs",
    "Free-form response",
}


class RenderProfileTests(unittest.TestCase):
    def test_generation_sizes_are_model_valid_and_transform_to_native(self):
        data = json.loads((ROOT / "contracts" / "render-profiles.json").read_text())
        for profile_id, profile in data["profiles"].items():
            generation = profile["generation"]
            native = profile["native_landscape"]
            transform = profile["transform"]
            width, height = generation["width"], generation["height"]
            self.assertEqual(width % 16, 0, profile_id)
            self.assertEqual(height % 16, 0, profile_id)
            self.assertLessEqual(max(width, height) / min(width, height), 3, profile_id)
            self.assertGreaterEqual(width * height, 655_360, profile_id)
            self.assertLessEqual(width * height, 8_294_400, profile_id)
            vertical_delta = transform["top"] + transform["bottom"]
            horizontal_delta = transform["left"] + transform["right"]
            if transform["kind"] == "pad":
                self.assertEqual(width + horizontal_delta, native["width"], profile_id)
                self.assertEqual(height + vertical_delta, native["height"], profile_id)
            elif transform["kind"] == "crop":
                self.assertEqual(width - horizontal_delta, native["width"], profile_id)
                self.assertEqual(height - vertical_delta, native["height"], profile_id)
            else:
                self.fail(f"unknown transform kind in {profile_id}")


class ExamplePayloadTests(unittest.TestCase):
    def test_capture_window_is_first_ink_through_submit(self):
        session = json.loads((ROOT / "contracts" / "session.example.json").read_text())
        start = session["first_ink_at"]
        end = session["submitted_at"]
        self.assertLess(start, end)
        for sample in session["heart_rate"]["samples"]:
            self.assertGreaterEqual(sample["captured_at"], start)
            self.assertLessEqual(sample["captured_at"], end)
            self.assertGreater(sample["bpm"], 0)

    def test_review_preserves_uncertainty_and_normalised_anchors(self):
        review = json.loads((ROOT / "contracts" / "review.example.json").read_text())
        self.assertTrue(any(a["kind"] == "uncertain-reading" for a in review["annotations"]))
        for annotation in review["annotations"]:
            self.assertGreaterEqual(annotation["confidence"], 0)
            self.assertLessEqual(annotation["confidence"], 1)
            for value in annotation["anchor"].values():
                if isinstance(value, float):
                    self.assertGreaterEqual(value, 0)
                    self.assertLessEqual(value, 1)


class IssueLedgerTests(unittest.TestCase):
    def test_issue_specs_are_portable_and_complete(self):
        specs = sorted(ISSUE_DIR.glob("[0-9][0-9][0-9]-*.md"))
        self.assertGreaterEqual(len(specs), 8)
        ids = [int(path.name[:3]) for path in specs]
        self.assertEqual(ids, list(range(1, len(ids) + 1)))
        for path in specs:
            text = path.read_text()
            headings = set(re.findall(r"^## (.+)$", text, re.MULTILINE))
            self.assertTrue(REQUIRED_HEADINGS.issubset(headings), path.name)
            self.assertNotIn("/Users/", text, path.name)
            self.assertNotRegex(text, r"(?i)(access[_-]?token|api[_-]?key)\s*[:=]\s*\S+", path.name)

    def test_dependencies_only_point_backwards(self):
        specs = sorted(ISSUE_DIR.glob("[0-9][0-9][0-9]-*.md"))
        valid_ids = {int(path.name[:3]) for path in specs}
        for path in specs:
            issue_id = int(path.name[:3])
            text = path.read_text()
            match = re.search(r"^depends-on:\s*(.+)$", text, re.MULTILINE)
            if not match:
                continue
            dependencies = {int(value) for value in re.findall(r"\d+", match.group(1))}
            self.assertTrue(dependencies.issubset(valid_ids), path.name)
            self.assertTrue(all(value < issue_id for value in dependencies), path.name)


if __name__ == "__main__":
    unittest.main()
