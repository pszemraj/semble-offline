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

UPSTREAM_REPOSITORY = "https://github.com/MinishLab/semble"
UPSTREAM_COMMIT = "a1ba6c18a4b0a58a3d1a15217d64bc92678d1d9d"
MODEL_REPOSITORY = "https://huggingface.co/minishlab/potion-code-16M-v2"
MODEL_REVISION = "e9d2a44ca6a05ac6685f3b23709ea57eb7352d5b"
GRAMMAR_PACKAGE = "tree-sitter-language-pack"
GRAMMAR_VERSION = "1.6.2"
GRAMMAR_ARCHIVE_URL = (
    "https://github.com/kreuzberg-dev/tree-sitter-language-pack/releases/download/v1.6.2/parsers-linux-x86_64.tar.zst"
)
GRAMMAR_ARCHIVE_SHA256 = "5b5a4d2d5319b7d2fae6c7a87e8bf8618c6c827842dba7641a93693980e6b5ea"
GRAMMAR_ARCHIVE_SIZE = 19_134_009


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


def main() -> None:
    """Write asset metadata for the extras declared in grammar-sources.json."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    sources = _load_json(BUNDLE / "grammar-sources.json")
    grammar_files = _file_hashes(GRAMMARS, "libtree_sitter_*.so")
    expected = {source["library"] for source in sources.values()}
    if set(grammar_files) != expected:
        raise RuntimeError("Bundled grammar files do not match grammar-sources.json")

    manifest = {
        "format_version": 2,
        "grammars": {
            "aliases": {},
            "excluded": {},
            "expected_count": len(sources),
            "files": grammar_files,
            "package": GRAMMAR_PACKAGE,
            "provenance": {
                "base": {
                    "archive_sha256": GRAMMAR_ARCHIVE_SHA256,
                    "archive_size": GRAMMAR_ARCHIVE_SIZE,
                    "archive_url": GRAMMAR_ARCHIVE_URL,
                    "kind": "release-archive",
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
            "version": "0.7.3",
        },
    }

    (BUNDLE / "asset-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
