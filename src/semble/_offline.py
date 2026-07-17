"""Resolve and validate the assets bundled with Semble Offline."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

_BUNDLED_DIR = Path(__file__).resolve().parent / "_bundled"
_MANIFEST_PATH = _BUNDLED_DIR / "asset-manifest.json"
_GRAMMAR_SOURCES_PATH = _BUNDLED_DIR / "grammar-sources.json"


class OfflineAssetError(RuntimeError):
    """Raised when required offline assets are missing, corrupt, or unusable."""


@dataclass(frozen=True)
class AssetCheck:
    """Result of one bundled-asset validation check."""

    name: str
    ok: bool
    detail: str


def _load_json_object(path: Path, description: str) -> dict[str, Any]:
    """Load a JSON object or raise a contextual offline-asset error."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise OfflineAssetError(f"Cannot read bundled {description}: {path}") from error
    if not isinstance(value, dict):
        raise OfflineAssetError(f"Bundled {description} is not a JSON object: {path}")
    return value


@cache
def load_asset_manifest() -> dict[str, Any]:
    """Load the bundled platform provenance and integrity manifest."""
    manifest = _load_json_object(_MANIFEST_PATH, "asset manifest")
    if manifest.get("format_version") != 2:
        raise OfflineAssetError(f"Unsupported bundled asset manifest: {_MANIFEST_PATH}")
    return manifest


@cache
def load_grammar_sources() -> dict[str, Any]:
    """Load the language-to-source provenance mapping bundled with the wheel."""
    return _load_json_object(_GRAMMAR_SOURCES_PATH, "grammar source manifest")


def _manifest_files(section: str) -> dict[str, str]:
    """Return the expected file hashes for one manifest section."""
    try:
        files = load_asset_manifest()[section]["files"]
    except (KeyError, TypeError) as error:
        raise OfflineAssetError(f"Asset manifest has no valid {section}.files section") from error
    valid_files = isinstance(files, dict) and all(
        isinstance(name, str) and isinstance(value, str) for name, value in files.items()
    )
    if not valid_files:
        raise OfflineAssetError(f"Asset manifest has no valid {section}.files section")
    return files


def grammar_library_suffix() -> str:
    """Return the native-library suffix declared by the bundled platform manifest."""
    try:
        suffix = load_asset_manifest()["platform"]["library_suffix"]
    except (KeyError, TypeError) as error:
        raise OfflineAssetError("Asset manifest has no valid platform.library_suffix") from error
    if suffix not in {".so", ".dylib"}:
        raise OfflineAssetError(f"Unsupported bundled grammar library suffix: {suffix!r}")
    return str(suffix)


def bundled_model_dir() -> Path:
    """Return the required bundled embedding model directory."""
    model_dir = _BUNDLED_DIR / "model"
    missing = [name for name in _manifest_files("model") if not (model_dir / name).is_file()]
    if missing:
        raise OfflineAssetError(
            f"Bundled embedding model is incomplete ({', '.join(missing)}). "
            "Reinstall Semble Offline from a trusted wheel."
        )
    return model_dir


def bundled_grammar_dir() -> Path:
    """Return the required bundled tree-sitter grammar directory."""
    grammar_dir = _BUNDLED_DIR / "grammars"
    missing = [name for name in _manifest_files("grammars") if not (grammar_dir / name).is_file()]
    if missing:
        preview = ", ".join(missing[:3])
        suffix = "..." if len(missing) > 3 else ""
        raise OfflineAssetError(
            f"Bundled tree-sitter grammars are incomplete ({preview}{suffix}). "
            "Reinstall Semble Offline from a trusted wheel."
        )
    return grammar_dir


def bundled_grammar_languages() -> list[str]:
    """Return every bundled language identifier in stable order."""
    sources = load_grammar_sources()
    if len(sources) != load_asset_manifest()["grammars"].get("expected_count"):
        raise OfflineAssetError("Grammar source manifest count does not match the asset manifest")
    if not all(isinstance(language, str) and isinstance(source, dict) for language, source in sources.items()):
        raise OfflineAssetError("Grammar source manifest contains invalid entries")
    return sorted(sources)


def grammar_symbol(language: str) -> str:
    """Return the shared-library symbol name for a Semble language identifier."""
    aliases = load_asset_manifest()["grammars"].get("aliases", {})
    return str(aliases.get(language, language))


def grammar_library_path(language: str) -> Path | None:
    """Return the bundled grammar library for language, without downloading anything."""
    directory = bundled_grammar_dir()
    symbol = grammar_symbol(language)
    library = directory / f"libtree_sitter_{symbol}{grammar_library_suffix()}"
    return library if library.is_file() else None


@cache
def activate_bundled_grammars() -> Path:
    """Configure tree-sitter-language-pack to use the bundled grammar directory."""
    target = bundled_grammar_dir()
    try:
        import tree_sitter_language_pack as tslp

        tslp.configure(cache_dir=str(target))
    except Exception as error:
        raise OfflineAssetError(f"Cannot configure the offline tree-sitter grammar directory: {target}") from error
    return target


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest for path."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_bundled_assets(full: bool = False) -> list[AssetCheck]:
    """Validate bundled model and grammar assets, optionally hashing every file."""
    checks: list[AssetCheck] = []
    try:
        manifest = load_asset_manifest()
        suffix = grammar_library_suffix()
        checks.append(AssetCheck("asset manifest", True, "format 2"))
    except OfflineAssetError as error:
        return [AssetCheck("asset manifest", False, str(error))]

    for section, directory in (("model", _BUNDLED_DIR / "model"), ("grammars", _BUNDLED_DIR / "grammars")):
        expected = _manifest_files(section)
        actual = {path.name for path in directory.iterdir() if path.is_file()} if directory.is_dir() else set()
        relevant_actual = {
            name for name in actual if name in expected or section == "grammars" and name.endswith((".so", ".dylib"))
        }
        missing = sorted(set(expected) - actual)
        unexpected = sorted(relevant_actual - set(expected))
        ok = not missing and not unexpected
        detail = f"{len(expected)} files"
        if missing:
            detail = f"missing {', '.join(missing[:3])}"
        elif unexpected:
            detail = f"unexpected {', '.join(unexpected[:3])}"
        checks.append(AssetCheck(f"bundled {section}", ok, detail))

        if full and ok:
            mismatches = [
                name for name, expected_hash in expected.items() if _sha256(directory / name) != expected_hash
            ]
            checks.append(
                AssetCheck(
                    f"{section} SHA-256",
                    not mismatches,
                    "all hashes match" if not mismatches else f"mismatch: {', '.join(mismatches[:3])}",
                )
            )

    excluded = manifest["grammars"].get("excluded", {})
    ebnf_absent = not (_BUNDLED_DIR / "grammars" / f"libtree_sitter_ebnf{suffix}").exists()
    checks.append(
        AssetCheck(
            "EBNF exclusion",
            ebnf_absent and "ebnf" in excluded,
            "GPL-3.0 grammar is not bundled; line chunking is used",
        )
    )
    return checks
