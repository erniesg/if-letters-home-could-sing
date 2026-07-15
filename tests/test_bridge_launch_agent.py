import plistlib
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LABEL = "com.erniesg.letters-home.bridge"


class BridgeLaunchAgentTests(unittest.TestCase):
    def test_launch_agent_uses_explicit_python_and_sanitized_environment(self):
        from mac_bridge.launch_agent import render_launch_agent

        plist = render_launch_agent(
            repo_root=Path("/opt/letters-home"),
            python=Path("/opt/python/bin/python3"),
            home=Path("/Users/tester"),
        )

        self.assertEqual(
            plist["ProgramArguments"][:3],
            ["/usr/bin/env", "-i", "HOME=/Users/tester"],
        )
        self.assertIn("PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin", plist["ProgramArguments"])
        self.assertIn("PYTHONPATH=/opt/letters-home", plist["ProgramArguments"])
        self.assertIn("/opt/python/bin/python3", plist["ProgramArguments"])
        self.assertEqual(
            plist["ProgramArguments"][-4:],
            ["-m", "mac_bridge.server", "--repo-root", "/opt/letters-home"],
        )
        self.assertTrue(plist["KeepAlive"])
        self.assertTrue(plist["RunAtLoad"])
        self.assertNotIn("EnvironmentVariables", plist)

    def test_launch_agent_logs_are_app_owned_and_private_context_is_a_path_only(self):
        from mac_bridge.launch_agent import render_launch_agent

        plist = render_launch_agent(
            repo_root=Path("/opt/letters-home"),
            python=Path("/opt/python/bin/python3"),
            home=Path("/Users/tester"),
            conversation_context_file=Path("/Users/tester/.config/letters-home/context.txt"),
        )

        self.assertEqual(plist["Label"], LABEL)
        self.assertEqual(
            plist["StandardOutPath"],
            "/Users/tester/.local/share/letters-home/bridge.stdout.log",
        )
        self.assertEqual(
            plist["StandardErrorPath"],
            "/Users/tester/.local/share/letters-home/bridge.stderr.log",
        )
        self.assertEqual(
            plist["ProgramArguments"][-2:],
            [
                "--conversation-context-file",
                "/Users/tester/.config/letters-home/context.txt",
            ],
        )
        rendered = plistlib.dumps(plist).decode("utf-8")
        self.assertNotIn("OPENAI_API_KEY", rendered)
        self.assertNotIn("conversation_context=", rendered)

    def test_renderer_rejects_relative_or_untrusted_inputs(self):
        from mac_bridge.launch_agent import LaunchAgentError, render_launch_agent

        cases = (
            {"repo_root": Path("relative"), "python": Path("/bin/python3"), "home": Path("/Users/tester")},
            {"repo_root": Path("/opt/app"), "python": Path("python3"), "home": Path("/Users/tester")},
            {"repo_root": Path("/opt/app"), "python": Path("/bin/python3"), "home": Path("relative")},
            {
                "repo_root": Path("/opt/app"),
                "python": Path("/bin/python3"),
                "home": Path("/Users/tester"),
                "conversation_context_file": Path("relative/context.txt"),
            },
        )
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaisesRegex(LaunchAgentError, "launch_agent_path_invalid"):
                    render_launch_agent(**case)

    def test_checked_in_plist_matches_the_deterministic_fixture(self):
        from mac_bridge.launch_agent import render_launch_agent

        fixture_path = ROOT / "mac_bridge" / "launchd" / f"{LABEL}.plist"
        self.assertTrue(fixture_path.is_file())
        with fixture_path.open("rb") as handle:
            fixture = plistlib.load(handle)
        self.assertEqual(
            fixture,
            render_launch_agent(
                repo_root=Path("/opt/letters-home"),
                python=Path("/opt/python/bin/python3"),
                home=Path("/Users/letters-home"),
            ),
        )

    def test_runtime_preflight_is_injectable_and_fails_closed(self):
        from mac_bridge.launch_agent import LaunchAgentError, runtime_preflight

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "mac_bridge").mkdir()
            (root / "mac_bridge" / "server.py").write_text("", encoding="utf-8")
            python = root / "python3"
            codex = root / "codex"
            pdftoppm = root / "pdftoppm"
            for executable in (python, codex, pdftoppm):
                executable.write_text("fixture", encoding="utf-8")
                executable.chmod(0o755)

            result = runtime_preflight(
                repo_root=root,
                python=python,
                codex=codex,
                pdftoppm=pdftoppm,
                module_available=lambda name: False,
            )
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["python"], str(python))
            self.assertEqual(result["codex"], str(codex))
            self.assertEqual(result["pdftoppm"], str(pdftoppm))

            with self.assertRaisesRegex(
                LaunchAgentError,
                "missing_runtime_dependency:pdftoppm",
            ):
                runtime_preflight(
                    repo_root=root,
                    python=python,
                    codex=codex,
                    pdftoppm=root / "missing-pdftoppm",
                )

    def test_install_and_uninstall_scripts_are_checkable_and_hash_owned(self):
        install = (ROOT / "scripts" / "install-letters-home-bridge").read_text()
        uninstall = (ROOT / "scripts" / "uninstall-letters-home-bridge").read_text()

        self.assertIn("--check-only", install)
        self.assertIn("launchctl bootstrap", install)
        self.assertIn("launchctl kickstart -k", install)
        self.assertIn("http://10.11.99.16:8765/health", install)
        self.assertIn("managed.sha256", install)
        self.assertIn("rollback_install", install)
        self.assertIn("plutil -lint", install)
        self.assertIn("sys.executable", install)
        self.assertIn("--check-only", uninstall)
        self.assertIn("launchctl bootout", uninstall)
        self.assertIn("managed.sha256", uninstall)
        self.assertIn("unmanaged_launch_agent", uninstall)


if __name__ == "__main__":
    unittest.main()
