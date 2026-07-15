"""Fixture-only dual-device release builder and recoverable installer."""

from .fake_device import create_fake_device
from .installer import FixtureInstaller, InstallError, InstallResult, PreflightResult
from .release import INSTALLER_VERSION, ReleaseError, build_release

__all__ = [
    "FixtureInstaller",
    "INSTALLER_VERSION",
    "InstallError",
    "InstallResult",
    "PreflightResult",
    "ReleaseError",
    "build_release",
    "create_fake_device",
]
