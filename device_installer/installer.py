"""Transactionally recoverable installer restricted to synthetic device roots."""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Mapping, Optional

from toolbar_launcher import PatchError, TabletSnapshot, apply_toolbar_patch
from toolbar_launcher.launcher import KNOWN_UNRELATED_MOD
from toolbar_launcher.targets import TARGETS

from .fake_device import (
    ACTIVE_QMDS_RECORD,
    BACKUP_MARKER,
    DEPENDENCIES_RECORD,
    DEVICE_RECORD,
)
from .release import (
    ACTIVE_INSTALL_QMD,
    INSTALL_LAYOUT,
    INSTALLER_VERSION,
    MANIFEST_NAME,
    PAYLOAD_DIRECTORY,
    ReleaseError,
    load_release_manifest,
    sha256,
    target_manifest,
)


STATE_DIRECTORY = ".letters-home-installer"
TRANSACTION_RECORD = "transaction.json"
INSTALLED_RECORD = "installed.json"
ACTIVE_QMDS_BACKUP = "active-qmds.json"
StepHook = Callable[[str], None]


class InstallError(ValueError):
    """A fail-closed installer stop condition with a stable code."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class InstallResult:
    action: str
    target: str
    version: str = INSTALLER_VERSION


@dataclass(frozen=True)
class PreflightResult:
    target: str
    already_installed: bool


class FixtureInstaller:
    """Install only into an explicit fake-device filesystem fixture."""

    def __init__(self, release: Path, device_root: Path) -> None:
        self.release = release.resolve()
        self.device_root = device_root.resolve()
        self.payload = self.release / PAYLOAD_DIRECTORY
        self.state = self.device_root / STATE_DIRECTORY
        self.transaction = self.state / TRANSACTION_RECORD
        self.installed = self.state / INSTALLED_RECORD

    def preflight(self) -> PreflightResult:
        device = self._device_record()
        if self.transaction.exists():
            raise InstallError("active_partial_install")
        manifest = self._validated_release()
        if self.installed.exists():
            self._validate_installed(manifest, device)
            return PreflightResult(str(device["target"]), True)

        target, active_qmds = self._validate_device_base(manifest, device)
        required_free = manifest.get("minimum_free_bytes")
        available = device.get("free_space_bytes")
        if not isinstance(required_free, int) or not isinstance(available, int):
            raise InstallError("invalid_space_record")
        if available < required_free:
            raise InstallError("low_space")
        for layout in INSTALL_LAYOUT:
            if self._device_path(str(layout["destination"])).exists():
                raise InstallError("destination_conflict")

        snapshot = TabletSnapshot(
            target=target.codename,
            model=str(device["model"]),
            os_version=str(device["os_version"]),
            source_path=target.resource_path,
            source=self._resource_path(target.resource_path).read_bytes(),
            active_qmds=active_qmds,
            appload_version=str(device["appload_version"]),
            xovi_version=str(device["xovi_version"]),
        )
        try:
            apply_toolbar_patch(snapshot)
        except PatchError as error:
            raise InstallError(error.code) from error
        return PreflightResult(target.codename, False)

    def install(self, *, step_hook: Optional[StepHook] = None) -> InstallResult:
        preflight = self.preflight()
        if preflight.already_installed:
            return InstallResult("already_installed", preflight.target)

        manifest = self._validated_release()
        original_active = self._device_path(ACTIVE_QMDS_RECORD)
        self.state.mkdir(mode=0o700)
        shutil.copy2(original_active, self.state / ACTIVE_QMDS_BACKUP)
        self._write_json(
            self.transaction,
            {
                "operation": "install",
                "target": preflight.target,
                "version": INSTALLER_VERSION,
            },
        )

        stage = self.state / "stage"
        stage.mkdir()
        for index, layout in enumerate(INSTALL_LAYOUT):
            source = self.payload / str(layout["payload"])
            staged = stage / str(index)
            shutil.copytree(source, staged, copy_function=shutil.copy2)
            destination = self._device_path(str(layout["destination"]))
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged, destination)
            if step_hook:
                step_hook(f"{layout['name']}_installed")

        active = list(self._read_active_qmds(original_active))
        active.append(str(manifest["active_install_qmd"]))
        self._write_json_atomic(original_active, {"qmds": active})
        if step_hook:
            step_hook("qmd_activated")

        manifest_hash = sha256((self.release / MANIFEST_NAME).read_bytes())
        self._write_json(
            self.installed,
            {
                "active_qmds_backup_sha256": sha256(
                    (self.state / ACTIVE_QMDS_BACKUP).read_bytes()
                ),
                "manifest_sha256": manifest_hash,
                "original_active_qmds": active[:-1],
                "target": preflight.target,
                "version": INSTALLER_VERSION,
            },
        )
        self.transaction.unlink()
        shutil.rmtree(stage)
        return InstallResult("installed", preflight.target)

    def uninstall(self, *, step_hook: Optional[StepHook] = None) -> InstallResult:
        device = self._device_record()
        if self.transaction.exists():
            raise InstallError("active_partial_install")
        manifest = self._validated_release()
        if not self.installed.exists():
            self._assert_unmanaged_destinations_absent(manifest)
            return InstallResult("already_uninstalled", str(device["target"]))
        self._validate_installed(manifest, device)

        self._write_json(
            self.transaction,
            {
                "operation": "uninstall",
                "target": device["target"],
                "version": INSTALLER_VERSION,
            },
        )
        trash = self.state / "trash"
        trash.mkdir()
        for index, layout in enumerate(INSTALL_LAYOUT):
            destination = self._device_path(str(layout["destination"]))
            os.replace(destination, trash / str(index))
            if step_hook:
                step_hook(f"{layout['name']}_removed")
        self._restore_active_qmds()
        if step_hook:
            step_hook("qmd_deactivated")
        shutil.rmtree(self.state)
        return InstallResult("uninstalled", str(device["target"]))

    def recover(self) -> InstallResult:
        device = self._device_record()
        if not self.transaction.exists():
            return InstallResult("no_partial_install", str(device["target"]))
        backup = self.state / ACTIVE_QMDS_BACKUP
        if not backup.is_file():
            raise InstallError("rollback_unavailable")
        target_name = str(device["target"])
        try:
            target = TARGETS[target_name]
        except KeyError as error:
            raise InstallError("wrong_target") from error
        for field, expected, code in (
            ("model", target.model, "wrong_model"),
            ("os_version", target.os_version, "wrong_os"),
            ("appload_version", target.appload_version, "wrong_appload_version"),
            ("xovi_version", target.xovi_version, "wrong_xovi_version"),
        ):
            if device.get(field) != expected:
                raise InstallError(code)
        if sha256(self._resource_path(target.resource_path).read_bytes()) != target.resource_sha256:
            raise InstallError("resource_changed_during_transaction")
        self._validate_backup(target)
        for layout in INSTALL_LAYOUT:
            destination = self._device_path(str(layout["destination"]))
            if destination.is_dir():
                shutil.rmtree(destination)
            elif destination.exists():
                destination.unlink()
        self._restore_active_qmds()
        shutil.rmtree(self.state)
        return InstallResult("recovered", target_name)

    def _validated_release(self) -> Mapping[str, object]:
        try:
            manifest = load_release_manifest(self.release)
        except ReleaseError as error:
            raise InstallError(error.code) from error
        if manifest.get("schema_version") != 1:
            raise InstallError("unsupported_release_schema")
        if manifest.get("fixture_only") is not True:
            raise InstallError("release_not_fixture_only")
        if manifest.get("installer_version") != INSTALLER_VERSION:
            raise InstallError("wrong_installer_version")
        if manifest.get("active_install_qmd") != ACTIVE_INSTALL_QMD:
            raise InstallError("wrong_install_phase")
        if manifest.get("install_layout") != list(INSTALL_LAYOUT):
            raise InstallError("release_layout_mismatch")
        expected_targets = {
            name: target_manifest(target) for name, target in sorted(TARGETS.items())
        }
        if manifest.get("targets") != expected_targets:
            raise InstallError("release_target_mismatch")
        expected_dependencies = {
            "appload": TARGETS["chiappa"].appload_version,
            "xovi": TARGETS["chiappa"].xovi_version,
        }
        if manifest.get("required_dependencies") != expected_dependencies:
            raise InstallError("release_dependency_mismatch")
        self._validate_payload_files(manifest)
        return manifest

    def _validate_payload_files(self, manifest: Mapping[str, object]) -> None:
        entries = manifest.get("payload_files")
        if not isinstance(entries, list) or not entries:
            raise InstallError("invalid_payload_manifest")
        expected_paths: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                raise InstallError("invalid_payload_manifest")
            relative = self._safe_relative(entry.get("path"))
            relative_text = relative.as_posix()
            if relative_text in expected_paths:
                raise InstallError("duplicate_payload_path")
            expected_paths.add(relative_text)
            path = self.payload / relative
            if path.is_symlink() or not path.is_file():
                raise InstallError("missing_payload_file")
            if entry.get("size_bytes") != path.stat().st_size:
                raise InstallError("payload_size_mismatch")
            if entry.get("sha256") != sha256(path.read_bytes()):
                raise InstallError("payload_checksum_mismatch")
            mode = entry.get("mode")
            if not isinstance(mode, str) or not re.fullmatch(r"0[0-7]{3}", mode):
                raise InstallError("invalid_payload_mode")
            if stat.S_IMODE(path.stat().st_mode) != int(mode, 8):
                raise InstallError("payload_mode_mismatch")
        actual_paths = {
            path.relative_to(self.payload).as_posix()
            for path in self.payload.rglob("*")
            if path.is_file()
        }
        if actual_paths != expected_paths:
            raise InstallError("payload_file_set_mismatch")

    def _validate_device_base(
        self, manifest: Mapping[str, object], device: Mapping[str, object]
    ):
        target_name = device.get("target")
        try:
            target = TARGETS[str(target_name)]
        except KeyError as error:
            raise InstallError("wrong_target") from error
        if manifest["targets"].get(target.codename) != target_manifest(target):
            raise InstallError("release_target_mismatch")
        checks = (
            ("model", target.model, "wrong_model"),
            ("os_version", target.os_version, "wrong_os"),
            ("appload_version", target.appload_version, "wrong_appload_version"),
            ("xovi_version", target.xovi_version, "wrong_xovi_version"),
        )
        for field, expected, code in checks:
            if device.get(field) != expected:
                raise InstallError(code)

        self._validate_dependencies(manifest["required_dependencies"])

        resource = self._resource_path(target.resource_path)
        if not resource.is_file() or sha256(resource.read_bytes()) != target.resource_sha256:
            raise InstallError("wrong_source_hash")
        self._validate_backup(target)
        active = self._read_active_qmds(self._device_path(ACTIVE_QMDS_RECORD))
        known = set(target.active_qmd_order) | {KNOWN_UNRELATED_MOD}
        if any(item not in known for item in active):
            raise InstallError("unknown_active_mod")
        required = tuple(item for item in active if item in target.active_qmd_order)
        if required != target.active_qmd_order:
            raise InstallError("active_mod_order_mismatch")
        return target, active

    def _validate_backup(self, target) -> None:
        marker_path = self._device_path(BACKUP_MARKER)
        if not marker_path.is_file():
            raise InstallError("missing_backup_marker")
        marker = self._read_json(marker_path, "backup_mismatch")
        expected = {
            "model": target.model,
            "os_version": target.os_version,
            "resource_path": target.resource_path,
            "resource_sha256": target.resource_sha256,
            "target": target.codename,
            "verified": True,
        }
        if any(marker.get(key) != value for key, value in expected.items()):
            raise InstallError("backup_mismatch")
        backup_relative = marker.get("backup_path")
        backup = self._device_path(str(backup_relative))
        if not backup.is_file() or sha256(backup.read_bytes()) != target.resource_sha256:
            raise InstallError("rollback_unavailable")

    def _validate_installed(
        self, manifest: Mapping[str, object], device: Mapping[str, object]
    ) -> None:
        record = self._read_json(self.installed, "installed_state_invalid")
        target, _ = self._validate_device_identity_and_resource(manifest, device)
        manifest_hash = sha256((self.release / MANIFEST_NAME).read_bytes())
        if (
            record.get("version") != INSTALLER_VERSION
            or record.get("target") != target.codename
            or record.get("manifest_sha256") != manifest_hash
        ):
            raise InstallError("installed_state_mismatch")
        backup = self.state / ACTIVE_QMDS_BACKUP
        if not backup.is_file() or record.get("active_qmds_backup_sha256") != sha256(backup.read_bytes()):
            raise InstallError("rollback_unavailable")
        original = self._read_active_qmds(backup)
        if record.get("original_active_qmds") != list(original):
            raise InstallError("installed_state_mismatch")
        active = self._read_active_qmds(self._device_path(ACTIVE_QMDS_RECORD))
        if active != original + (ACTIVE_INSTALL_QMD,):
            raise InstallError("installed_qmd_set_changed")
        self._validate_installed_payload(manifest)

    def _validate_device_identity_and_resource(
        self, manifest: Mapping[str, object], device: Mapping[str, object]
    ):
        target_name = str(device.get("target"))
        try:
            target = TARGETS[target_name]
        except KeyError as error:
            raise InstallError("wrong_target") from error
        for field, expected, code in (
            ("model", target.model, "wrong_model"),
            ("os_version", target.os_version, "wrong_os"),
            ("appload_version", target.appload_version, "wrong_appload_version"),
            ("xovi_version", target.xovi_version, "wrong_xovi_version"),
        ):
            if device.get(field) != expected:
                raise InstallError(code)
        if manifest["targets"].get(target_name) != target_manifest(target):
            raise InstallError("release_target_mismatch")
        self._validate_dependencies(manifest["required_dependencies"])
        resource = self._resource_path(target.resource_path)
        if not resource.is_file() or sha256(resource.read_bytes()) != target.resource_sha256:
            raise InstallError("wrong_source_hash")
        self._validate_backup(target)
        return target, resource

    def _validate_dependencies(self, required: Mapping[str, object]) -> None:
        dependencies = self._read_json(
            self._device_path(DEPENDENCIES_RECORD), "missing_dependency"
        )
        for name, version in required.items():
            if name not in dependencies:
                raise InstallError("missing_dependency")
            if dependencies[name] != version:
                raise InstallError("wrong_dependency_version")

    def _validate_installed_payload(self, manifest: Mapping[str, object]) -> None:
        entries = {str(entry["path"]): entry for entry in manifest["payload_files"]}
        for layout in manifest["install_layout"]:
            prefix = str(layout["payload"])
            destination = self._device_path(str(layout["destination"]))
            expected: set[str] = set()
            for relative, entry in entries.items():
                if relative == prefix or relative.startswith(prefix + "/"):
                    suffix = relative[len(prefix):].lstrip("/")
                    expected.add(suffix)
                    installed = destination / suffix
                    if not installed.is_file():
                        raise InstallError("installed_payload_changed")
                    if sha256(installed.read_bytes()) != entry["sha256"]:
                        raise InstallError("installed_payload_changed")
                    if stat.S_IMODE(installed.stat().st_mode) != int(str(entry["mode"]), 8):
                        raise InstallError("installed_payload_mode_changed")
            actual = {
                path.relative_to(destination).as_posix()
                for path in destination.rglob("*")
                if path.is_file()
            }
            if actual != expected:
                raise InstallError("installed_payload_changed")

    def _assert_unmanaged_destinations_absent(self, manifest: Mapping[str, object]) -> None:
        for layout in manifest["install_layout"]:
            if self._device_path(str(layout["destination"])).exists():
                raise InstallError("unmanaged_installation")
        active_path = self._device_path(ACTIVE_QMDS_RECORD)
        if ACTIVE_INSTALL_QMD in self._read_active_qmds(active_path):
            raise InstallError("unmanaged_installation")

    def _restore_active_qmds(self) -> None:
        backup = self.state / ACTIVE_QMDS_BACKUP
        if not backup.is_file():
            raise InstallError("rollback_unavailable")
        destination = self._device_path(ACTIVE_QMDS_RECORD)
        temporary = destination.with_name(destination.name + ".restore")
        shutil.copy2(backup, temporary)
        os.replace(temporary, destination)

    def _device_record(self) -> Mapping[str, object]:
        path = self.device_root / DEVICE_RECORD
        if not path.is_file():
            raise InstallError("not_fixture_device")
        device = self._read_json(path, "invalid_fixture_device")
        if device.get("fixture_only") is not True or device.get("schema_version") != 1:
            raise InstallError("not_fixture_device")
        return device

    def _resource_path(self, resource_path: str) -> Path:
        if not resource_path.startswith("/"):
            raise InstallError("invalid_resource_path")
        return self._device_path(resource_path.lstrip("/"))

    def _device_path(self, relative: str) -> Path:
        return self.device_root / self._safe_relative(relative)

    @staticmethod
    def _safe_relative(value: object) -> PurePosixPath:
        if not isinstance(value, str) or not value:
            raise InstallError("unsafe_relative_path")
        relative = PurePosixPath(value)
        if relative.is_absolute() or ".." in relative.parts or "." in relative.parts:
            raise InstallError("unsafe_relative_path")
        return relative

    @staticmethod
    def _read_json(path: Path, code: str) -> Mapping[str, object]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise InstallError(code) from error
        if not isinstance(value, dict):
            raise InstallError(code)
        return value

    def _read_active_qmds(self, path: Path) -> tuple[str, ...]:
        value = self._read_json(path, "invalid_active_qmd_record").get("qmds")
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise InstallError("invalid_active_qmd_record")
        return tuple(value)

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        path.chmod(0o600)

    def _write_json_atomic(self, path: Path, value: object) -> None:
        temporary = path.with_name(path.name + ".new")
        self._write_json(temporary, value)
        temporary.chmod(stat.S_IMODE(path.stat().st_mode))
        os.replace(temporary, path)
