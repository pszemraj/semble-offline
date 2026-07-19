#!/usr/bin/env python3
"""Verify the structure, tags, assets, and native binaries of an offline wheel."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import zipfile
from pathlib import Path
from typing import Any

GRAMMAR_PREFIX = "semble/_bundled/grammars/"
MANIFEST_PATH = "semble/_bundled/asset-manifest.json"
SOURCES_PATH = "semble/_bundled/grammar-sources.json"
MACHO_64_LE = b"\xcf\xfa\xed\xfe"
CPU_TYPE_ARM64 = 0x0100000C
MH_DYLIB = 6
PLATFORM_MACOS = 1
LC_VERSION_MIN_MACOSX = 0x24
LC_BUILD_VERSION = 0x32
PT_DYNAMIC = 2
DT_RPATH = 15
DT_RUNPATH = 29
ELF_ET_DYN = 3
SUPPORTED_PLATFORMS = {
    ("linux", "x86_64"): {
        "library_suffix": ".so",
        "minimum_version": {"kind": "glibc", "value": "2.34"},
        "wheel_tag": "manylinux_2_34_x86_64",
    },
    ("macos", "arm64"): {
        "library_suffix": ".dylib",
        "minimum_version": {"kind": "macos", "value": "11.0"},
        "wheel_tag": "macosx_11_0_arm64",
    },
}


def _sha256(data: bytes) -> str:
    """Return the SHA-256 digest for data."""
    return hashlib.sha256(data).hexdigest()


def _json_object(wheel: zipfile.ZipFile, path: str) -> dict[str, Any]:
    """Load a required JSON object from a wheel member."""
    try:
        value = json.loads(wheel.read(path))
    except (KeyError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Wheel contains no valid {path}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"Wheel member is not a JSON object: {path}")
    return value


def _metadata_value(text: str, field: str) -> str:
    """Return a required RFC822-style metadata field."""
    match = re.search(rf"^{re.escape(field)}: (.+)$", text, flags=re.MULTILINE)
    if not match:
        raise RuntimeError(f"Wheel metadata is missing {field}")
    return match.group(1).strip()


def _verify_metadata(path: Path, wheel: zipfile.ZipFile, names: set[str], manifest: dict[str, Any]) -> None:
    """Verify platform-specific wheel metadata and its filename."""
    wheel_metadata_paths = sorted(name for name in names if re.fullmatch(r"[^/]+\.dist-info/WHEEL", name))
    package_metadata_paths = sorted(name for name in names if re.fullmatch(r"[^/]+\.dist-info/METADATA", name))
    if len(wheel_metadata_paths) != 1 or len(package_metadata_paths) != 1:
        raise RuntimeError("Wheel has no unique dist-info WHEEL and METADATA files")
    wheel_metadata_path = wheel_metadata_paths[0]
    package_metadata_path = package_metadata_paths[0]
    if wheel_metadata_path.rsplit("/", 1)[0] != package_metadata_path.rsplit("/", 1)[0]:
        raise RuntimeError("Wheel WHEEL and METADATA files use different dist-info directories")
    wheel_metadata = wheel.read(wheel_metadata_path).decode("utf-8")
    package_metadata = wheel.read(package_metadata_path).decode("utf-8")
    wheel_tag = str(manifest["platform"]["wheel_tag"])
    version = _metadata_value(package_metadata, "Version")
    python_requirement = {clause.strip() for clause in _metadata_value(package_metadata, "Requires-Python").split(",")}
    if python_requirement != {">=3.10", "<3.15"}:
        raise RuntimeError("Wheel metadata must require CPython 3.10 through 3.14")
    expected_name = f"semble-{version}-py3-none-{wheel_tag}.whl"
    if path.name != expected_name:
        raise RuntimeError(f"Unexpected wheel filename: {path.name}; expected {expected_name}")
    if "Root-Is-Purelib: false" not in wheel_metadata:
        raise RuntimeError("Wheel metadata does not mark the distribution as platform-specific")
    expected_tag = f"Tag: py3-none-{wheel_tag}"
    if expected_tag not in wheel_metadata:
        raise RuntimeError(f"Wheel metadata is missing {expected_tag}")


def _verify_required_files(names: set[str]) -> None:
    """Verify that provenance, license, and core model files are packaged."""
    required = {
        "semble/_bundled/THIRD_PARTY_NOTICES.md",
        "semble/_bundled/LICENSE.tree-sitter-language-pack",
        MANIFEST_PATH,
        SOURCES_PATH,
        "semble/_bundled/model/model.safetensors",
    }
    if missing := sorted(required - names):
        raise RuntimeError(f"Wheel is missing required bundled files: {missing}")


def _unpack_macos_version(value: int) -> tuple[int, int, int]:
    """Decode Apple's packed major.minor.patch version integer."""
    return value >> 16, value >> 8 & 0xFF, value & 0xFF


def _macho_minimum_versions(data: bytes) -> list[tuple[int, int, int]]:
    """Return minimum macOS versions from a validated Mach-O load-command table."""
    command_count = struct.unpack_from("<I", data, 16)[0]
    offset = 32
    minimum_versions: list[tuple[int, int, int]] = []
    for _ in range(command_count):
        if offset + 8 > len(data):
            raise RuntimeError("Mach-O load command table is truncated")
        command, size = struct.unpack_from("<II", data, offset)
        if size < 8 or offset + size > len(data):
            raise RuntimeError("Mach-O load command has an invalid size")
        if command == LC_BUILD_VERSION:
            if size < 24:
                raise RuntimeError("Mach-O LC_BUILD_VERSION is truncated")
            if struct.unpack_from("<I", data, offset + 8)[0] != PLATFORM_MACOS:
                raise RuntimeError("Mach-O grammar does not target macOS")
            minimum_versions.append(_unpack_macos_version(struct.unpack_from("<I", data, offset + 12)[0]))
        elif command == LC_VERSION_MIN_MACOSX:
            if size < 16:
                raise RuntimeError("Mach-O LC_VERSION_MIN_MACOSX is truncated")
            minimum_versions.append(_unpack_macos_version(struct.unpack_from("<I", data, offset + 8)[0]))
        offset += size
    return minimum_versions


def _verify_macho_arm64(data: bytes, maximum_minimum: tuple[int, int, int]) -> None:
    """Verify a thin arm64 Mach-O and its declared minimum macOS version."""
    if len(data) < 32 or data[:4] != MACHO_64_LE:
        raise RuntimeError("grammar is not a thin 64-bit little-endian Mach-O library")
    if struct.unpack_from("<I", data, 4)[0] != CPU_TYPE_ARM64:
        raise RuntimeError("Mach-O grammar is not arm64")
    if struct.unpack_from("<I", data, 12)[0] != MH_DYLIB:
        raise RuntimeError("Mach-O grammar is not a dynamic library")
    minimum_versions = _macho_minimum_versions(data)
    if not minimum_versions:
        raise RuntimeError("Mach-O grammar declares no minimum macOS version")
    if max(minimum_versions) > maximum_minimum:
        actual = ".".join(map(str, max(minimum_versions)))
        expected = ".".join(map(str, maximum_minimum))
        raise RuntimeError(f"Mach-O grammar requires macOS {actual}, newer than {expected}")


def _verify_no_elf_search_paths(data: bytes) -> None:
    """Reject embedded runtime search paths from an ELF program-header table."""
    program_offset = struct.unpack_from("<Q", data, 32)[0]
    program_entry_size = struct.unpack_from("<H", data, 54)[0]
    program_count = struct.unpack_from("<H", data, 56)[0]
    if program_count and program_entry_size < 56:
        raise RuntimeError("ELF program-header entry is truncated")
    if program_offset + program_entry_size * program_count > len(data):
        raise RuntimeError("ELF program-header table is truncated")

    for index in range(program_count):
        header_offset = program_offset + index * program_entry_size
        if struct.unpack_from("<I", data, header_offset)[0] != PT_DYNAMIC:
            continue
        dynamic_offset = struct.unpack_from("<Q", data, header_offset + 8)[0]
        dynamic_size = struct.unpack_from("<Q", data, header_offset + 32)[0]
        if dynamic_size % 16 or dynamic_offset + dynamic_size > len(data):
            raise RuntimeError("ELF dynamic table is truncated")
        for entry_offset in range(dynamic_offset, dynamic_offset + dynamic_size, 16):
            tag = struct.unpack_from("<q", data, entry_offset)[0]
            if tag == 0:
                break
            if tag in {DT_RPATH, DT_RUNPATH}:
                raise RuntimeError("ELF grammar contains an embedded RPATH or RUNPATH")


def _verify_elf_x86_64(data: bytes) -> None:
    """Verify a little-endian 64-bit x86-64 ELF library without embedded search paths."""
    if len(data) < 64 or data[:4] != b"\x7fELF" or data[4:6] != b"\x02\x01":
        raise RuntimeError("grammar is not a 64-bit little-endian ELF library")
    if struct.unpack_from("<H", data, 16)[0] != ELF_ET_DYN:
        raise RuntimeError("ELF grammar is not a shared library")
    if struct.unpack_from("<H", data, 18)[0] != 62:
        raise RuntimeError("ELF grammar is not x86-64")
    _verify_no_elf_search_paths(data)


def _verify_native_library(data: bytes, operating_system: str) -> None:
    """Verify a grammar library's native format and architecture."""
    if operating_system == "linux":
        _verify_elf_x86_64(data)
    elif operating_system == "macos":
        _verify_macho_arm64(data, (11, 0, 0))
    else:
        raise RuntimeError(f"Unsupported manifest operating system: {operating_system}")


def _platform_details(manifest: dict[str, Any]) -> tuple[str, str]:
    """Return a consistent operating-system and native-library suffix pair."""
    if manifest.get("format_version") != 2:
        raise RuntimeError("Wheel must contain asset manifest format 2")
    platform_data = manifest.get("platform", {})
    if not isinstance(platform_data, dict):
        raise RuntimeError("Wheel platform manifest is not an object")
    operating_system = str(platform_data.get("operating_system", ""))
    platform_key = (operating_system, platform_data.get("architecture"))
    expected = SUPPORTED_PLATFORMS.get(platform_key)
    if expected is None or any(platform_data.get(key) != value for key, value in expected.items()):
        raise RuntimeError("Manifest does not declare a supported canonical platform")
    return operating_system, str(expected["library_suffix"])


def _grammar_members(names: set[str]) -> set[str]:
    """Return every native grammar member under the canonical wheel path."""
    # Keep Windows libraries visible so exact-set validation rejects them instead of silently ignoring them.
    return {
        name.removeprefix(GRAMMAR_PREFIX)
        for name in names
        if name.startswith(GRAMMAR_PREFIX) and name.endswith((".so", ".dylib", ".dll"))
    }


def _verify_grammar_set(
    wheel: zipfile.ZipFile,
    native_members: set[str],
    manifest: dict[str, Any],
    suffix: str,
) -> dict[str, str]:
    """Verify the exact grammar set and its source-provenance mapping."""
    expected_grammars = manifest["grammars"]["files"]
    if not isinstance(expected_grammars, dict):
        raise RuntimeError("Manifest grammars.files is not an object")

    if native_members != set(expected_grammars):
        raise RuntimeError("Wheel grammar contents do not match the asset manifest")
    expected_count = manifest["grammars"].get("expected_count")
    if expected_count != 264 or len(native_members) != expected_count:
        raise RuntimeError("Wheel must contain exactly 264 grammars")
    if any(not name.endswith(suffix) for name in native_members) or f"libtree_sitter_ebnf{suffix}" in native_members:
        raise RuntimeError("Wheel has a wrong-platform grammar or includes EBNF")

    grammar_sources = _json_object(wheel, SOURCES_PATH)
    source_libraries = {source.get("library") for source in grammar_sources.values() if isinstance(source, dict)}
    if len(grammar_sources) != 264 or source_libraries != native_members:
        raise RuntimeError("Grammar source provenance does not match the wheel libraries")
    return expected_grammars


def _verify_file_hashes(
    wheel: zipfile.ZipFile,
    expected_grammars: dict[str, str],
    manifest: dict[str, Any],
    operating_system: str,
) -> None:
    """Verify grammar/model hashes and native grammar headers."""
    for filename, expected_hash in expected_grammars.items():
        data = wheel.read(f"{GRAMMAR_PREFIX}{filename}")
        if _sha256(data) != expected_hash:
            raise RuntimeError(f"Grammar hash mismatch: {filename}")
        try:
            _verify_native_library(data, operating_system)
        except RuntimeError as error:
            raise RuntimeError(f"Invalid native grammar {filename}: {error}") from error
    for filename, expected_hash in manifest["model"]["files"].items():
        if _sha256(wheel.read(f"semble/_bundled/model/{filename}")) != expected_hash:
            raise RuntimeError(f"Model hash mismatch: {filename}")


def _verify_model_set(names: set[str], manifest: dict[str, Any]) -> None:
    """Verify that every packaged model file is declared in the manifest."""
    prefix = "semble/_bundled/model/"
    actual = {name.removeprefix(prefix) for name in names if name.startswith(prefix) and not name.endswith("/")}
    model_data = manifest.get("model")
    expected = model_data.get("files") if isinstance(model_data, dict) else None
    if not isinstance(expected, dict) or actual != set(expected):
        raise RuntimeError("Wheel model contents do not match the asset manifest")


def _verify_asset_hashes(wheel: zipfile.ZipFile, names: set[str], manifest: dict[str, Any]) -> None:
    """Verify exact grammar contents, provenance mapping, and bundled asset digests."""
    operating_system, suffix = _platform_details(manifest)
    _verify_model_set(names, manifest)
    native_members = _grammar_members(names)
    expected_grammars = _verify_grammar_set(wheel, native_members, manifest, suffix)
    _verify_file_hashes(wheel, expected_grammars, manifest, operating_system)


def verify_wheel(path: Path) -> None:
    """Raise an actionable exception if path is not a valid release wheel."""
    with zipfile.ZipFile(path) as wheel:
        members = wheel.namelist()
        names = set(members)
        if len(members) != len(names):
            raise RuntimeError("Wheel contains duplicate member names")
        _verify_required_files(names)
        manifest = _json_object(wheel, MANIFEST_PATH)
        _platform_details(manifest)
        _verify_metadata(path, wheel, names, manifest)
        _verify_asset_hashes(wheel, names, manifest)


def main() -> None:
    """Parse arguments, verify a wheel, and print a concise success result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    verify_wheel(args.wheel)
    print(f"Verified {args.wheel.name}: tag, notices, model, and 264 native grammar hashes are correct")


if __name__ == "__main__":
    main()
