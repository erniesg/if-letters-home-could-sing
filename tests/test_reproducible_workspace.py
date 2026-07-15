import ast
import json
import re
import subprocess
import unittest
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 and older macOS system Python.
    tomllib = None


ROOT = Path(__file__).resolve().parents[1]


def load_workspace_metadata(path: Path):
    text = path.read_text(encoding="utf-8")
    if tomllib is not None:
        return tomllib.loads(text)

    def section(name):
        match = re.search(
            rf"(?ms)^\[{re.escape(name)}\]\s*(.*?)(?=^\[|\Z)",
            text,
        )
        if match is None:
            raise AssertionError(f"missing [{name}] in pyproject.toml")
        return match.group(1)

    def literal(section_name, key):
        body = section(section_name)
        match = re.search(
            rf"(?ms)^{re.escape(key)}\s*=\s*(\[[^\]]*\]|\"[^\"]*\")",
            body,
        )
        if match is None:
            raise AssertionError(f"missing {key} in [{section_name}]")
        return ast.literal_eval(match.group(1))

    return {
        "build-system": {"requires": literal("build-system", "requires")},
        "project": {
            "requires-python": literal("project", "requires-python"),
            "dependencies": literal("project", "dependencies"),
            "optional-dependencies": {
                "dev": literal("project.optional-dependencies", "dev")
            },
        },
    }


def requirement_lines(path: Path):
    return [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def frontend_sources():
    for suffix in ("*.ts", "*.tsx", "*.js", "*.mjs"):
        for path in (ROOT / "frontend").rglob(suffix):
            relative_parts = path.relative_to(ROOT / "frontend").parts
            if "node_modules" not in relative_parts and ".next" not in relative_parts:
                yield path


class PythonWorkspaceTests(unittest.TestCase):
    def test_active_python_workspace_is_pinned_and_dependency_free(self):
        metadata = load_workspace_metadata(ROOT / "pyproject.toml")
        project = metadata["project"]

        self.assertEqual((ROOT / ".python-version").read_text().strip(), "3.12.8")
        self.assertEqual(project["requires-python"], ">=3.11,<3.13")
        self.assertEqual(project["dependencies"], [])
        self.assertEqual(project["optional-dependencies"]["dev"], [])
        self.assertEqual(requirement_lines(ROOT / "requirements.txt"), [])
        for requirement in metadata["build-system"]["requires"]:
            self.assertRegex(requirement, r"^[A-Za-z0-9_.-]+==[0-9][A-Za-z0-9_.+-]*$")

    def test_legacy_public_dependencies_are_separate_and_exact(self):
        requirements = requirement_lines(ROOT / "requirements-legacy.txt")
        self.assertGreater(len(requirements), 0)
        for requirement in requirements:
            self.assertRegex(
                requirement,
                r"^[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?==[0-9][A-Za-z0-9_.+-]*$",
            )


class FrontendWorkspaceTests(unittest.TestCase):
    def test_frontend_manifest_and_lock_are_exact(self):
        manifest = json.loads((ROOT / "frontend" / "package.json").read_text())
        lock = json.loads((ROOT / "frontend" / "package-lock.json").read_text())

        self.assertEqual(manifest["packageManager"], "npm@10.9.8")
        self.assertEqual((ROOT / "frontend" / ".nvmrc").read_text().strip(), "22.22.3")
        self.assertEqual(lock["lockfileVersion"], 3)
        self.assertEqual(lock["packages"][""]["version"], manifest["version"])
        for group in ("dependencies", "devDependencies"):
            self.assertGreater(len(manifest[group]), 0)
            for package, version in manifest[group].items():
                self.assertRegex(version, r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?$", package)


class LegacyBoundaryTests(unittest.TestCase):
    def test_legacy_runner_reports_missing_setup_as_a_block(self):
        result = subprocess.run(
            [str(ROOT / "scripts" / "legacy-tests")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertIn(result.returncode, (0, 2), result.stderr)
        if result.returncode == 2:
            self.assertIn("setup blocked", result.stderr)
            self.assertNotIn("/Users/", result.stderr)

    def test_legacy_archive_fixture_is_synthetic_and_portable(self):
        source = (ROOT / "legacy_tests" / "test_operators.py").read_text()
        self.assertNotIn("/Users/", source)
        self.assertIn("tmp_path", source)
        self.assertIn("zipfile.ZipFile", source)


class SensitiveLoggingTests(unittest.TestCase):
    def test_provider_credentials_and_token_substrings_are_not_logged(self):
        for path in frontend_sources():
            source = path.read_text()
            console_arguments = re.findall(
                r"console\.(?:debug|log|info|warn|error)\((.*?)\);",
                source,
                re.DOTALL,
            )
            for arguments in console_arguments:
                self.assertNotRegex(
                    arguments,
                    r"(?i)(?:access[_-]?token|whoop_access_token|openai_api_key|authorization)",
                    path.relative_to(ROOT),
                )
            self.assertNotRegex(
                source,
                r"(?i)access[_-]?token\.(?:slice|substring|substr)\(",
                path.relative_to(ROOT),
            )

    def test_participant_ink_and_biometrics_are_not_debug_logged(self):
        frontend_source = "\n".join(
            path.read_text()
            for path in frontend_sources()
        )
        drawing_source = (ROOT / "draw.js").read_text()
        forbidden_fragments = (
            "Fetched cycles:",
            "Fetched heart rate:",
            "Received data:",
            "Heart Rate Update:",
            "Heart Rate Window:",
            "RR Intervals:",
            "Received strokes:",
        )
        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, frontend_source + drawing_source)


if __name__ == "__main__":
    unittest.main()
