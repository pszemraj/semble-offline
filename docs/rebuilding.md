# Rebuilding and releases

The source checkout contains the Linux model and extra grammar bundle. The macOS wheel requires a native bundle built from the same CUDA and zsh source pins. `semble-grammars` remains an ordinary Python dependency; its prebuilt parser archive is not copied into this wheel.

Version `0.7.3+offline.1` is prepared on the integration branch. The release URLs in the user documentation become usable only after the maintainer publishes that release. Building and testing locally does not publish anything.

## Linux wheel

On Linux x86_64, activate a development environment and run:

```bash
python -m pip install -e ".[dev,mcp]"
python -m pip install "build==1.5.0" "auditwheel==6.7.0"
export SOURCE_DATE_EPOCH="$(git log -1 --pretty=%ct)"
python -m build --wheel
python scripts/verify_wheel.py --check-linux-policy dist/semble-0.7.3+offline.1-py3-none-manylinux_2_34_x86_64.whl
```

The verifier uses `auditwheel`'s policy analysis to require compatibility with `manylinux_2_34_x86_64` or an older, wider-compatible policy; a filename alone is not sufficient evidence.

## macOS arm64 wheel

These native commands must be run on the Apple Silicon laptop; Linux validation cannot establish native macOS loading or performance. Run on macOS 11 or later with the compiler tools available. Install the maintainer tools, build the pinned extra grammars, then point setuptools at that bundle:

```bash
python -m pip install "build==1.5.0" "delocate==0.13.0" "GitPython==3.1.52" "anyio==4.14.2" "typing-extensions==4.16.0"
rustup toolchain install 1.91 --profile minimal
npm install --prefix /tmp/semble-tree-sitter-cli tree-sitter-cli@0.26.8
export PATH="/tmp/semble-tree-sitter-cli/node_modules/.bin:$PATH"
export MACOSX_DEPLOYMENT_TARGET=11.0
python scripts/build_grammar_bundle.py --platform macos-arm64 --grammar cuda --grammar zsh --output build/macos-arm64-bundle
export SEMBLE_OFFLINE_BUNDLE_DIR="$PWD/build/macos-arm64-bundle"
export SOURCE_DATE_EPOCH="$(git log -1 --pretty=%ct)"
python -m build --wheel
python scripts/verify_wheel.py dist/semble-0.7.3+offline.1-py3-none-macosx_11_0_arm64.whl
delocate-listdeps --all dist/semble-0.7.3+offline.1-py3-none-macosx_11_0_arm64.whl
delocate-wheel --require-archs arm64 --wheel-dir /tmp/semble-delocated dist/semble-0.7.3+offline.1-py3-none-macosx_11_0_arm64.whl
```

The verifier checks every Mach-O header, deployment target, and canonical `@rpath/<filename>` install name. Inspect the delocated audit copy: it should not gain a `.dylibs` directory, and dependencies should be system libraries only.

### Native macOS validation handoff

Install the built wheel into a fresh environment while connected, including test dependencies. Keep the source checkout available for tests, but verify that imports resolve to the installed wheel:

```bash
python -m venv /tmp/semble-macos-check
/tmp/semble-macos-check/bin/python -m pip install "${PWD}/dist/semble-0.7.3+offline.1-py3-none-macosx_11_0_arm64.whl[dev,mcp]"
/tmp/semble-macos-check/bin/python -c 'import pathlib, semble; print(pathlib.Path(semble.__file__).resolve())'
/tmp/semble-macos-check/bin/python -m pytest
```

Run lint, formatting, docstring and type checks from the development environment with `make lint typecheck`. Record the macOS and Python versions, the `delocate` output, and test results in the PR. Generated reports and wheel files stay outside Git.

For the offline check, disconnect networking after installing dependencies, start with empty caches, and run:

```bash
export XDG_CACHE_HOME="$(mktemp -d)"
export SEMBLE_CACHE_LOCATION="$(mktemp -d)"
export HF_HOME="$(mktemp -d)"
export HF_HUB_OFFLINE=1
/tmp/semble-macos-check/bin/python -m semble doctor --full
```

Require a passing model check, separate CUDA and zsh checks, the installed `semble-grammars` version and language count, and every parser loading from both sources. The empty-cache run must successfully extract dependency grammars under `$XDG_CACHE_HOME/semble/grammars/<version>/`, even though macOS search indexes otherwise default to `~/Library/Caches/semble/`.

While disconnected, search a local fixture repository containing `.py`, `.cu`, `.cuh`, and `.zsh` files and require no `falling back to line chunking` warning. On a local FAISS checkout, confirm that CUDA headers enter the index and CUDA chunks start at block boundaries:

```python
from pathlib import Path
import semble
from semble import SembleIndex

index = SembleIndex.from_path("/path/to/faiss")
headers = {chunk.file_path for chunk in index.chunks if chunk.file_path.endswith(".cuh")}
cuda_chunks = [chunk for chunk in index.chunks if chunk.file_path.endswith(".cu")]
indented = [chunk for chunk in cuda_chunks if chunk.content.startswith((" ", "\t"))]
print("indexed CUDA headers:", len(headers))
print("CUDA chunks starting on whitespace:", len(indented), "of", len(cuda_chunks))
print("package MiB:", sum(p.stat().st_size for p in Path(semble.__file__).parent.rglob("*") if p.is_file()) / 2**20)
```

For the referenced FAISS snapshot, the expected header count is 66 and the indented CUDA chunk count is zero; record the actual checkout revision when comparing. The installed `semble/` directory should be roughly 45 MB, rather than the previous roughly 399 MB. This excludes the separate `semble_grammars/` dependency and extracted cache.

Measure three CLI invocations using the same local FAISS checkout and query: first search with an empty index cache, an unchanged warm search, and a search after appending a comment to one source file in a disposable checkout. Use `/usr/bin/time -p /tmp/semble-macos-check/bin/python -m semble search "GPU distance calculation" /path/to/faiss --format text` for each. Compare ratios: the one-file update should be close to the warm search and substantially faster than cold indexing. The 2-vCPU reference was 6.1 s cold, 0.65 s warm, and 0.70 s after one edit; these are comparison ratios, not Mac latency targets.

## Bundle builder behavior

`scripts/build_grammar_bundle.py` checks out `tree-sitter-language-pack` commit `6bb9761028dfc3a72329d15f0f339ec7ccb56159`, checks source metadata against `grammar-sources.json`, applies the tracked C++ linker and exact-revision fetch patches, and compiles only the selected sources. `--grammar NAME` can be repeated; omitting it builds all extras declared in the manifest. The current extras are CUDA and zsh. Output contains `grammars/`, a platform manifest, and a platform-adjusted `grammar-sources.json`.

Adding an extra means declaring its source in `grammar-sources.json` and supplying its platform library. Bundle-size checks derive the expected set from that source manifest.

## Regenerating Linux asset metadata

After intentionally changing the declared Linux extras or their libraries, regenerate the existing asset metadata:

```bash
python scripts/generate_asset_manifest.py
```

The generator reads the declared source set, requires matching `.so` files, and hashes the model and extra libraries into `asset-manifest.json`. Review source pins and asset metadata with the payload change. Keep build outputs and validation reports untracked.

## Reproducibility and release

Existing release tooling builds clean source snapshots with the same staged bundle and `SOURCE_DATE_EPOCH`, checks platform wheels, and prepares GitHub Release assets. It does not publish an sdist or upload to PyPI. Tags, releases, and publication remain separate maintainer actions after review; this integration does not perform them or add CI checks.
