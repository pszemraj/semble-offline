# Rebuilding and releases

Builds are supported only on Linux x86_64. Activate a development environment, install the project and build tools, then build the wheel:

```bash
python -m pip install -e ".[dev,mcp]"
python -m pip install build auditwheel
SOURCE_DATE_EPOCH="$(git log -1 --pretty=%ct)" python -m build --wheel
```

Verify the result before distributing it:

```bash
python scripts/verify_wheel.py dist/semble-0.5.1+offline.1-py3-none-manylinux_2_34_x86_64.whl
python -m auditwheel show dist/semble-0.5.1+offline.1-py3-none-manylinux_2_34_x86_64.whl
python -m semble doctor --full
```

Two builds from the same commit and `SOURCE_DATE_EPOCH` must be byte-identical. Build them sequentially because setuptools uses a shared local `build/` directory.

## Regenerating asset metadata

`scripts/generate_asset_manifest.py` hashes the checked-in payload and combines it with the pinned v1.6.2 language definitions and license cache. Download these two source files from the exact `tree-sitter-language-pack` tag, then run:

```bash
python scripts/generate_asset_manifest.py --language-definitions /path/to/language_definitions.json --license-cache /path/to/license_cache.json
```

The generator requires exactly 264 grammar libraries and rejects a bundle containing EBNF. Review changes to both generated JSON files before committing them.

## GitHub Release

Pushing a tag that exactly matches `v` plus `semble.__version__`, currently `v0.5.1+offline.1`, starts the release workflow. It runs the source tests, builds the wheel twice with a fixed timestamp, compares the bytes, validates contents and ELF compatibility, installs the wheel in a fresh environment, runs full diagnostics with invalid proxies, writes `SHA256SUMS`, and creates or updates the GitHub Release.

The workflow does not build an sdist and does not publish to PyPI. Pushing tags or creating releases is a maintainer action and is never performed by the build scripts themselves.
