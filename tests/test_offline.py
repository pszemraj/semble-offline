from copy import deepcopy
from unittest.mock import patch

import pytest

from semble._offline import (
    OfflineAssetError,
    bundled_grammar_dir,
    bundled_grammar_languages,
    bundled_model_dir,
    grammar_library_path,
    grammar_library_suffix,
    grammar_symbol,
    load_asset_manifest,
    validate_bundled_assets,
)
from semble.utils import resolve_model_name


def test_asset_manifest_matches_bundle() -> None:
    """The checked-in manifest describes the complete redistributable bundle."""
    manifest = load_asset_manifest()
    grammar_files = manifest["grammars"]["files"]
    suffix = grammar_library_suffix()
    assert len(grammar_files) == 264
    assert f"libtree_sitter_ebnf{suffix}" not in grammar_files
    assert set(grammar_files) == {path.name for path in bundled_grammar_dir().glob(f"*{suffix}")}
    assert len(bundled_grammar_languages()) == 264
    assert all(check.ok for check in validate_bundled_assets())


def test_asset_validation_reports_malformed_manifest_section() -> None:
    """A malformed format-2 manifest becomes a failed check rather than an exception."""
    manifest = deepcopy(load_asset_manifest())
    del manifest["model"]
    with patch("semble._offline.load_asset_manifest", return_value=manifest):
        checks = validate_bundled_assets()
    assert len(checks) == 1
    assert checks[0].name == "asset manifest"
    assert not checks[0].ok
    assert checks[0].detail == "Asset manifest has no valid model.files section"


def test_asset_validation_reports_invalid_exclusion_metadata() -> None:
    """Invalid exclusion metadata fails its check without aborting diagnostics."""
    manifest = deepcopy(load_asset_manifest())
    manifest["grammars"]["excluded"] = None
    with patch("semble._offline.load_asset_manifest", return_value=manifest):
        checks = validate_bundled_assets()
    exclusion = next(check for check in checks if check.name == "EBNF exclusion")
    assert not exclusion.ok


def test_asset_validation_reports_undeclared_model_file(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A stale or injected model file fails exact-set validation."""
    model_dir = tmp_path / "model"
    grammar_dir = tmp_path / "grammars"
    model_dir.mkdir()
    grammar_dir.mkdir()
    (model_dir / "config.json").touch()
    (model_dir / "stale.safetensors").touch()
    manifest = {
        "format_version": 2,
        "model": {"files": {"config.json": "unused"}},
        "grammars": {"files": {}, "excluded": {"ebnf": "excluded"}},
        "platform": {"library_suffix": ".so"},
    }
    monkeypatch.setattr("semble._offline._BUNDLED_DIR", tmp_path)
    with patch("semble._offline.load_asset_manifest", return_value=manifest):
        checks = validate_bundled_assets()
    model_check = next(check for check in checks if check.name == "bundled model")
    assert not model_check.ok
    assert model_check.detail == "unexpected stale.safetensors"


def test_bundled_languages_report_malformed_asset_manifest() -> None:
    """Language enumeration preserves the offline-asset error boundary."""
    with patch("semble._offline.load_asset_manifest", return_value={"format_version": 2}):
        with pytest.raises(OfflineAssetError, match="no valid grammars section"):
            bundled_grammar_languages()


@pytest.mark.parametrize(
    ("language", "symbol"),
    [
        ("csharp", "c_sharp"),
        ("embeddedtemplate", "embedded_template"),
        ("nushell", "nu"),
        ("vb", "vb_dotnet"),
        ("python", "python"),
    ],
)
def test_grammar_aliases_resolve_to_bundled_libraries(language: str, symbol: str) -> None:
    """Semble identifiers with different C symbols resolve without a download."""
    assert grammar_symbol(language) == symbol
    expected = bundled_grammar_dir() / f"libtree_sitter_{symbol}{grammar_library_suffix()}"
    assert grammar_library_path(language) == expected


def test_ebnf_is_intentionally_not_bundled() -> None:
    """The GPL-3.0 EBNF grammar is absent so .ebnf inputs use line chunking."""
    assert grammar_library_path("ebnf") is None


def test_default_model_is_bundled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default model resolution stays local and an override must be a local directory."""
    monkeypatch.delenv("SEMBLE_MODEL_NAME", raising=False)
    assert resolve_model_name() == str(bundled_model_dir())

    monkeypatch.setenv("SEMBLE_MODEL_NAME", "/definitely/not/a/local/model")
    with pytest.raises(RuntimeError, match="local model directory"):
        resolve_model_name()


@pytest.mark.parametrize("language", ["mojo", "nim", "norg", "wolfram"])
def test_cpp_scanner_grammar_loads(language: str) -> None:
    """C++ scanner grammars load their runtime and can parse without linker errors."""
    from semble.chunking.core import _cached_get_parser

    parser = _cached_get_parser(language)  # type: ignore[arg-type]
    assert parser is not None
    assert parser.parse(b"").root_node is not None
