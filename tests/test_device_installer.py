import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from device_installer import (
    FixtureInstaller,
    INSTALLER_VERSION,
    InstallError,
    build_release,
    create_fake_device,
)
from device_installer.fake_device import (
    ACTIVE_QMDS_RECORD,
    BACKUP_MARKER,
    DEPENDENCIES_RECORD,
    DEVICE_RECORD,
)
from device_installer.installer import STATE_DIRECTORY, TRANSACTION_RECORD
from device_installer.release import ACTIVE_INSTALL_QMD, MANIFEST_NAME
from tablet_app.simulator import run_scenario, verify_snapshots
from toolbar_launcher import TARGETS


ROOT = Path(__file__).resolve().parents[1]


def make_fake_rcc(path):
    path.write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        "out=\n"
        "while [ \"$#\" -gt 0 ]; do\n"
        "  if [ \"$1\" = -o ]; then shift; out=$1; fi\n"
        "  shift\n"
        "done\n"
        "printf fixture-rcc-v1 > \"$out\"\n"
    )
    path.chmod(0o755)


def load_json(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def update_json(path, **changes):
    value = load_json(path)
    value.update(changes)
    write_json(path, value)


def tree_snapshot(root):
    snapshot = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        mode = stat.S_IMODE(path.stat().st_mode)
        if path.is_dir():
            snapshot[relative] = ("directory", mode)
        else:
            snapshot[relative] = (
                "file",
                mode,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
    return snapshot


class InstallerFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name)
        fake_rcc = self.workspace / "rcc"
        make_fake_rcc(fake_rcc)
        self.release = self.workspace / "release"
        build_release(self.release, str(fake_rcc))
        self.manifest = load_json(self.release / MANIFEST_NAME)

    def tearDown(self):
        self.temporary.cleanup()

    def create_device(self, name, suffix=""):
        path = self.workspace / f"{name}-{suffix or 'device'}"
        return create_fake_device(path, name)

    def assert_refused(self, expected, installer):
        with self.assertRaises(InstallError) as context:
            installer.preflight()
        self.assertEqual(context.exception.code, expected)

    def test_release_manifest_pins_targets_versions_modes_and_payload_hashes(self):
        self.assertEqual(self.manifest["installer_version"], INSTALLER_VERSION)
        self.assertTrue(self.manifest["fixture_only"])
        self.assertEqual(set(self.manifest["targets"]), {"chiappa", "ferrari"})
        self.assertIsNot(
            self.manifest["targets"]["chiappa"],
            self.manifest["targets"]["ferrari"],
        )
        for name, target in TARGETS.items():
            record = self.manifest["targets"][name]
            self.assertEqual(record["model"], target.model)
            self.assertEqual(record["os_version"], "3.28.0.162")
            self.assertEqual(record["resource_sha256"], target.resource_sha256)
            self.assertEqual(
                record["backed_up_resource_sha256"],
                target.backed_up_resource_sha256,
            )
            self.assertEqual(record["xochitl_sha256"], target.xochitl_sha256)
            self.assertEqual(record["hashtab_sha256"], target.hashtab_sha256)
            self.assertEqual(record["appload_version"], "0.5.3")
            self.assertEqual(record["xovi_version"], "0.3.3")
            self.assertEqual(record["active_qmd_order"], list(target.active_qmd_order))

        files = {entry["path"]: entry for entry in self.manifest["payload_files"]}
        required = {
            "appload/letters-home/backend/entry",
            "appload/letters-home/icon.png",
            "appload/letters-home/manifest.json",
            "appload/letters-home/resources.rcc",
            "toolbar/10-letters-home-inert.qmd",
            "toolbar/20-letters-home-launch.qmd",
            "toolbar/letter-icon.qrc",
            "toolbar/letter.svg",
        }
        self.assertTrue(required.issubset(files))
        for relative, entry in files.items():
            path = self.release / "payload" / relative
            self.assertEqual(entry["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(entry["size_bytes"], path.stat().st_size)
            self.assertEqual(entry["mode"], f"{stat.S_IMODE(path.stat().st_mode):04o}")
        self.assertEqual(files["appload/letters-home/backend/entry"]["mode"], "0755")
        self.assertTrue(
            all(
                entry["mode"] == "0644"
                for relative, entry in files.items()
                if relative != "appload/letters-home/backend/entry"
            )
        )

    def test_install_is_idempotent_and_uninstall_restores_each_target_exactly(self):
        for target_name in TARGETS:
            with self.subTest(target=target_name):
                device = self.create_device(target_name, "round-trip")
                original = tree_snapshot(device)
                resource = device / TARGETS[target_name].resource_path.lstrip("/")
                resource_bytes = resource.read_bytes()
                installer = FixtureInstaller(self.release, device)

                self.assertFalse(installer.preflight().already_installed)
                self.assertEqual(installer.install().action, "installed")
                installed = tree_snapshot(device)
                self.assertEqual(resource.read_bytes(), resource_bytes)
                active = load_json(device / ACTIVE_QMDS_RECORD)["qmds"]
                self.assertEqual(active[:-1], list(TARGETS[target_name].active_qmd_order))
                self.assertEqual(active[-1], ACTIVE_INSTALL_QMD)
                self.assertTrue(installer.preflight().already_installed)
                self.assertEqual(installer.install().action, "already_installed")
                self.assertEqual(tree_snapshot(device), installed)

                self.assertEqual(installer.uninstall().action, "uninstalled")
                self.assertEqual(tree_snapshot(device), original)
                self.assertEqual(installer.uninstall().action, "already_uninstalled")
                self.assertEqual(tree_snapshot(device), original)

    def test_interrupted_install_recovery_restores_byte_identical_fixture(self):
        steps = ("app_installed", "toolbar_installed", "qmd_activated")
        for target_name in TARGETS:
            for step in steps:
                with self.subTest(target=target_name, step=step):
                    device = self.create_device(target_name, f"interrupt-{step}")
                    original = tree_snapshot(device)
                    installer = FixtureInstaller(self.release, device)

                    def interrupt(completed):
                        if completed == step:
                            raise RuntimeError("synthetic interruption")

                    with self.assertRaisesRegex(RuntimeError, "synthetic interruption"):
                        installer.install(step_hook=interrupt)
                    self.assert_refused("active_partial_install", installer)
                    self.assertEqual(installer.recover().action, "recovered")
                    self.assertEqual(tree_snapshot(device), original)

    def test_interrupted_uninstall_recovery_completes_clean_removal(self):
        for target_name in TARGETS:
            with self.subTest(target=target_name):
                device = self.create_device(target_name, "uninstall-interrupt")
                original = tree_snapshot(device)
                installer = FixtureInstaller(self.release, device)
                installer.install()

                def interrupt(completed):
                    if completed == "app_removed":
                        raise RuntimeError("synthetic interruption")

                with self.assertRaisesRegex(RuntimeError, "synthetic interruption"):
                    installer.uninstall(step_hook=interrupt)
                self.assert_refused("active_partial_install", installer)
                self.assertEqual(installer.recover().action, "recovered")
                self.assertEqual(tree_snapshot(device), original)

    def test_interrupted_install_recovery_does_not_require_release_payload(self):
        release = self.workspace / "disposable-release"
        shutil.copytree(self.release, release)
        device = self.create_device("chiappa", "release-lost")
        original = tree_snapshot(device)
        installer = FixtureInstaller(release, device)

        def interrupt(completed):
            if completed == "app_installed":
                raise RuntimeError("synthetic interruption")

        with self.assertRaisesRegex(RuntimeError, "synthetic interruption"):
            installer.install(step_hook=interrupt)
        shutil.rmtree(release)
        self.assertEqual(installer.recover().action, "recovered")
        self.assertEqual(tree_snapshot(device), original)

    def test_recovery_rejects_tampered_transaction_and_qmd_backup(self):
        for tamper, expected in (
            ("transaction", "invalid_transaction_state"),
            ("backup", "rollback_state_mismatch"),
        ):
            with self.subTest(tamper=tamper):
                device = self.create_device("chiappa", f"tampered-{tamper}")
                installer = FixtureInstaller(self.release, device)

                def interrupt(completed):
                    if completed == "app_installed":
                        raise RuntimeError("synthetic interruption")

                with self.assertRaisesRegex(RuntimeError, "synthetic interruption"):
                    installer.install(step_hook=interrupt)
                if tamper == "transaction":
                    transaction = load_json(installer.transaction)
                    transaction["target"] = "ferrari"
                    write_json(installer.transaction, transaction)
                else:
                    backup = installer.state / "active-qmds.json"
                    backup.write_bytes(backup.read_bytes() + b"\n")

                with self.assertRaises(InstallError) as context:
                    installer.recover()
                self.assertEqual(context.exception.code, expected)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support is required")
    def test_preflight_rejects_symlink_escape_from_fixture_root(self):
        device = self.create_device("chiappa", "symlink-escape")
        outside = self.workspace / "outside-fixture"
        outside.mkdir()
        extensions = device / "opt" / "xovi" / "extensions"
        extensions.rmdir()
        extensions.symlink_to(outside, target_is_directory=True)

        with self.assertRaises(InstallError) as context:
            FixtureInstaller(self.release, device).preflight()

        self.assertEqual(context.exception.code, "unsafe_device_symlink")
        self.assertEqual(list(outside.iterdir()), [])

    def test_preflight_rejects_orphaned_installer_state(self):
        device = self.create_device("chiappa", "orphaned-state")
        (device / STATE_DIRECTORY).mkdir()

        self.assert_refused(
            "orphaned_installer_state",
            FixtureInstaller(self.release, device),
        )

    def test_preflight_refusal_matrix_covers_both_exact_targets(self):
        def low_space(root, _target):
            update_json(root / DEVICE_RECORD, free_space_bytes=0)

        def missing_backup(root, _target):
            (root / BACKUP_MARKER).unlink()

        def wrong_model(root, target):
            other = "ferrari" if target == "chiappa" else "chiappa"
            update_json(root / DEVICE_RECORD, model=TARGETS[other].model)

        def wrong_os(root, _target):
            update_json(root / DEVICE_RECORD, os_version="3.28.0.163")

        def wrong_appload(root, _target):
            update_json(root / DEVICE_RECORD, appload_version="0.5.2")

        def wrong_xovi(root, _target):
            update_json(root / DEVICE_RECORD, xovi_version="0.3.2")

        def wrong_hash(root, target):
            resource = root / TARGETS[target].resource_path.lstrip("/")
            resource.write_bytes(resource.read_bytes() + b"\n")

        def unknown_qmd(root, _target):
            path = root / ACTIVE_QMDS_RECORD
            value = load_json(path)
            value["qmds"].append("unknown-toolbar.qmd")
            write_json(path, value)

        def wrong_qmd_order(root, _target):
            path = root / ACTIVE_QMDS_RECORD
            value = load_json(path)
            value["qmds"][1:] = reversed(value["qmds"][1:])
            write_json(path, value)

        def missing_dependency(root, _target):
            path = root / DEPENDENCIES_RECORD
            value = load_json(path)
            del value["appload"]
            write_json(path, value)

        def partial_install(root, _target):
            state = root / STATE_DIRECTORY
            state.mkdir()
            write_json(state / TRANSACTION_RECORD, {"operation": "install"})

        cases = (
            ("low_space", low_space),
            ("missing_backup_marker", missing_backup),
            ("wrong_model", wrong_model),
            ("wrong_os", wrong_os),
            ("wrong_appload_version", wrong_appload),
            ("wrong_xovi_version", wrong_xovi),
            ("wrong_source_hash", wrong_hash),
            ("unknown_active_mod", unknown_qmd),
            ("active_mod_order_mismatch", wrong_qmd_order),
            ("missing_dependency", missing_dependency),
            ("active_partial_install", partial_install),
        )
        for target_name in TARGETS:
            for code, mutation in cases:
                with self.subTest(target=target_name, refusal=code):
                    device = self.create_device(target_name, f"refusal-{code}")
                    mutation(device, target_name)
                    self.assert_refused(code, FixtureInstaller(self.release, device))

    def test_payload_checksum_and_mode_changes_fail_closed(self):
        for kind in ("checksum", "mode"):
            with self.subTest(kind=kind):
                release = self.workspace / f"release-{kind}"
                shutil.copytree(self.release, release)
                payload = release / "payload" / "toolbar" / "10-letters-home-inert.qmd"
                expected = "payload_checksum_mismatch"
                if kind == "checksum":
                    contents = payload.read_bytes()
                    payload.write_bytes(bytes([contents[0] ^ 1]) + contents[1:])
                else:
                    payload.chmod(0o600)
                    expected = "payload_mode_mismatch"
                device = self.create_device("chiappa", f"payload-{kind}")
                self.assert_refused(expected, FixtureInstaller(release, device))

    def test_installer_refuses_roots_without_the_synthetic_device_marker(self):
        root = self.workspace / "not-a-fixture"
        root.mkdir()
        self.assert_refused("not_fixture_device", FixtureInstaller(self.release, root))

    def test_controlled_trial_script_emits_a_per_target_plan_and_stops_for_approval(self):
        script = ROOT / "scripts" / "run-controlled-device-trial.sh"
        self.assertTrue(script.is_file())
        self.assertTrue(script.stat().st_mode & stat.S_IXUSR)
        script_source = script.read_text()
        for forbidden_command in ("ssh ", "scp ", "systemctl ", "reboot "):
            self.assertNotIn(forbidden_command, script_source)

        for target_name, target in TARGETS.items():
            with self.subTest(target=target_name):
                completed = subprocess.run(
                    [str(script), "--device", target_name],
                    cwd=ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(completed.returncode, 4)
                plan = json.loads(completed.stdout)
                self.assertEqual(plan["action"], "stop_for_owner_approval")
                self.assertEqual(plan["target"]["codename"], target_name)
                self.assertEqual(plan["target"]["model"], target.model)
                self.assertEqual(plan["fixture_expectations"]["os_version"], "3.28.0.162")
                self.assertEqual(
                    plan["fixture_expectations"]["resource_sha256"],
                    target.resource_sha256,
                )
                self.assertEqual(
                    plan["backed_up_observations"]["resource_sha256"],
                    target.backed_up_resource_sha256,
                )
                self.assertEqual(
                    plan["backed_up_observations"]["xochitl_sha256"],
                    target.xochitl_sha256,
                )
                self.assertEqual(
                    plan["backed_up_observations"]["hashtab_sha256"],
                    target.hashtab_sha256,
                )
                self.assertEqual(
                    plan["proposed_destinations"]["appload_application"],
                    "/home/root/xovi/exthome/appload/letters-home",
                )
                self.assertIsNone(plan["observed_device_state"])
                self.assertFalse(plan["authorization"]["network_access"])
                self.assertFalse(plan["authorization"]["mutation"])
                self.assertEqual(plan["requested_read_only_window_minutes"], 5)

    def test_controlled_trial_script_has_no_execute_mode_before_discovery(self):
        script = ROOT / "scripts" / "run-controlled-device-trial.sh"
        completed = subprocess.run(
            [str(script), "--device", "chiappa", "--execute"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")

    def test_installed_fixture_matrix_exercises_flow_retry_and_orientations(self):
        snapshot_root = ROOT / "tablet_app" / "snapshots"
        self.assertEqual(verify_snapshots(snapshot_root), ())
        for target_name in TARGETS:
            device = self.create_device(target_name, "flow")
            FixtureInstaller(self.release, device).install()
            complete, states = run_scenario("complete")
            self.assertEqual(states[-1], "marginalia")
            self.assertIsNotNone(complete.session.first_ink_at)
            self.assertIsNotNone(complete.session.submitted_at)
            self.assertTrue(complete.session.annotations)
            retried, retry_states = run_scenario("timeout-retry")
            self.assertIn("review_error", retry_states)
            self.assertEqual(retry_states[-1], "marginalia")
            self.assertEqual(retried.session.review_id, "fixture-review-0001")
            for orientation in ("portrait", "landscape"):
                for state in ("incoming", "reply", "marginalia"):
                    self.assertTrue(
                        (snapshot_root / f"{target_name}-{orientation}-{state}.svg").is_file()
                    )


if __name__ == "__main__":
    unittest.main()
