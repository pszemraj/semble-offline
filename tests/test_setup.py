import json
import platform
import runpy
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


@pytest.fixture
def setup_namespace(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Load setup.py without invoking setuptools or requiring a macOS bundle."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    with patch("setuptools.setup"):
        return runpy.run_path(str(Path(__file__).parents[1] / "setup.py"))


def _write_manifest(bundle: Path, manifest: dict[str, Any]) -> None:
    """Write manifest to a temporary bundle."""
    (bundle / "asset-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _make_bundle(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    """Create the smallest valid release bundle accepted by setup.py."""
    bundle = tmp_path / "bundle"
    grammar_dir = bundle / "grammars"
    grammar_dir.mkdir(parents=True)
    grammar_files = {f"libtree_sitter_language_{index:03d}.so": "unused" for index in range(264)}
    for filename in grammar_files:
        (grammar_dir / filename).touch()
    (bundle / "grammar-sources.json").write_text("{}\n", encoding="utf-8")
    manifest = {
        "format_version": 2,
        "platform": {
            "architecture": "x86_64",
            "library_suffix": ".so",
            "minimum_version": {"kind": "glibc", "value": "2.34"},
            "operating_system": "linux",
            "wheel_tag": "manylinux_2_34_x86_64",
        },
        "grammars": {"expected_count": 264, "files": grammar_files},
    }
    _write_manifest(bundle, manifest)
    return bundle, manifest


def test_load_manifest_accepts_valid_release_bundle(setup_namespace: dict[str, Any], tmp_path: Path) -> None:
    """A complete format-2 release bundle is accepted."""
    bundle, manifest = _make_bundle(tmp_path)
    assert setup_namespace["_load_manifest"](bundle) == manifest


def test_load_manifest_rejects_unsupported_format(setup_namespace: dict[str, Any], tmp_path: Path) -> None:
    """A bundle using an unsupported manifest format is rejected."""
    bundle, manifest = _make_bundle(tmp_path)
    manifest["format_version"] = 1
    _write_manifest(bundle, manifest)
    with pytest.raises(RuntimeError, match="Unsupported Semble Offline bundle manifest"):
        setup_namespace["_load_manifest"](bundle)


def test_load_manifest_requires_exact_grammar_count(setup_namespace: dict[str, Any], tmp_path: Path) -> None:
    """A release bundle must declare exactly 264 grammars."""
    bundle, manifest = _make_bundle(tmp_path)
    manifest["grammars"]["expected_count"] = 263
    _write_manifest(bundle, manifest)
    with pytest.raises(RuntimeError, match="exactly 264 grammars"):
        setup_namespace["_load_manifest"](bundle)


def test_load_manifest_rejects_suffix_mismatch(setup_namespace: dict[str, Any], tmp_path: Path) -> None:
    """The declared library suffix must match the staged grammar files."""
    bundle, manifest = _make_bundle(tmp_path)
    manifest["platform"]["library_suffix"] = ".dylib"
    _write_manifest(bundle, manifest)
    with pytest.raises(RuntimeError, match="Unsupported Semble Offline bundle platform"):
        setup_namespace["_load_manifest"](bundle)


def test_load_manifest_rejects_wrong_wheel_tag(setup_namespace: dict[str, Any], tmp_path: Path) -> None:
    """A bundle cannot select an arbitrary wheel tag for supported native assets."""
    bundle, manifest = _make_bundle(tmp_path)
    manifest["platform"]["wheel_tag"] = "manylinux_2_39_x86_64"
    _write_manifest(bundle, manifest)
    with pytest.raises(RuntimeError, match="Unsupported Semble Offline bundle platform"):
        setup_namespace["_load_manifest"](bundle)


def test_load_manifest_requires_platform_minimum(setup_namespace: dict[str, Any], tmp_path: Path) -> None:
    """A supported bundle must declare its canonical operating-system floor."""
    bundle, manifest = _make_bundle(tmp_path)
    del manifest["platform"]["minimum_version"]
    _write_manifest(bundle, manifest)
    with pytest.raises(RuntimeError, match="Unsupported Semble Offline bundle platform"):
        setup_namespace["_load_manifest"](bundle)


def test_load_manifest_reports_malformed_sections(setup_namespace: dict[str, Any], tmp_path: Path) -> None:
    """Malformed manifest sections retain the contextual setup error."""
    bundle, manifest = _make_bundle(tmp_path)
    manifest["platform"] = []
    _write_manifest(bundle, manifest)
    with pytest.raises(RuntimeError, match="Invalid Semble Offline bundle manifest"):
        setup_namespace["_load_manifest"](bundle)


def test_load_manifest_excludes_ebnf(setup_namespace: dict[str, Any], tmp_path: Path) -> None:
    """The release bundle cannot include the excluded EBNF grammar."""
    bundle, manifest = _make_bundle(tmp_path)
    grammar_files = manifest["grammars"]["files"]
    replaced = next(iter(grammar_files))
    (bundle / "grammars" / replaced).unlink()
    del grammar_files[replaced]
    grammar_files["libtree_sitter_ebnf.so"] = "unused"
    (bundle / "grammars" / "libtree_sitter_ebnf.so").touch()
    _write_manifest(bundle, manifest)
    with pytest.raises(RuntimeError, match="grammar filenames are invalid"):
        setup_namespace["_load_manifest"](bundle)


def test_select_bundle_rejects_host_platform_mismatch(
    setup_namespace: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A bundle for another platform cannot be selected for the build host."""
    bundle, manifest = _make_bundle(tmp_path)
    grammar_files = manifest["grammars"]["files"]
    dylib_files = {name.removesuffix(".so") + ".dylib": digest for name, digest in grammar_files.items()}
    for path in (bundle / "grammars").glob("*.so"):
        path.rename(path.with_suffix(".dylib"))
    manifest["grammars"]["files"] = dylib_files
    manifest["platform"] = {
        "architecture": "arm64",
        "library_suffix": ".dylib",
        "minimum_version": {"kind": "macos", "value": "11.0"},
        "operating_system": "macos",
        "wheel_tag": "macosx_11_0_arm64",
    }
    _write_manifest(bundle, manifest)
    select_bundle = setup_namespace["_select_bundle"]
    monkeypatch.setitem(select_bundle.__globals__, "_SOURCE_BUNDLE", bundle)
    with pytest.raises(RuntimeError, match="does not match build host"):
        select_bundle()
