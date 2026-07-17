"""Installation diagnostics for Semble Offline."""

from __future__ import annotations

import platform
import sys
from importlib.util import find_spec
from typing import Any

from model2vec.utils import get_package_extras

from semble._offline import AssetCheck, bundled_grammar_languages, load_asset_manifest, validate_bundled_assets
from semble.version import __version__


def _version_at_least(actual: str, minimum: str) -> bool:
    """Return whether a dotted numeric version satisfies a minimum."""
    try:
        actual_parts = tuple(int(part) for part in actual.split("."))
        minimum_parts = tuple(int(part) for part in minimum.split("."))
    except ValueError:
        return False
    width = max(len(actual_parts), len(minimum_parts))
    return actual_parts + (0,) * (width - len(actual_parts)) >= minimum_parts + (0,) * (width - len(minimum_parts))


def _platform_checks(manifest: dict[str, Any] | None = None) -> list[AssetCheck]:
    """Return checks for the platform declared by the installed wheel."""
    manifest = load_asset_manifest() if manifest is None else manifest
    platform_data = manifest["platform"]
    expected_os = str(platform_data["operating_system"])
    expected_arch = str(platform_data["architecture"])
    minimum = platform_data["minimum_version"]
    machine = platform.machine().lower()
    normalized_machine = "arm64" if machine in {"arm64", "aarch64"} else "x86_64" if machine == "amd64" else machine
    actual_os = "macos" if sys.platform == "darwin" else "linux" if sys.platform == "linux" else sys.platform

    checks = [
        AssetCheck("Semble version", True, __version__),
        AssetCheck("Python", (3, 10) <= sys.version_info[:2] < (3, 15), platform.python_version()),
        AssetCheck(
            "wheel platform",
            (actual_os, normalized_machine) == (expected_os, expected_arch),
            f"installed for {expected_os} {expected_arch}; running on {actual_os} {normalized_machine}",
        ),
    ]

    kind = minimum.get("kind")
    required = str(minimum.get("value", ""))
    if kind == "glibc":
        libc_name, libc_version = platform.libc_ver()
        ok = actual_os == "linux" and libc_name == "glibc" and _version_at_least(libc_version, required)
        detail = f"{libc_name or 'unknown libc'} {libc_version or 'unknown version'}"
        checks.append(AssetCheck(f"glibc {required}+", ok, detail))
    elif kind == "macos":
        macos_version = platform.mac_ver()[0]
        ok = actual_os == "macos" and _version_at_least(macos_version, required)
        checks.append(AssetCheck(f"macOS {required}+", ok, macos_version or "unknown version"))
    else:
        checks.append(AssetCheck("platform minimum", False, f"unsupported requirement: {kind!r}"))
    return checks


def _parser_checks(full: bool) -> list[AssetCheck]:
    """Exercise one or every bundled parser."""
    from semble.chunking.core import _cached_get_parser

    if full:
        failures: list[str] = []
        languages = bundled_grammar_languages()
        for language in languages:
            try:
                parser = _cached_get_parser(language)  # type: ignore[arg-type]
                if parser is None:
                    failures.append(f"{language} (unavailable)")
                else:
                    parser.parse(b"")
            except Exception as error:
                failures.append(f"{language} ({error})")
        parser_checks = [
            AssetCheck(
                "all grammar parsers",
                not failures,
                f"{len(languages)} loaded locally" if not failures else f"failed: {', '.join(failures[:8])}",
            )
        ]
    else:
        try:
            parser = _cached_get_parser("python")
            if parser is not None:
                parser.parse(b"")
        except Exception as error:
            parser_checks = [AssetCheck("parser: python", False, str(error))]
        else:
            detail = "loaded locally" if parser is not None else "unavailable"
            parser_checks = [AssetCheck("parser: python", parser is not None, detail)]

    return parser_checks


def _model_check() -> AssetCheck:
    """Load and exercise the bundled embedding model."""
    try:
        from semble.index.dense import load_model

        model, model_path = load_model()
        dimensions = len(model.encode(["def offline_search(): pass"])[0])
    except Exception as error:
        return AssetCheck("embedding model", False, str(error))
    return AssetCheck("embedding model", True, f"{dimensions} dimensions from {model_path}")


def _runtime_checks(full: bool) -> list[AssetCheck]:
    """Exercise bundled parsers and, in full mode, the embedding model."""
    checks = _parser_checks(full)

    if full:
        checks.append(_model_check())
    return checks


def run_doctor(full: bool = False) -> bool:
    """Print installation diagnostics and return whether required checks passed."""
    checks = [*_platform_checks(), *validate_bundled_assets(full=full), *_runtime_checks(full)]
    width = max(len(check.name) for check in checks)
    print(f"Semble Offline diagnostics{' (full)' if full else ''}\n")
    for check in checks:
        marker = "ok" if check.ok else "FAIL"
        print(f"[{marker:<4}] {check.name:<{width}}  {check.detail}")

    mcp_missing = [name for name in get_package_extras("semble", "mcp") if find_spec(name) is None]
    if mcp_missing:
        print(f"[info] {'MCP extra':<{width}}  not installed (optional for CLI use)")
    else:
        print(f"[ok  ] {'MCP extra':<{width}}  installed")

    success = all(check.ok for check in checks)
    print("\nAll required checks passed." if success else "\nOne or more required checks failed.")
    return success
