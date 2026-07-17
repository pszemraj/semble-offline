"""Setuptools hooks for the platform-specific offline wheels."""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any

from setuptools import setup
from setuptools.command.bdist_wheel import bdist_wheel
from setuptools.command.build_py import build_py
from setuptools.dist import Distribution

_ROOT = Path(__file__).resolve().parent
_SOURCE_BUNDLE = _ROOT / "src" / "semble" / "_bundled"
_STAGED_BUNDLE_ENV = "SEMBLE_OFFLINE_BUNDLE_DIR"


def _load_manifest(bundle: Path) -> dict[str, Any]:
    """Load and minimally validate a bundle manifest used for wheel assembly."""
    manifest_path = bundle / "asset-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        platform_data = manifest["platform"]
        grammar_data = manifest["grammars"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise RuntimeError(f"Invalid Semble Offline bundle manifest: {manifest_path}") from error

    suffix = platform_data.get("library_suffix")
    files = grammar_data.get("files")
    if manifest.get("format_version") != 2 or suffix not in {".so", ".dylib"} or not isinstance(files, dict):
        raise RuntimeError(f"Unsupported Semble Offline bundle manifest: {manifest_path}")
    if grammar_data.get("expected_count") != 264 or len(files) != 264:
        raise RuntimeError(f"A release wheel bundle must contain exactly 264 grammars: {manifest_path}")
    grammar_dir = bundle / "grammars"
    if set(files) != {path.name for path in grammar_dir.glob(f"*{suffix}")}:
        raise RuntimeError(f"Staged grammar files do not match the bundle manifest: {manifest_path}")
    if any(not name.endswith(suffix) for name in files) or f"libtree_sitter_ebnf{suffix}" in files:
        raise RuntimeError(f"Staged grammar filenames are invalid: {manifest_path}")
    if not (bundle / "grammar-sources.json").is_file():
        raise RuntimeError(f"Staged bundle has no grammar-sources.json: {bundle}")
    return manifest


def _select_bundle() -> tuple[Path, dict[str, Any]]:
    """Select the checked-in Linux bundle or an explicitly staged macOS bundle."""
    machine = platform.machine().lower()
    if sys.platform == "linux" and machine in {"x86_64", "amd64"}:
        bundle = _SOURCE_BUNDLE
        expected = ("linux", "x86_64")
    elif sys.platform == "darwin" and machine in {"arm64", "aarch64"}:
        staged = os.environ.get(_STAGED_BUNDLE_ENV)
        if not staged:
            raise RuntimeError(
                "Building Semble Offline on macOS requires a prepared arm64 grammar bundle. "
                "Install the published macOS wheel, or run scripts/build_grammar_bundle.py and set "
                f"{_STAGED_BUNDLE_ENV} to its output directory."
            )
        bundle = Path(staged).expanduser().resolve()
        expected = ("macos", "arm64")
    else:
        raise RuntimeError("Semble Offline can only be built for Linux x86_64 or macOS arm64")

    manifest = _load_manifest(bundle)
    actual = (manifest["platform"].get("operating_system"), manifest["platform"].get("architecture"))
    if actual != expected:
        raise RuntimeError(f"Bundle platform {actual!r} does not match build host {expected!r}: {bundle}")
    return bundle, manifest


_BUNDLE, _MANIFEST = _select_bundle()
_WHEEL_PLATFORM = str(_MANIFEST["platform"]["wheel_tag"])
_LIBRARY_SUFFIX = str(_MANIFEST["platform"]["library_suffix"])


class OfflineWheel(bdist_wheel):
    """Mark bundled grammar libraries as platform-specific package data."""

    def finalize_options(self) -> None:
        """Place the package in platform-specific wheel paths."""
        super().finalize_options()
        self.root_is_pure = False

    def get_tag(self) -> tuple[str, str, str]:
        """Return the supported interpreter, ABI, and manifest platform tag."""
        return "py3", "none", _WHEEL_PLATFORM


class BinaryDistribution(Distribution):
    """Treat packaged grammar shared libraries as platform-specific code."""

    def has_ext_modules(self) -> bool:
        """Return true so package modules are installed into platlib."""
        return True


class OfflineBuildPy(build_py):
    """Stage exactly one platform bundle and remove stale native libraries."""

    def run(self) -> None:
        """Build Python modules, replace staged assets, and enforce exclusions."""
        super().run()
        target = Path(self.build_lib) / "semble" / "_bundled"
        target_grammars = target / "grammars"
        target_grammars.mkdir(parents=True, exist_ok=True)
        for pattern in ("libtree_sitter_*.so", "libtree_sitter_*.dylib"):
            for library in target_grammars.glob(pattern):
                library.unlink()
        for library in sorted((_BUNDLE / "grammars").glob(f"libtree_sitter_*{_LIBRARY_SUFFIX}")):
            shutil.copy2(library, target_grammars / library.name)
        for metadata in ("asset-manifest.json", "grammar-sources.json"):
            shutil.copy2(_BUNDLE / metadata, target / metadata)

        expected = set(_MANIFEST["grammars"]["files"])
        actual = {path.name for path in target_grammars.glob(f"libtree_sitter_*{_LIBRARY_SUFFIX}")}
        if actual != expected:
            raise RuntimeError("Built grammar contents do not match the selected bundle manifest")


setup(distclass=BinaryDistribution, cmdclass={"bdist_wheel": OfflineWheel, "build_py": OfflineBuildPy})
