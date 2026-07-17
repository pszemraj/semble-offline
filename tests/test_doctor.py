import sys
from unittest.mock import patch

import pytest

from semble.doctor import _platform_checks, _version_at_least


def _manifest(operating_system: str, architecture: str, kind: str, minimum: str) -> dict:
    return {
        "platform": {
            "architecture": architecture,
            "minimum_version": {"kind": kind, "value": minimum},
            "operating_system": operating_system,
        }
    }


@pytest.mark.parametrize(
    ("actual", "minimum", "expected"),
    [("11.0", "11.0", True), ("15.5.1", "11.0", True), ("10.15.7", "11.0", False), ("unknown", "11.0", False)],
)
def test_version_at_least(actual: str, minimum: str, expected: bool) -> None:
    """Dotted platform versions compare numerically and fail closed."""
    assert _version_at_least(actual, minimum) is expected


def test_linux_platform_checks_follow_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    """Linux checks use the manifest's architecture and glibc floor."""
    monkeypatch.setattr(sys, "platform", "linux")
    with patch("platform.machine", return_value="x86_64"), patch("platform.libc_ver", return_value=("glibc", "2.34")):
        checks = _platform_checks(_manifest("linux", "x86_64", "glibc", "2.34"))
    assert all(check.ok for check in checks)


def test_macos_platform_checks_follow_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    """MacOS checks use the manifest's architecture and OS floor."""
    monkeypatch.setattr(sys, "platform", "darwin")
    with patch("platform.machine", return_value="arm64"), patch("platform.mac_ver", return_value=("11.0", (), "")):
        checks = _platform_checks(_manifest("macos", "arm64", "macos", "11.0"))
    assert all(check.ok for check in checks)


def test_platform_mismatch_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Installing a wheel on a different OS and architecture fails diagnostics."""
    monkeypatch.setattr(sys, "platform", "linux")
    with patch("platform.machine", return_value="x86_64"), patch("platform.mac_ver", return_value=("", (), "")):
        checks = _platform_checks(_manifest("macos", "arm64", "macos", "11.0"))
    assert not next(check for check in checks if check.name == "wheel platform").ok
    assert not next(check for check in checks if check.name == "macOS 11.0+").ok
