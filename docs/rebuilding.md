# Rebuilding and releases

The checked-in source bundle builds the Linux wheel directly. The macOS wheel first requires a native grammar bundle generated from the pinned source revisions. GitHub Actions runs both paths in `.github/workflows/wheels.yaml`; this is the authoritative release build and does not require a maintainer laptop.

## Linux wheel

On Linux x86_64, activate a development environment and run:

```bash
python -m pip install -e ".[dev,mcp]"
python -m pip install "build==1.5.0" "auditwheel==6.7.0"
export SOURCE_DATE_EPOCH="$(git log -1 --pretty=%ct)"
python -m build --wheel
python scripts/verify_wheel.py dist/semble-0.5.1+offline.2-py3-none-manylinux_2_34_x86_64.whl
python -m auditwheel show dist/semble-0.5.1+offline.2-py3-none-manylinux_2_34_x86_64.whl
```

`auditwheel` must report that the complete wheel is consistent with `manylinux_2_34_x86_64`; a filename alone is not sufficient evidence.

## macOS arm64 wheel

Run the native build on Apple Silicon macOS 11 or later. Install the exact maintainer tools, build the pinned grammar bundle, then point setuptools at it:

```bash
python -m pip install "build==1.5.0" "delocate==0.13.0" "GitPython==3.1.52" "anyio==4.14.2" "typing-extensions==4.16.0"
rustup toolchain install 1.91 --profile minimal
npm install --prefix /tmp/semble-tree-sitter-cli tree-sitter-cli@0.26.8
export PATH="/tmp/semble-tree-sitter-cli/node_modules/.bin:$PATH"
export MACOSX_DEPLOYMENT_TARGET=11.0
python scripts/build_grammar_bundle.py --platform macos-arm64 --output build/macos-arm64-bundle
export SEMBLE_OFFLINE_BUNDLE_DIR="$PWD/build/macos-arm64-bundle"
export SOURCE_DATE_EPOCH="$(git log -1 --pretty=%ct)"
python -m build --wheel
python scripts/verify_wheel.py dist/semble-0.5.1+offline.2-py3-none-macosx_11_0_arm64.whl
delocate-listdeps --all dist/semble-0.5.1+offline.2-py3-none-macosx_11_0_arm64.whl
delocate-wheel --require-archs arm64 --wheel-dir /tmp/semble-delocated dist/semble-0.5.1+offline.2-py3-none-macosx_11_0_arm64.whl
```

The verifier checks every Mach-O header and deployment target. The release workflow additionally rejects a delocated audit copy if it gains a `.dylibs` directory, ensuring the published wheel depends only on system libraries.

## Bundle builder behavior

`scripts/build_grammar_bundle.py` checks out `tree-sitter-language-pack` commit `6bb9761028dfc3a72329d15f0f339ec7ccb56159`, validates its repository, revision, library symbol, and license data against the checked-in 264-source manifest, applies the tracked C++ linker and exact-revision fetch patches, and compiles only the selected sources. `--grammar NAME` can be repeated for a targeted native rebuild; omitting it builds all 264 grammars. The output contains `grammars/`, a platform manifest, and a platform-adjusted `grammar-sources.json`.

The four corrected Linux C++ grammars were built with conda-forge GCC 11.4 and `sysroot_linux-64` 2.17, then had their build-only RPATH removed with patchelf 0.17.2. Any replacement must retain a compatibility floor no newer than the wheel tag, contain no ELF `DT_RPATH` or `DT_RUNPATH`, and pass `auditwheel` before its hashes are regenerated.

## Regenerating Linux asset metadata

`scripts/generate_asset_manifest.py` hashes the checked-in Linux payload and combines it with the pinned v1.6.2 language definitions and license cache:

```bash
python scripts/generate_asset_manifest.py --language-definitions /path/to/tree-sitter-language-pack/sources/language_definitions.json --license-cache /path/to/tree-sitter-language-pack/sources/license_cache.json
```

The generator requires exactly 264 `.so` libraries, rejects EBNF, and records the corrected-link provenance. Review both generated JSON files before committing them.

## Reproducibility and release

Build each wheel twice from the same staged bundle and `SOURCE_DATE_EPOCH`; the two wheel files must be byte-identical. Build sequentially because setuptools uses a shared local `build/` directory.

Pushing a tag that exactly matches `v` plus `semble.__version__`, currently `v0.5.1+offline.2`, calls the same reusable wheel workflow used by pull requests. It builds both platforms, verifies them, installs each artifact across Python 3.10 through 3.14, and runs full offline diagnostics. The final job writes one `SHA256SUMS`, creates a draft GitHub Release, uploads and downloads the assets for re-verification, then publishes the draft. A rerun may replace assets only while the release remains a draft; the workflow refuses to modify an already-published release.

The workflow does not build an sdist and does not publish to PyPI. Pushing tags or creating releases is a maintainer action and is never performed by the build scripts themselves.
