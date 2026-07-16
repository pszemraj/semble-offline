from pathlib import Path

import pytest

from semble._offline import (
    OfflineAssetError,
    bundled_grammar_dir,
    bundled_model_dir,
    grammar_library_path,
    grammar_symbol,
    load_asset_manifest,
    validate_bundled_assets,
)
from semble.utils import resolve_model_name


def test_asset_manifest_matches_bundle() -> None:
    """The checked-in manifest describes the complete redistributable bundle."""
    manifest = load_asset_manifest()
    grammar_files = manifest["grammars"]["files"]
    assert len(grammar_files) == 264
    assert "libtree_sitter_ebnf.so" not in grammar_files
    assert set(grammar_files) == {path.name for path in bundled_grammar_dir().glob("*.so")}
    assert all(check.ok for check in validate_bundled_assets())


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
    assert grammar_library_path(language) == bundled_grammar_dir() / f"libtree_sitter_{symbol}.so"


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


def test_invalid_grammar_override_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A bad explicit grammar override fails instead of falling through to a downloader cache."""
    monkeypatch.setenv("SEMBLE_TS_CACHE_DIR", str(tmp_path / "missing"))
    with pytest.raises(OfflineAssetError, match="not a directory"):
        grammar_library_path("python")
