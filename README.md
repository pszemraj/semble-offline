# Semble Offline

Semble Offline is a Linux x86_64 distribution of [Semble](https://github.com/MinishLab/semble) for firewalled and air-gapped development environments. It bundles the embedding model and tree-sitter grammar binaries that upstream Semble normally obtains from Hugging Face and GitHub at runtime.

Use it when your Python environment can install dependencies from an approved package index, but the running process cannot reach public model or release hosts. Once installed, local repository indexing and search make no automatic network requests.

This repository tracks the problem described in [MinishLab/semble#224](https://github.com/MinishLab/semble/issues/224) and is intended as a focused stopgap until upstream provides an equivalent distribution.

## Requirements

- Linux x86_64 with glibc 2.34 or later
- CPython 3.10 through 3.14
- About 58 MB for the wheel and about 430 MB for the installed Semble payload, before ordinary Python dependencies
- Access to your approved Python package index during installation, or a directory containing pre-downloaded dependency wheels

Other operating systems and architectures are intentionally unsupported. The wheel has a platform tag so installers reject incompatible targets up front.

## Install

Activate the environment where Semble should run. The GitHub Release wheel is the preferred reproducible install:

```bash
python -m pip install "semble[mcp] @ https://github.com/pszemraj/semble-offline/releases/download/v0.5.1%2Boffline.1/semble-0.5.1%2Boffline.1-py3-none-manylinux_2_34_x86_64.whl"
```

Install directly from the tagged Git source when a wheel URL is not convenient:

```bash
python -m pip install "semble[mcp] @ git+https://github.com/pszemraj/semble-offline.git@v0.5.1+offline.1"
```

Omit `[mcp]` if you only need the CLI and Python API. Both commands still resolve Semble's ordinary dependencies through the package index configured for your environment; this fork removes runtime asset downloads, not normal package installation.

Verify the installation and every bundled asset without network access:

```bash
python -m semble doctor --full
```

For a fully disconnected target, see [offline transfer](docs/offline-transfer.md).

## Use

The search CLI and Python API remain compatible with upstream Semble 0.5.1:

```bash
semble search "retry with exponential backoff" /path/to/repository
semble find-related src/retry.py 42 /path/to/repository
semble search "deployment configuration" /path/to/repository --content config
```

`python -m semble` can be used anywhere the `semble` executable is not on `PATH`.

To configure supported coding agents, run:

```bash
semble install
```

The installer writes MCP entries that use the absolute Python interpreter from the active installation. It never launches a package runner or resolves a different copy of Semble from PyPI. Run `semble uninstall` to remove those entries.

## Offline behavior

- The `minishlab/potion-code-16M-v2` embedding model is bundled and required by default.
- 264 tree-sitter grammar libraries from `tree-sitter-language-pack` 1.6.2 are bundled and loaded from the package.
- The GPL-3.0 EBNF grammar is deliberately excluded; `.ebnf` files use Semble's line chunker.
- Missing or corrupt bundled assets produce a clear error instead of silently falling through to a network download.
- `SEMBLE_MODEL_NAME` may point to a different local model directory, and `SEMBLE_TS_CACHE_DIR` may point to a different local grammar directory.
- Supplying a remote Git URL to `semble search` is an explicit request to clone that repository and therefore requires network access. Searching local paths does not.

See [provenance](docs/provenance.md) for exact revisions, hashes, licenses, and the upstream base.

## Project status

The installed distribution and import package are both named `semble`; this is intentional replacement behavior for constrained environments. Version `0.5.1+offline.1` is based on upstream commit `f4c397e2ede0c16ab1772adeee9a0af1024043bf`.

PyPI publication is not part of this repository change. GitHub Releases are the binary distribution channel, while a tagged Git URL remains available for source installation.

Useful references:

- [Installation and agent setup](docs/installation.md)
- [Offline transfer](docs/offline-transfer.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Asset provenance](docs/provenance.md)
- [Rebuilding and releases](docs/rebuilding.md)
- [Contributing](CONTRIBUTING.md)

Semble itself is MIT licensed. The upstream authors and citation information are preserved in [CITATION.cff](CITATION.cff); bundled third-party asset notices ship inside the wheel.
