import struct

import pytest

from scripts.verify_wheel import (
    CPU_TYPE_ARM64,
    DT_RPATH,
    DT_RUNPATH,
    LC_BUILD_VERSION,
    MACHO_64_LE,
    PT_DYNAMIC,
    _verify_native_library,
)


def _macho(minimum: tuple[int, int, int], cpu_type: int = CPU_TYPE_ARM64) -> bytes:
    packed_version = minimum[0] << 16 | minimum[1] << 8 | minimum[2]
    header = MACHO_64_LE + struct.pack("<IIIIIII", cpu_type, 3, 6, 1, 24, 0, 0)
    command = struct.pack("<IIIIII", LC_BUILD_VERSION, 24, 1, packed_version, packed_version, 0)
    return header + command


def test_accepts_linux_x86_64_header() -> None:
    """The native verifier accepts a 64-bit little-endian x86-64 ELF header."""
    header = bytearray(64)
    header[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", header, 18, 62)
    _verify_native_library(bytes(header), "linux")


@pytest.mark.parametrize("dynamic_tag", [DT_RPATH, DT_RUNPATH])
def test_rejects_linux_embedded_library_search_path(dynamic_tag: int) -> None:
    """A Linux grammar cannot retain a build-host RPATH or RUNPATH."""
    header = bytearray(152)
    header[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", header, 18, 62)
    struct.pack_into("<Q", header, 32, 64)
    struct.pack_into("<H", header, 54, 56)
    struct.pack_into("<H", header, 56, 1)
    struct.pack_into("<IIQQQQQQ", header, 64, PT_DYNAMIC, 0, 120, 0, 0, 32, 32, 8)
    struct.pack_into("<qQqQ", header, 120, dynamic_tag, 0, 0, 0)
    with pytest.raises(RuntimeError, match="embedded RPATH or RUNPATH"):
        _verify_native_library(bytes(header), "linux")


def test_accepts_macos_11_arm64_header() -> None:
    """The native verifier accepts an arm64 Mach-O targeting macOS 11."""
    _verify_native_library(_macho((11, 0, 0)), "macos")


def test_rejects_newer_macos_deployment_target() -> None:
    """A dylib requiring a newer OS than its wheel tag is rejected."""
    with pytest.raises(RuntimeError, match="newer than 11.0.0"):
        _verify_native_library(_macho((15, 5, 0)), "macos")


def test_rejects_wrong_macos_architecture() -> None:
    """An Intel dylib cannot be mislabeled as an arm64 wheel asset."""
    with pytest.raises(RuntimeError, match="not arm64"):
        _verify_native_library(_macho((11, 0, 0), cpu_type=0x01000007), "macos")
