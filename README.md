# Semble Offline

Semble Offline provides local code search for firewalled and air-gapped Linux x86_64 and Apple Silicon macOS systems. It packages [Semble](https://github.com/MinishLab/semble) with an embedding model and dedicated CUDA and zsh grammars; `semble-grammars` supplies the other prebuilt parsers.

Use it when Python packages can come from an approved index but the installed agent cannot reach public model or release hosts. Once installed, searching a local repository makes no automatic network requests.

```bash
semble search "retry with exponential backoff" . --format text
```

## Supported platforms

Linux x86_64 with glibc 2.34 or later and Apple Silicon macOS 11 or later, using CPython 3.10 through 3.14. Intel macOS, Windows, Linux ARM, and musl-based Linux are unsupported.

## Install and verify

The commands target the planned `0.7.3+offline.1` release. Until it is published, build a [Linux wheel](docs/rebuilding.md#linux-wheel) or [macOS wheel with a native grammar bundle](docs/rebuilding.md#macos-arm64-wheel).

Run the following steps yourself, or paste the block into your coding agent:

```text
Use the already-active Python environment. Install exactly one wheel matching this machine, after the maintainer publishes the release:

Linux x86_64:
python -m pip install "semble[mcp] @ https://github.com/pszemraj/semble-offline/releases/download/v0.7.3%2Boffline.1/semble-0.7.3%2Boffline.1-py3-none-manylinux_2_34_x86_64.whl"

Apple Silicon macOS:
python -m pip install "semble[mcp] @ https://github.com/pszemraj/semble-offline/releases/download/v0.7.3%2Boffline.1/semble-0.7.3%2Boffline.1-py3-none-macosx_11_0_arm64.whl"

Before publication, use a locally built platform wheel instead.

Verify the installation:
python -m semble doctor --full
Require "All required checks passed." before searching.

Search this repository with one focused description per query:
semble search "<code or behavior to find>" . --format text

Read the returned file and line. To find similar code, use:
semble find-related <file_path> <line> .

Use exact-text search for exhaustive matches of known symbols or strings.
Search local paths in restricted environments; remote Git URLs require networking.
Keep this installation; an unqualified `pip install semble` can replace it with upstream.
```

Doctor checks the platform, bundled hashes, parser loading, and model. It reports missing MCP dependencies as optional. Omit `[mcp]` from installation only for CLI-only use. Dependencies come from the configured package index; for a disconnected machine, use the [offline transfer procedure](docs/offline-transfer.md).

If the `semble` executable is not on `PATH`, use `python -m semble` with the same arguments. [Agent setup](docs/installation.md) covers MCP configuration, installed instructions, and removal.

## Search a repository

Searches build an index on first use. Later searches reuse unchanged files and reindex only added or edited files, removing deleted files from the index:

```bash
semble search "deployment configuration" /path/to/repository --content config
semble search "invoice endpoint" ./service-a ../service-b --format text
semble file-types
semble clear orphans
```

`--content` selects `code` (the default), `docs`, `config`, or `all`. `--format text` produces readable snippets; JSON is the default. Multiple search paths share one ranked result set, with repository prefixes on result paths and a `repos` map in JSON output; pass the same paths to `find-related`.

`file-types` lists indexed extensions. `clear orphans` removes cached indexes whose source paths no longer exist.

## Offline behavior

Local indexing and querying use installed assets. The default model is bundled; `SEMBLE_MODEL_NAME` can select another local model directory. Dependency parsers extract locally on first use, while the two extra grammars load directly from the package. See [asset provenance](docs/provenance.md) for source pins, grammar precedence, file mappings, and cache locations, or [troubleshooting](docs/troubleshooting.md) for failed diagnostics.

## Project status

This repository addresses the offline installation use case described in [MinishLab/semble#224](https://github.com/MinishLab/semble/issues/224). The distribution and import package are both named `semble`, replacing upstream in the selected environment. The [upstream base and bundled assets](docs/provenance.md) record the revisions used for this distribution.

GitHub Releases distribute the platform wheels; this repository does not publish packages to PyPI.

Useful references:

- [Install and configure an agent](docs/installation.md)
- [Offline transfer](docs/offline-transfer.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Asset provenance](docs/provenance.md)
- [Rebuilding and releases](docs/rebuilding.md)
- [Contributing](CONTRIBUTING.md)

Semble itself is MIT licensed. The upstream authors and citation information are preserved in [CITATION.cff](CITATION.cff); bundled third-party asset notices ship inside the wheel.
