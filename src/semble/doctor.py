"""Installation diagnostics for Semble Offline."""

from __future__ import annotations

import platform
import sys
from importlib.util import find_spec

from model2vec.utils import get_package_extras

from semble._offline import AssetCheck, validate_bundled_assets
from semble.version import __version__


def _platform_checks() -> list[AssetCheck]:
    """Return checks for the intentionally narrow supported platform."""
    machine = platform.machine().lower()
    linux_x86_64 = sys.platform == "linux" and machine in {"x86_64", "amd64"}
    libc_name, libc_version = platform.libc_ver()
    glibc_detail = f"{libc_name or 'unknown libc'} {libc_version or 'unknown version'}"
    try:
        glibc_supported = libc_name == "glibc" and tuple(map(int, libc_version.split(".")[:2])) >= (2, 34)
    except ValueError:
        glibc_supported = False
    return [
        AssetCheck("Semble version", True, __version__),
        AssetCheck("Python", (3, 10) <= sys.version_info[:2] < (3, 15), platform.python_version()),
        AssetCheck("Linux x86_64", linux_x86_64, f"{sys.platform} {machine}"),
        AssetCheck("glibc 2.34+", glibc_supported, glibc_detail),
    ]


def _runtime_checks(full: bool) -> list[AssetCheck]:
    """Exercise representative parsers and, in full mode, the embedding model."""
    from semble.chunking.core import _cached_get_parser

    languages = ["python"]
    if full:
        languages.extend(["csharp", "embeddedtemplate", "nushell", "vb", "cuda", "json5"])
    checks = []
    for language in languages:
        try:
            available = _cached_get_parser(language) is not None
        except Exception as error:
            checks.append(AssetCheck(f"parser: {language}", False, str(error)))
        else:
            checks.append(
                AssetCheck(f"parser: {language}", available, "loaded locally" if available else "unavailable")
            )

    if full:
        try:
            from semble.index.dense import load_model

            model, model_path = load_model()
            dimensions = len(model.encode(["def offline_search(): pass"])[0])
        except Exception as error:
            checks.append(AssetCheck("embedding model", False, str(error)))
        else:
            checks.append(AssetCheck("embedding model", True, f"{dimensions} dimensions from {model_path}"))
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
