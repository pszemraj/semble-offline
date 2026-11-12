# Semble Offline

Semble Offline is a Linux x86_64 and Apple Silicon macOS distribution of [Semble](https://github.com/MinishLab/semble) for firewalled and air-gapped development environments. It bundles the embedding model and dedicated CUDA and zsh grammars. The `semble-grammars` dependency supplies the other prebuilt parsers without runtime downloads.

Use it when Python packages can come from an approved index but the installed agent cannot reach public model or release hosts. Once installed, searching a local repository makes no automatic network requests.

```bash
semble search "retry with exponential backoff" . --format text
```

**Supported platforms:** Linux x86_64 with glibc 2.34 or later, and Apple Silicon macOS 11 or later. Both support CPython 3.10 through 3.14. Intel macOS, Windows, Linux ARM, musl-based Linux, and older systems are intentionally out of scope.

## Install and verify

**The commands below target the planned `0.7.3+offline.1` release; those assets are not published by this change.** Until a maintainer publishes them, build and install a local wheel using [the rebuilding instructions](docs/rebuilding.md).

Activate the Python environment where Semble should run, then install the release wheel matching the machine.

Linux x86_64:

```bash
python -m pip install "semble[mcp] @ https://github.com/pszemraj/semble-offline/releases/download/v0.7.3%2Boffline.1/semble-0.7.3%2Boffline.1-py3-none-manylinux_2_34_x86_64.whl"
```

Apple Silicon macOS:

```bash
python -m pip install "semble[mcp] @ https://github.com/pszemraj/semble-offline/releases/download/v0.7.3%2Boffline.1/semble-0.7.3%2Boffline.1-py3-none-macosx_11_0_arm64.whl"
```

Linux can also build from a source checkout. macOS end-user installation is wheel-only because the source checkout intentionally contains the Linux grammar bundle; maintainers can prepare a local macOS bundle with the documented build helper.

Verify the platform, bundled model and extra grammar hashes, every parser from both sources, and MCP dependencies:

```bash
python -m semble doctor --full
```

The command should end with `All required checks passed.` Omit `[mcp]` only when the agent will call the CLI directly and does not need an MCP server.

The wheel resolves ordinary Python dependencies through the package index already configured for the environment. For a machine with no package-index access, follow the [offline transfer procedure](docs/offline-transfer.md).

## Paste this into your agent

Give an agent the following instructions when you want it to install and use Semble itself:

```text
Use the already-active Python environment. The following URLs target the planned 0.7.3+offline.1 release; use them only after the maintainer publishes it. Until then, use the locally built platform wheel. Install the release wheel matching this machine with exactly one of these commands:

Linux x86_64:
python -m pip install "semble[mcp] @ https://github.com/pszemraj/semble-offline/releases/download/v0.7.3%2Boffline.1/semble-0.7.3%2Boffline.1-py3-none-manylinux_2_34_x86_64.whl"

Apple Silicon macOS:
python -m pip install "semble[mcp] @ https://github.com/pszemraj/semble-offline/releases/download/v0.7.3%2Boffline.1/semble-0.7.3%2Boffline.1-py3-none-macosx_11_0_arm64.whl"

Do not use a Git-source installation on macOS.

Verify the installation before using it:

python -m semble doctor --full

If diagnostics pass, use Semble for code discovery in this repository:

- `semble search "<one focused description of the code or behavior>" . --format text`
- Pass several local paths to search related repositories together.
- `semble file-types` lists indexed extensions; `semble clear orphans` removes indexes for deleted repositories.
- `semble find-related <file_path> <line> .` after finding one relevant implementation.
- Add `--content docs`, `--content config`, or `--content all` when the target is not source code.
- Use one concept per search query.
- Use exact-text search instead when you need every occurrence of a known symbol or string.
- Search local paths in restricted environments; a remote Git URL explicitly requests network access.
- Do not replace this installation with an unqualified `pip install semble`.
```

If the `semble` executable is not on `PATH`, use `python -m semble` with the same arguments.

## Configure a coding agent

To detect installed agents and choose integrations interactively:

```bash
semble install
```

For unattended setup, name the agent and integrations explicitly:

```bash
semble install --agent codex --type mcp instructions --yes
```

Replace `codex` with an agent ID shown by `semble install --help`. The installer preserves unrelated configuration and writes MCP entries using the absolute Python executable from the active environment. If that environment moves, run the installer again.

Remove configuration created by Semble with:

```bash
semble uninstall --agent codex --type all --yes
```

## Search a repository

Searches build an index on first use. Later searches reuse unchanged files and reindex only added or edited files, removing deleted files from the index:

```bash
semble search "retry with exponential backoff" /path/to/repository --format text
semble find-related src/retry.py 42 /path/to/repository
semble search "deployment configuration" /path/to/repository --content config
semble search "invoice endpoint" ./service-a ../service-b --format text
semble file-types
semble clear orphans
```

`--format text` produces readable snippets; JSON is the default. Multiple search paths share one ranked result set, with repository prefixes on result paths. `file-types` lists indexed extensions, and `clear orphans` removes cached indexes whose source paths no longer exist.

`python -m semble` can be used anywhere the `semble` executable is not on `PATH`.

Use Semble to discover relevant code by behavior. Use an exact-text tool when you already know the symbol, filename, or error message and need exhaustive matches.

## Offline behavior

- The `minishlab/potion-code-16M-v2` embedding model is bundled and required by default.
- `semble-grammars` supplies prebuilt grammars in its installed archive and extracts them locally on first use. Its version and language count appear in `semble doctor`.
- This wheel adds only `cuda` and `zsh`, loading them before the dependency's parsers. `.cu` and `.cuh` use CUDA; `.zsh` uses the dedicated zsh grammar; `.mm` uses C++.
- Dependency grammars need a writable `$XDG_CACHE_HOME/semble/grammars/<version>/` directory (default `~/.cache/semble/grammars/<version>/`, including on macOS).
- Missing bundled assets raise an error. `doctor` directly exercises dependency extraction/loading so a broken grammar cache is reported before search can fall back to line chunking.
- `SEMBLE_MODEL_NAME` may point to a different local model directory.
- Supplying a remote Git URL to `semble search` is an explicit request to clone that repository and therefore requires network access. Searching local paths does not.

See [provenance](docs/provenance.md) for exact revisions, hashes, licenses, and the upstream base.

## Project status

This repository addresses the offline installation use case described in [MinishLab/semble#224](https://github.com/MinishLab/semble/issues/224). The distribution and import package are both named `semble`, replacing upstream in the selected environment. Version `0.7.3+offline.1` is based on upstream tag `v0.7.3`, commit `a1ba6c18a4b0a58a3d1a15217d64bc92678d1d9d`.

PyPI publication is not part of this repository change. GitHub Releases are the binary distribution channel; direct source installation is supported on Linux; macOS requires a prepared native bundle.

Useful references:

- [Install and configure an agent](docs/installation.md)
- [Offline transfer](docs/offline-transfer.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Asset provenance](docs/provenance.md)
- [Rebuilding and releases](docs/rebuilding.md)
- [Contributing](CONTRIBUTING.md)

Semble itself is MIT licensed. The upstream authors and citation information are preserved in [CITATION.cff](CITATION.cff); bundled third-party asset notices ship inside the wheel.
