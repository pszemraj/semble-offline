# Troubleshooting

Start with the [installation diagnostics](../README.md#install-and-verify). Fix the first failed check before debugging agent configuration.

## The wheel is not supported on this platform

Compare the wheel filename and your machine with the [supported platforms](../README.md#supported-platforms).

## A macOS source build asks for a grammar bundle

The checkout contains Linux grammar libraries. Install the matching macOS wheel, or prepare a native bundle as described in [Rebuilding and releases](rebuilding.md#macos-arm64-wheel).

## MCP dependencies are missing

Repeat the [wheel installation](../README.md#install-and-verify) with the `[mcp]` extra, adding `--upgrade --force-reinstall` if repairing an existing installation. Use the same platform wheel; an unqualified `python -m pip install semble` can replace this distribution with upstream Semble.

## An agent starts the wrong Semble

Check the generated Python command against the [interpreter configuration](installation.md#python-executable), then restart the agent. Remove stale entries pointing to another installation. Confirm the intended interpreter with:

```bash
python -m semble --version
```

## A bundled asset is missing or has the wrong hash

Reinstall from the matching release wheel and rerun diagnostics. For a published release, compare the wheel's checksum with its `SHA256SUMS` first. Runtime downloads do not repair missing assets. A missing grammar library is logged by the chunker, which can then use line chunking; a failed model load prevents indexing.

## A grammar falls back to line chunking

Run `semble doctor --full`. It directly loads dependency parsers and reports extraction errors hidden by search's fallback. Check that the [grammar cache](provenance.md#grammar-sources) is writable. CUDA and zsh have separate diagnostic entries. A language unavailable from both parser sources uses line chunking when its file extension is indexed.

## A custom model directory fails

Check `SEMBLE_MODEL_NAME` against the [offline model settings](../README.md#offline-behavior). Unset it to use the bundled model.

## Installation works but a remote repository search fails

A remote Git URL explicitly requests a clone and requires network access. Transfer or clone the repository first, then search its local path:

```bash
semble search "the behavior to find" /local/path/to/repository
```
