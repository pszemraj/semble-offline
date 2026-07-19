import struct
import zipfile
from pathlib import Path

import pytest

from scripts.verify_wheel import (
    CPU_TYPE_ARM64,
    DT_RPATH,
    DT_RUNPATH,
    ELF_ET_DYN,
    LC_BUILD_VERSION,
    MACHO_64_LE,
    MH_DYLIB,
    PLATFORM_MACOS,
    PT_DYNAMIC,
    _platform_details,
    _verify_metadata,
    _verify_model_set,
    _verify_native_library,
    verify_wheel,
)


def _macho(
    minimum: tuple[int, int, int],
    cpu_type: int = CPU_TYPE_ARM64,
    file_type: int = MH_DYLIB,
    platform: int = PLATFORM_MACOS,
) -> bytes:
    packed_version = minimum[0] << 16 | minimum[1] << 8 | minimum[2]
    header = MACHO_64_LE + struct.pack("<IIIIIII", cpu_type, 3, file_type, 1, 24, 0, 0)
    command = struct.pack("<IIIIII", LC_BUILD_VERSION, 24, platform, packed_version, packed_version, 0)
    return header + command


def _platform_manifest(operating_system: str = "linux") -> dict[str, object]:
    """Return a canonical platform manifest for verifier unit tests."""
    platform = {
        "architecture": "x86_64",
        "library_suffix": ".so",
        "minimum_version": {"kind": "glibc", "value": "2.34"},
        "operating_system": "linux",
        "wheel_tag": "manylinux_2_34_x86_64",
    }
    if operating_system == "macos":
        platform = {
            "architecture": "arm64",
            "library_suffix": ".dylib",
            "minimum_version": {"kind": "macos", "value": "11.0"},
            "operating_system": "macos",
            "wheel_tag": "macosx_11_0_arm64",
        }
    return {"format_version": 2, "platform": platform}


def _metadata_wheel(
    tmp_path: Path,
    wheel_dirs: tuple[str, ...] = ("semble-0.5.1+offline.2.dist-info",),
    metadata_dir: str = "semble-0.5.1+offline.2.dist-info",
    requires_python: str = ">=3.10,<3.15",
) -> Path:
    """Write the metadata members needed by the metadata verifier."""
    path = tmp_path / "semble-0.5.1+offline.2-py3-none-manylinux_2_34_x86_64.whl"
    with zipfile.ZipFile(path, "w") as wheel:
        for directory in wheel_dirs:
            wheel.writestr(
                f"{directory}/WHEEL",
                "Wheel-Version: 1.0\nRoot-Is-Purelib: false\nTag: py3-none-manylinux_2_34_x86_64\n",
            )
        wheel.writestr(
            f"{metadata_dir}/METADATA",
            f"Metadata-Version: 2.4\nVersion: 0.5.1+offline.2\nRequires-Python: {requires_python}\n",
        )
    return path


def test_accepts_linux_x86_64_header() -> None:
    """The native verifier accepts a 64-bit little-endian x86-64 ELF header."""
    header = bytearray(64)
    header[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", header, 16, ELF_ET_DYN)
    struct.pack_into("<H", header, 18, 62)
    _verify_native_library(bytes(header), "linux")


@pytest.mark.parametrize("dynamic_tag", [DT_RPATH, DT_RUNPATH])
def test_rejects_linux_embedded_library_search_path(dynamic_tag: int) -> None:
    """A Linux grammar cannot retain a build-host RPATH or RUNPATH."""
    header = bytearray(152)
    header[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", header, 16, ELF_ET_DYN)
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


def test_rejects_non_library_elf_type() -> None:
    """An x86-64 ELF executable or object cannot masquerade as a grammar library."""
    header = bytearray(64)
    header[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", header, 18, 62)
    with pytest.raises(RuntimeError, match="not a shared library"):
        _verify_native_library(bytes(header), "linux")


def test_rejects_non_library_macho_type() -> None:
    """An arm64 Mach-O executable cannot masquerade as a grammar dylib."""
    with pytest.raises(RuntimeError, match="not a dynamic library"):
        _verify_native_library(_macho((11, 0, 0), file_type=2), "macos")


def test_rejects_non_macos_build_platform() -> None:
    """An arm64 iOS dylib cannot masquerade as a macOS grammar dylib."""
    with pytest.raises(RuntimeError, match="does not target macOS"):
        _verify_native_library(_macho((11, 0, 0), platform=2), "macos")


@pytest.mark.parametrize("operating_system", ["linux", "macos"])
def test_accepts_canonical_platform_manifest(operating_system: str) -> None:
    """Both release platform declarations are accepted exactly."""
    expected_suffix = ".so" if operating_system == "linux" else ".dylib"
    assert _platform_details(_platform_manifest(operating_system)) == (operating_system, expected_suffix)


@pytest.mark.parametrize("field", ["wheel_tag", "minimum_version"])
def test_rejects_noncanonical_platform_manifest(field: str) -> None:
    """A supported OS and architecture cannot carry an arbitrary tag or floor."""
    manifest = _platform_manifest()
    platform = manifest["platform"]
    assert isinstance(platform, dict)
    platform.pop(field)
    with pytest.raises(RuntimeError, match="supported canonical platform"):
        _platform_details(manifest)


def test_metadata_requires_one_consistent_dist_info_directory(tmp_path: Path) -> None:
    """Multiple or mismatched dist-info metadata directories are rejected."""
    path = _metadata_wheel(tmp_path, wheel_dirs=("first.dist-info", "second.dist-info"))
    with zipfile.ZipFile(path) as wheel:
        with pytest.raises(RuntimeError, match="no unique dist-info"):
            _verify_metadata(path, wheel, set(wheel.namelist()), _platform_manifest())

    path = _metadata_wheel(tmp_path, wheel_dirs=("first.dist-info",), metadata_dir="second.dist-info")
    with zipfile.ZipFile(path) as wheel:
        with pytest.raises(RuntimeError, match="different dist-info directories"):
            _verify_metadata(path, wheel, set(wheel.namelist()), _platform_manifest())


def test_metadata_enforces_supported_python_range(tmp_path: Path) -> None:
    """Wheel metadata cannot claim support beyond the tested interpreter matrix."""
    path = _metadata_wheel(tmp_path, requires_python=">=3.10")
    with zipfile.ZipFile(path) as wheel:
        with pytest.raises(RuntimeError, match="CPython 3.10 through 3.14"):
            _verify_metadata(path, wheel, set(wheel.namelist()), _platform_manifest())


def test_rejects_undeclared_model_member() -> None:
    """Every packaged model file must be declared by the asset manifest."""
    manifest = {"model": {"files": {"config.json": "unused"}}}
    names = {"semble/_bundled/model/config.json", "semble/_bundled/model/stale.safetensors"}
    with pytest.raises(RuntimeError, match="model contents do not match"):
        _verify_model_set(names, manifest)


def test_rejects_duplicate_wheel_members(tmp_path: Path) -> None:
    """Duplicate ZIP members cannot hide conflicting release content."""
    path = tmp_path / "duplicate.whl"
    with pytest.warns(UserWarning, match="Duplicate name"):
        with zipfile.ZipFile(path, "w") as wheel:
            wheel.writestr("duplicate", b"first")
            wheel.writestr("duplicate", b"second")
    with pytest.raises(RuntimeError, match="duplicate member names"):
        verify_wheel(path)
