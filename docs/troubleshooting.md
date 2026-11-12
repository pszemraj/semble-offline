# Troubleshooting

Start with:

```bash
python -m semble --version
python -m semble doctor --full
```

The full check validates the platform, manifest, model files, every asset hash, every extra and dependency grammar parser, the embedding model, and the optional MCP dependencies. Fix the first failed check before debugging agent configuration.

## The wheel is not supported on this platform

Use `manylinux_2_34_x86_64` on Linux x86_64 with glibc 2.34 or later. Use `macosx_11_0_arm64` on Apple Silicon macOS 11 or later. Intel macOS, Windows, Linux ARM, musl-based Linux, and older operating systems are outside this release's scope.

## A macOS Git-source build asks for a grammar bundle

This is intentional. The checkout contains the Linux grammar bundle, so the supported macOS end-user installation is the release wheel. Maintainers rebuilding locally must first run `scripts/build_grammar_bundle.py --platform macos-arm64` and set `SEMBLE_OFFLINE_BUNDLE_DIR` as documented in [Rebuilding and releases](rebuilding.md).

The release URLs below target the planned `0.7.3+offline.1` release; use a locally built wheel until those assets are published.

## MCP dependencies are missing

Reinstall the matching release wheel with the `[mcp]` extra. For example, on Apple Silicon macOS:

```bash
python -m pip install --upgrade --force-reinstall "semble[mcp] @ https://github.com/pszemraj/semble-offline/releases/download/v0.7.3%2Boffline.1/semble-0.7.3%2Boffline.1-py3-none-macosx_11_0_arm64.whl"
python -m semble doctor --full
```

Do not use an unqualified install from PyPI because it can resolve upstream Semble instead of this distribution.

## An agent starts the wrong Semble

Activate the environment containing Semble Offline, verify it, and rewrite the agent entry:

```bash
python -m semble --version
semble install
```

The installer uses that environment's absolute Python executable and `-m semble`. Restart the agent after updating its configuration. Remove stale entries that point to a different interpreter.

## A bundled asset is missing or has the wrong hash

Reinstall from the matching release wheel, verify its checksum against the release's `SHA256SUMS`, then rerun full diagnostics. Missing assets are not repaired through runtime downloads; fail-closed behavior is intentional.

## A dependency grammar falls back to line chunking

Run `semble doctor --full`. It loads `semble-grammars` directly and reports extraction/loading failures that search would otherwise catch and handle with line chunking. The installed dependency contains its own parser archive, so no network access is needed. Ensure `$XDG_CACHE_HOME/semble/grammars/<version>/` is writable (or `~/.cache/semble/grammars/<version>/` when unset). This grammar cache location applies on macOS too.

CUDA and zsh come from this wheel and take precedence. Check their individual diagnostic entries if `.cu`, `.cuh`, or `.zsh` files fall back. Languages absent from both sources use line chunking when their extensions are included for indexing.

## A custom model directory fails

`SEMBLE_MODEL_NAME` must point to a local model directory. It does not accept a remote model ID or URL. Unset it to return to the model bundled with Semble Offline.

## Installation works but a remote repository search fails

The offline guarantee covers automatic model and grammar acquisition. A remote Git URL explicitly requests a clone and still requires network access. Clone or transfer the repository first, then search its local path:

```bash
semble search "the behavior to find" /local/path/to/repository
```
