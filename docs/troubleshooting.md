# Troubleshooting

Start with:

```bash
python -m semble --version
python -m semble doctor --full
```

The full check validates the platform, manifest, model files, every asset hash, representative parser aliases, the embedding model, and the optional MCP dependencies. Fix the first failed check before debugging agent configuration.

## The wheel is not supported on this platform

The release wheel is intentionally tagged `manylinux_2_34_x86_64`. It requires Linux x86_64 and glibc 2.34 or later. macOS, Windows, ARM Linux, musl-based distributions, and older glibc systems are outside this project's scope.

## MCP dependencies are missing

Reinstall the tagged version with the `[mcp]` extra:

```bash
python -m pip install --upgrade --force-reinstall "semble[mcp] @ git+https://github.com/pszemraj/semble-offline.git@v0.5.1+offline.1"
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

Reinstall from the release wheel, verify its checksum against the release's `SHA256SUMS`, then rerun full diagnostics. Missing assets are not repaired through runtime downloads; fail-closed behavior is intentional.

## EBNF uses line chunking

This is expected. The EBNF grammar in the source language-pack release is GPL-3.0 and is not redistributed here. Other bundled languages use AST-aware chunking.

## A custom model or grammar directory fails

`SEMBLE_MODEL_NAME` must be a local model directory. `SEMBLE_TS_CACHE_DIR` must be a local directory containing `libtree_sitter_*.so` files compatible with `tree-sitter-language-pack` 1.6.2. These overrides do not accept remote URLs.

## Installation works but a remote repository search fails

The offline guarantee covers automatic model and grammar acquisition. A remote Git URL explicitly requests a clone and still requires network access. Clone or transfer the repository first, then search its local path:

```bash
semble search "the behavior to find" /local/path/to/repository
```
