#!/usr/bin/env python3
"""Generate checked-in Linux provenance and integrity metadata for bundled assets."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "src" / "semble" / "_bundled"
GRAMMARS = BUNDLE / "grammars"
MODEL = BUNDLE / "model"
LINKER_PATCH = ROOT / "scripts" / "patches" / "tree-sitter-language-pack-cxx-linker.patch"

UPSTREAM_REPOSITORY = "https://github.com/MinishLab/semble"
UPSTREAM_COMMIT = "f4c397e2ede0c16ab1772adeee9a0af1024043bf"
MODEL_REPOSITORY = "https://huggingface.co/minishlab/potion-code-16M-v2"
MODEL_REVISION = "e9d2a44ca6a05ac6685f3b23709ea57eb7352d5b"
GRAMMAR_PACKAGE = "tree-sitter-language-pack"
GRAMMAR_VERSION = "1.6.2"
LANGUAGE_PACK_COMMIT = "6bb9761028dfc3a72329d15f0f339ec7ccb56159"
GRAMMAR_ARCHIVE_URL = (
    "https://github.com/kreuzberg-dev/tree-sitter-language-pack/releases/download/v1.6.2/parsers-linux-x86_64.tar.zst"
)
GRAMMAR_ARCHIVE_SHA256 = "5b5a4d2d5319b7d2fae6c7a87e8bf8618c6c827842dba7641a93693980e6b5ea"
GRAMMAR_ARCHIVE_SIZE = 19_134_009
REBUILT_CXX_GRAMMARS = ["mojo", "nim", "norg", "wolfram"]


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _file_hashes(directory: Path, pattern: str) -> dict[str, str]:
    """Return sorted relative file names mapped to their SHA-256 digests."""
    return {path.name: _sha256(path) for path in sorted(directory.glob(pattern))}


def _load_json(path: Path) -> dict[str, Any]:
    """Read a JSON object from path."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"Expected a JSON object in {path}")
    return value


def _grammar_sources(definitions_path: Path, licenses_path: Path) -> dict[str, dict[str, str]]:
    """Select source revisions and licenses for the grammar binaries in this bundle."""
    definitions = _load_json(definitions_path)
    licenses = _load_json(licenses_path)
    included_symbols = {path.stem.removeprefix("libtree_sitter_") for path in GRAMMARS.glob("libtree_sitter_*.so")}
    sources: dict[str, dict[str, str]] = {}
    for language, raw_definition in definitions.items():
        if not isinstance(raw_definition, dict):
            continue
        symbol = str(raw_definition.get("c_symbol", language))
        if symbol not in included_symbols:
            continue
        repository = str(raw_definition["repo"])
        license_key = repository.removeprefix("https://github.com/").removesuffix(".git")
        sources[str(language)] = {
            "library": f"libtree_sitter_{symbol}.so",
            "license": str(licenses.get(license_key, "UNKNOWN")),
            "repository": repository,
            "revision": str(raw_definition["rev"]),
        }

    resolved_symbols = {value["library"][len("libtree_sitter_") : -len(".so")] for value in sources.values()}
    unresolved = included_symbols - resolved_symbols
    if unresolved:
        raise RuntimeError(f"No source metadata for grammar symbols: {sorted(unresolved)}")
    return dict(sorted(sources.items()))


def main() -> None:
    """Write deterministic asset-manifest.json and grammar-sources.json files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language-definitions", required=True, type=Path)
    parser.add_argument("--license-cache", required=True, type=Path)
    args = parser.parse_args()

    grammar_files = _file_hashes(GRAMMARS, "libtree_sitter_*.so")
    if len(grammar_files) != 264:
        raise RuntimeError(f"Expected 264 bundled grammars after excluding EBNF; found {len(grammar_files)}")
    if "libtree_sitter_ebnf.so" in grammar_files:
        raise RuntimeError("EBNF must not be bundled because its grammar is GPL-3.0")

    manifest = {
        "format_version": 2,
        "grammars": {
            "aliases": {
                "csharp": "c_sharp",
                "embeddedtemplate": "embedded_template",
                "nushell": "nu",
                "vb": "vb_dotnet",
            },
            "excluded": {"ebnf": "Excluded because the v1.6.2 grammar is GPL-3.0; .ebnf files use line chunking."},
            "expected_count": 264,
            "files": grammar_files,
            "package": GRAMMAR_PACKAGE,
            "provenance": {
                "base": {
                    "archive_sha256": GRAMMAR_ARCHIVE_SHA256,
                    "archive_size": GRAMMAR_ARCHIVE_SIZE,
                    "archive_url": GRAMMAR_ARCHIVE_URL,
                    "kind": "release-archive",
                },
                "rebuilt": {
                    "c_compiler": "x86_64-conda-linux-gnu-cc (conda-forge gcc 11.4.0-13) 11.4.0",
                    "compiler_sysroot": "sysroot_linux-64 2.17",
                    "cxx_compiler": "x86_64-conda-linux-gnu-c++ (conda-forge gcc 11.4.0-13) 11.4.0",
                    "kind": "source-build",
                    "language_pack_commit": LANGUAGE_PACK_COMMIT,
                    "libraries": [f"libtree_sitter_{name}.so" for name in REBUILT_CXX_GRAMMARS],
                    "linker_patch_sha256": _sha256(LINKER_PATCH),
                    "rust_toolchain": "1.91",
                    "tree_sitter_cli": "0.26.8",
                },
            },
            "version": GRAMMAR_VERSION,
        },
        "model": {
            "files": _file_hashes(MODEL, "*"),
            "repository": MODEL_REPOSITORY,
            "revision": MODEL_REVISION,
        },
        "platform": {
            "architecture": "x86_64",
            "library_suffix": ".so",
            "minimum_version": {"kind": "glibc", "value": "2.34"},
            "operating_system": "linux",
            "wheel_tag": "manylinux_2_34_x86_64",
        },
        "upstream": {
            "commit": UPSTREAM_COMMIT,
            "repository": UPSTREAM_REPOSITORY,
            "version": "0.5.1",
        },
    }
    sources = _grammar_sources(args.language_definitions, args.license_cache)

    (BUNDLE / "asset-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (BUNDLE / "grammar-sources.json").write_text(json.dumps(sources, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
