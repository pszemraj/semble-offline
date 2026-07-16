#!/usr/bin/env python3
"""Verify the structure, tags, assets, and hashes of a Semble Offline wheel."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

EXPECTED_NAME = "semble-0.5.1+offline.1-py3-none-manylinux_2_34_x86_64.whl"
EXPECTED_TAG = "Tag: py3-none-manylinux_2_34_x86_64"
GRAMMAR_PREFIX = "semble/_bundled/grammars/"


def _sha256(data: bytes) -> str:
    """Return the SHA-256 digest for data."""
    return hashlib.sha256(data).hexdigest()


def _verify_metadata(wheel: zipfile.ZipFile, names: set[str]) -> None:
    """Verify platform-specific wheel metadata."""
    metadata_path = next(name for name in names if re.fullmatch(r"[^/]+\.dist-info/WHEEL", name))
    metadata = wheel.read(metadata_path).decode("utf-8")
    if "Root-Is-Purelib: false" not in metadata:
        raise RuntimeError("Wheel metadata does not mark the distribution as platform-specific")
    if EXPECTED_TAG not in metadata:
        raise RuntimeError(f"Wheel metadata is missing {EXPECTED_TAG}")


def _verify_required_files(names: set[str]) -> None:
    """Verify that provenance, license, and core model files are packaged."""
    required = {
        "semble/_bundled/THIRD_PARTY_NOTICES.md",
        "semble/_bundled/LICENSE.tree-sitter-language-pack",
        "semble/_bundled/asset-manifest.json",
        "semble/_bundled/grammar-sources.json",
        "semble/_bundled/model/model.safetensors",
    }
    if missing := sorted(required - names):
        raise RuntimeError(f"Wheel is missing required bundled files: {missing}")


def _verify_asset_hashes(wheel: zipfile.ZipFile, names: set[str]) -> None:
    """Verify exact grammar contents and every bundled asset digest."""
    manifest = json.loads(wheel.read("semble/_bundled/asset-manifest.json"))
    expected_grammars = manifest["grammars"]["files"]
    actual_grammars = {
        name.removeprefix(GRAMMAR_PREFIX) for name in names if name.startswith(GRAMMAR_PREFIX) and name.endswith(".so")
    }
    if actual_grammars != set(expected_grammars):
        raise RuntimeError("Wheel grammar contents do not match the asset manifest")
    if len(actual_grammars) != 264 or "libtree_sitter_ebnf.so" in actual_grammars:
        raise RuntimeError("Wheel must contain exactly 264 grammars and exclude EBNF")

    for filename, expected_hash in expected_grammars.items():
        if _sha256(wheel.read(f"{GRAMMAR_PREFIX}{filename}")) != expected_hash:
            raise RuntimeError(f"Grammar hash mismatch: {filename}")
    for filename, expected_hash in manifest["model"]["files"].items():
        if _sha256(wheel.read(f"semble/_bundled/model/{filename}")) != expected_hash:
            raise RuntimeError(f"Model hash mismatch: {filename}")


def verify_wheel(path: Path) -> None:
    """Raise an actionable exception if path is not the expected release wheel."""
    if path.name != EXPECTED_NAME:
        raise RuntimeError(f"Unexpected wheel filename: {path.name}; expected {EXPECTED_NAME}")
    with zipfile.ZipFile(path) as wheel:
        names = set(wheel.namelist())
        _verify_metadata(wheel, names)
        _verify_required_files(names)
        _verify_asset_hashes(wheel, names)


def main() -> None:
    """Parse arguments, verify a wheel, and print a concise success result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    verify_wheel(args.wheel)
    print(f"Verified {args.wheel.name}: platform tag, notices, model, and 264 grammar hashes are correct")


if __name__ == "__main__":
    main()
