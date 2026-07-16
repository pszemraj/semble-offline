"""Setuptools hooks for the platform-specific offline wheel."""

from __future__ import annotations

import platform
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.bdist_wheel import bdist_wheel
from setuptools.command.build_py import build_py
from setuptools.dist import Distribution

_WHEEL_PLATFORM = "manylinux_2_34_x86_64"


class OfflineWheel(bdist_wheel):
    """Mark bundled ELF grammar libraries as platform-specific package data."""

    def finalize_options(self) -> None:
        """Place the package in platform-specific wheel paths."""
        super().finalize_options()
        self.root_is_pure = False

    def get_tag(self) -> tuple[str, str, str]:
        """Return the single supported interpreter, ABI, and platform tag."""
        return "py3", "none", _WHEEL_PLATFORM


class BinaryDistribution(Distribution):
    """Treat packaged grammar shared libraries as platform-specific code."""

    def has_ext_modules(self) -> bool:
        """Return true so package modules are installed into platlib."""
        return True


class OfflineBuildPy(build_py):
    """Enforce the EBNF exclusion even when a local build directory is stale."""

    def run(self) -> None:
        """Build Python modules and remove the prohibited grammar if present."""
        super().run()
        ebnf = Path(self.build_lib) / "semble" / "_bundled" / "grammars" / "libtree_sitter_ebnf.so"
        ebnf.unlink(missing_ok=True)


if sys.platform != "linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
    raise RuntimeError("Semble Offline can only be built and installed on Linux x86_64")

setup(distclass=BinaryDistribution, cmdclass={"bdist_wheel": OfflineWheel, "build_py": OfflineBuildPy})
