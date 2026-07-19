#!/usr/bin/env python3
"""Build a pinned, platform-specific tree-sitter grammar bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "src" / "semble" / "_bundled"
GRAMMAR_SOURCES = BUNDLE / "grammar-sources.json"
BASE_MANIFEST = BUNDLE / "asset-manifest.json"
CXX_LINKER_PATCH = ROOT / "scripts" / "patches" / "tree-sitter-language-pack-cxx-linker.patch"
PINNED_REVISIONS_PATCH = ROOT / "scripts" / "patches" / "tree-sitter-language-pack-pinned-revisions.patch"
LANGUAGE_PACK_PATCHES = (CXX_LINKER_PATCH, PINNED_REVISIONS_PATCH)

LANGUAGE_PACK_REPOSITORY = "https://github.com/kreuzberg-dev/tree-sitter-language-pack"
LANGUAGE_PACK_VERSION = "1.6.2"
LANGUAGE_PACK_COMMIT = "6bb9761028dfc3a72329d15f0f339ec7ccb56159"
TREE_SITTER_CLI_VERSION = "0.26.8"
RUST_TOOLCHAIN = "1.91"

PLATFORMS: dict[str, dict[str, Any]] = {
    "linux-x86_64": {
        "architecture": "x86_64",
        "library_suffix": ".so",
        "minimum_version": {"kind": "glibc", "value": "2.34"},
        "operating_system": "linux",
        "wheel_tag": "manylinux_2_34_x86_64",
    },
    "macos-arm64": {
        "architecture": "arm64",
        "library_suffix": ".dylib",
        "minimum_version": {"kind": "macos", "value": "11.0"},
        "operating_system": "macos",
        "wheel_tag": "macosx_11_0_arm64",
    },
}


def _run(*args: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    """Run a required subprocess and echo its shell-safe command."""
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=cwd, env=env, check=True)


def _output(*args: str, cwd: Path | None = None) -> str:
    """Return stripped stdout from a required subprocess."""
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object from path."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"Expected a JSON object in {path}")
    return value


def _sha256(path: Path) -> str:
    """Return a file's SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _host_platform() -> str:
    """Return the supported platform identifier for the current build host."""
    machine = platform.machine().lower()
    if sys.platform == "linux" and machine in {"x86_64", "amd64"}:
        return "linux-x86_64"
    if sys.platform == "darwin" and machine in {"arm64", "aarch64"}:
        return "macos-arm64"
    return f"{sys.platform}-{machine}"


def _library_name(definition: dict[str, Any], language: str, suffix: str) -> str:
    """Return the library filename implied by a language-pack definition."""
    symbol = str(definition.get("c_symbol", language))
    return f"libtree_sitter_{symbol}{suffix}"


def _license_key(repository: str) -> str:
    """Return the language-pack license-cache key for a GitHub repository URL."""
    return repository.removeprefix("https://github.com/").removesuffix(".git")


def validate_sources(selected_sources: dict[str, Any], definitions: dict[str, Any], licenses: dict[str, Any]) -> None:
    """Ensure language-pack definitions exactly match the checked-in source pins."""
    errors: list[str] = []
    for language, raw_source in selected_sources.items():
        source = raw_source if isinstance(raw_source, dict) else {}
        definition = definitions.get(language)
        if not isinstance(definition, dict):
            errors.append(f"{language}: missing language-pack definition")
            continue
        repository = str(definition.get("repo", ""))
        expected_library = _library_name(definition, language, ".so")
        checks = {
            "repository": (source.get("repository"), repository),
            "revision": (source.get("revision"), definition.get("rev")),
            "library": (source.get("library"), expected_library),
            "license": (source.get("license"), licenses.get(_license_key(repository), "UNKNOWN")),
        }
        for field, (actual, expected) in checks.items():
            if actual != expected:
                errors.append(f"{language}: {field} is {actual!r}, expected {expected!r}")
    if errors:
        raise RuntimeError("Pinned grammar metadata does not match language-pack v1.6.2:\n" + "\n".join(errors))


def _check_tool_versions() -> None:
    """Require the pinned Rust toolchain and tree-sitter CLI."""
    rust_version = _output("rustup", "run", RUST_TOOLCHAIN, "rustc", "--version")
    if not rust_version.startswith(f"rustc {RUST_TOOLCHAIN}.") and not rust_version.startswith(
        f"rustc {RUST_TOOLCHAIN} "
    ):
        raise RuntimeError(f"Expected Rust {RUST_TOOLCHAIN}; found {rust_version}")
    tree_sitter_version = _output("tree-sitter", "--version")
    if tree_sitter_version != f"tree-sitter {TREE_SITTER_CLI_VERSION}":
        raise RuntimeError(f"Expected tree-sitter {TREE_SITTER_CLI_VERSION}; found {tree_sitter_version}")


def _compiler_provenance() -> dict[str, str]:
    """Return compiler identities and any configured target sysroot."""
    cc = os.environ.get("CC", "cc")
    cxx = os.environ.get("CXX", "c++")
    provenance = {
        "c_compiler": _output(cc, "--version").splitlines()[0],
        "cxx_compiler": _output(cxx, "--version").splitlines()[0],
    }
    sysroot = os.environ.get("SDKROOT") or os.environ.get("CONDA_BUILD_SYSROOT", "")
    if not sysroot:
        command = ("xcrun", "--show-sdk-path") if sys.platform == "darwin" else (cxx, "-print-sysroot")
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        if result.returncode == 0:
            sysroot = result.stdout.strip()
    if sysroot:
        provenance["compiler_sysroot"] = sysroot
    return provenance


def _clone_language_pack(checkout: Path) -> None:
    """Clone and patch the exact language-pack source revision."""
    _run("git", "clone", "--filter=blob:none", "--no-checkout", LANGUAGE_PACK_REPOSITORY, str(checkout))
    _run("git", "checkout", "--detach", LANGUAGE_PACK_COMMIT, cwd=checkout)
    if _output("git", "rev-parse", "HEAD", cwd=checkout) != LANGUAGE_PACK_COMMIT:
        raise RuntimeError("Language-pack checkout did not resolve to the pinned commit")
    for patch in LANGUAGE_PACK_PATCHES:
        # Zero-context patches are tied to the verified commit above; --check makes any layout drift fail first.
        _run("git", "apply", "--unidiff-zero", "--check", str(patch), cwd=checkout)
        _run("git", "apply", "--unidiff-zero", str(patch), cwd=checkout)


def _write_filtered_definitions(checkout: Path, definitions: dict[str, Any]) -> None:
    """Limit the temporary language-pack checkout to the selected source set."""
    content = json.dumps(definitions, indent=2, sort_keys=True) + "\n"
    (checkout / "sources" / "language_definitions.json").write_text(content, encoding="utf-8")
    (checkout / "crates" / "ts-pack-core" / "language_definitions.json").write_text(content, encoding="utf-8")


def _build_libraries(checkout: Path, languages: list[str], platform_name: str) -> list[Path]:
    """Clone pinned parser sources and compile the selected dynamic libraries."""
    environment = os.environ.copy()
    environment.update(
        {
            "PROJECT_ROOT": str(checkout),
            "TSLP_LANGUAGES": ",".join(languages),
            "TSLP_LINK_MODE": "dynamic",
            "TSLP_NO_CACHE": "1",
        }
    )
    if platform_name == "macos-arm64":
        environment["MACOSX_DEPLOYMENT_TARGET"] = "11.0"

    _run(sys.executable, "scripts/clone_vendors.py", cwd=checkout, env=environment)
    missing_sources = [
        language for language in languages if not (checkout / "parsers" / language / "src" / "parser.c").is_file()
    ]
    if missing_sources:
        raise RuntimeError(f"Parser generation produced no parser.c for: {missing_sources}")
    _run(
        "rustup",
        "run",
        RUST_TOOLCHAIN,
        "cargo",
        "build",
        "--locked",
        "--package",
        "tree-sitter-language-pack",
        "--release",
        cwd=checkout,
        env=environment,
    )
    suffix = str(PLATFORMS[platform_name]["library_suffix"])
    return sorted((checkout / "target" / "release" / "build").glob(f"*/out/libs/libtree_sitter_*{suffix}"))


def _set_macos_install_name(library: Path) -> None:
    """Replace a build-directory dylib ID with its stable packaged identity."""
    _run("install_name_tool", "-id", f"@rpath/{library.name}", str(library))


def _stage_bundle(
    output: Path,
    built_libraries: list[Path],
    selected_sources: dict[str, Any],
    selected_definitions: dict[str, Any],
    platform_name: str,
) -> None:
    """Write libraries and deterministic platform metadata to output."""
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"Output directory must be absent or empty: {output}")
    grammar_dir = output / "grammars"
    grammar_dir.mkdir(parents=True, exist_ok=True)
    suffix = str(PLATFORMS[platform_name]["library_suffix"])
    expected_names = {_library_name(selected_definitions[language], language, suffix) for language in selected_sources}
    by_name: dict[str, Path] = {}
    for library in built_libraries:
        if library.name in by_name:
            raise RuntimeError(f"Build produced duplicate grammar library: {library.name}")
        by_name[library.name] = library
    if set(by_name) != expected_names:
        missing = sorted(expected_names - set(by_name))
        unexpected = sorted(set(by_name) - expected_names)
        raise RuntimeError(f"Built grammar set mismatch; missing={missing}, unexpected={unexpected}")

    for name, source_path in sorted(by_name.items()):
        staged_path = grammar_dir / name
        shutil.copy2(source_path, staged_path)
        if platform_name == "macos-arm64":
            _set_macos_install_name(staged_path)
    files = {path.name: _sha256(path) for path in sorted(grammar_dir.iterdir())}

    base_manifest = _load_json(BASE_MANIFEST)
    provenance = {
        **_compiler_provenance(),
        "kind": "source-build",
        "language_pack_commit": LANGUAGE_PACK_COMMIT,
        "linker_patch_sha256": _sha256(CXX_LINKER_PATCH),
        "rust_toolchain": RUST_TOOLCHAIN,
        "tree_sitter_cli": TREE_SITTER_CLI_VERSION,
        "vendor_fetch_patch_sha256": _sha256(PINNED_REVISIONS_PATCH),
    }
    if platform_name == "macos-arm64":
        provenance["install_name_pattern"] = "@rpath/<filename>"
    manifest = {
        "format_version": 2,
        "grammars": {
            "aliases": base_manifest["grammars"]["aliases"],
            "excluded": base_manifest["grammars"]["excluded"],
            "expected_count": len(files),
            "files": files,
            "package": "tree-sitter-language-pack",
            "provenance": provenance,
            "version": LANGUAGE_PACK_VERSION,
        },
        "model": base_manifest["model"],
        "platform": PLATFORMS[platform_name],
        "upstream": base_manifest["upstream"],
    }
    staged_sources = {
        language: {**source, "library": _library_name(selected_definitions[language], language, suffix)}
        for language, source in selected_sources.items()
    }
    (output / "asset-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "grammar-sources.json").write_text(
        json.dumps(staged_sources, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    """Build a selected or complete grammar bundle on its native platform."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True, choices=sorted(PLATFORMS))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--grammar", action="append", default=[], help="Build one grammar; repeat as needed")
    args = parser.parse_args()

    if _host_platform() != args.platform:
        raise RuntimeError(f"Requested {args.platform}, but the current host is {_host_platform()}")
    all_sources = _load_json(GRAMMAR_SOURCES)
    requested = sorted(set(args.grammar)) if args.grammar else sorted(all_sources)
    unknown = sorted(set(requested) - set(all_sources))
    if unknown:
        raise RuntimeError(f"Unknown or unbundled grammar names: {unknown}")
    selected_sources = {language: all_sources[language] for language in requested}

    with tempfile.TemporaryDirectory(prefix="semble-grammar-build-") as temporary:
        checkout = Path(temporary) / "tree-sitter-language-pack"
        _clone_language_pack(checkout)
        definitions = _load_json(checkout / "sources" / "language_definitions.json")
        licenses = _load_json(checkout / "sources" / "license_cache.json")
        validate_sources(selected_sources, definitions, licenses)
        selected_definitions = {language: definitions[language] for language in requested}
        _check_tool_versions()
        _write_filtered_definitions(checkout, selected_definitions)
        built_libraries = _build_libraries(checkout, requested, args.platform)
        _stage_bundle(args.output.resolve(), built_libraries, selected_sources, selected_definitions, args.platform)

    print(f"Built {len(requested)} {args.platform} grammar libraries in {args.output}")


if __name__ == "__main__":
    main()
