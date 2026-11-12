from copy import deepcopy
from unittest.mock import patch

import pytest

from semble._offline import (
    OfflineAssetError,
    bundled_grammar_dir,
    bundled_grammar_languages,
    bundled_model_dir,
    get_bundled_parser,
    grammar_library_path,
    grammar_library_suffix,
    load_asset_manifest,
    load_grammar_sources,
    validate_bundled_assets,
)
from semble.utils import resolve_model_name


def test_asset_manifest_matches_bundle() -> None:
    """The checked-in manifest describes the complete redistributable bundle."""
    manifest = load_asset_manifest()
    grammar_files = manifest["grammars"]["files"]
    suffix = grammar_library_suffix()
    sources = load_grammar_sources()
    assert set(grammar_files) == {entry["library"] for entry in sources.values()}
    assert set(grammar_files) == {path.name for path in bundled_grammar_dir().glob(f"*{suffix}")}
    assert bundled_grammar_languages() == sorted(sources)
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
        "grammars": {"files": {}},
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


@pytest.mark.parametrize("language", ["cuda", "zsh"])
def test_extras_resolve_and_load(language: str) -> None:
    """Dedicated extra grammars load without the language-pack runtime."""
    expected = bundled_grammar_dir() / load_grammar_sources()[language]["library"]
    assert grammar_library_path(language) == expected
    parser = get_bundled_parser(language)
    assert parser is not None
    assert parser.parse(b"").root_node is not None


def test_dependency_language_is_not_an_extra() -> None:
    """Standard languages are delegated to semble-grammars."""
    assert grammar_library_path("python") is None
    assert get_bundled_parser("python") is None


def test_default_model_is_bundled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default model resolution stays local and an override must be a local directory."""
    monkeypatch.delenv("SEMBLE_MODEL_NAME", raising=False)
    assert resolve_model_name() == str(bundled_model_dir())

    monkeypatch.setenv("SEMBLE_MODEL_NAME", "/definitely/not/a/local/model")
    with pytest.raises(RuntimeError, match="local model directory"):
        resolve_model_name()
