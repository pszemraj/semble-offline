import sys
from unittest.mock import patch

import pytest

from semble._offline import AssetCheck, OfflineAssetError
from semble.doctor import _parser_checks, _platform_checks, _version_at_least


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


def test_platform_checks_report_unreadable_manifest() -> None:
    """An unreadable asset manifest becomes a failed diagnostic check."""
    with patch("semble.doctor.load_asset_manifest", side_effect=OfflineAssetError("cannot read asset manifest")):
        checks = _platform_checks()
    platform_check = next(check for check in checks if check.name == "wheel platform")
    assert not platform_check.ok
    assert platform_check.detail == "cannot read asset manifest"


@pytest.mark.parametrize(
    "manifest",
    [
        {"format_version": 2},
        {"format_version": 2, "platform": []},
        {
            "format_version": 2,
            "platform": {"operating_system": "linux", "architecture": "x86_64", "minimum_version": []},
        },
    ],
)
def test_platform_checks_report_malformed_manifest(manifest: dict) -> None:
    """Malformed platform metadata becomes a failed diagnostic check."""
    checks = _platform_checks(manifest)
    platform_check = next(check for check in checks if check.name == "wheel platform")
    assert not platform_check.ok
    assert platform_check.detail == "Asset manifest has no valid platform requirements"


def test_full_parser_checks_report_unreadable_source_manifest() -> None:
    """An unreadable grammar source manifest becomes a failed diagnostic check."""
    with patch("semble.doctor.bundled_grammar_languages", side_effect=OfflineAssetError("cannot read grammar sources")):
        checks = _parser_checks(full=True)
    assert checks == [AssetCheck("all grammar parsers", False, "cannot read grammar sources")]


def test_full_parser_checks_report_omitted_failure_count() -> None:
    """A broad parser failure reports how many details were omitted."""
    languages = [f"language_{index}" for index in range(10)]
    with (
        patch("semble.doctor.bundled_grammar_languages", return_value=languages),
        patch("semble.chunking.core._cached_get_parser", return_value=None),
    ):
        checks = _parser_checks(full=True)
    assert checks[0].detail.endswith(" (+2 more)")
