# Troubleshooting

Start with `python -m semble doctor --full`. It checks the supported platform, manifest, model files, all asset hashes, representative parser aliases, the embedding model, and the optional MCP dependencies.

## The wheel is not supported on this platform

The release wheel is intentionally tagged `manylinux_2_34_x86_64`. It requires Linux x86_64 and glibc 2.34 or later. macOS, Windows, ARM Linux, musl-based distributions, and older glibc systems are outside this project's scope.

## MCP dependencies are missing

Reinstall the same release wheel or tagged Git URL with the `[mcp]` extra. Avoid an unqualified install from PyPI because that can resolve upstream Semble instead of this fork.

## An agent starts the wrong Semble

Run `semble install` again from the environment containing Semble Offline. Current installer output uses that environment's absolute Python executable and `-m semble`. Remove stale entries containing a package runner or a different interpreter.

## A bundled asset is missing or has the wrong hash

Reinstall from a trusted release wheel and verify its checksum against the release's `SHA256SUMS`. Do not allow a missing asset to be repaired through a runtime download; fail-closed behavior is intentional.

## EBNF uses line chunking

This is expected. The EBNF grammar in the source language-pack release is GPL-3.0 and is not redistributed here. Other bundled languages use AST-aware chunking.

## A custom model or grammar directory fails

`SEMBLE_MODEL_NAME` must be a local model directory. `SEMBLE_TS_CACHE_DIR` must be a local directory containing `libtree_sitter_*.so` files compatible with `tree-sitter-language-pack` 1.6.2. These overrides do not accept remote URLs.

## Installation works but a remote repository search fails

The offline guarantee covers automatic model and grammar acquisition. Passing an HTTP, SSH, or other Git URL to `semble search` explicitly requests a clone and still requires network access. Clone or transfer the repository first, then search its local path.
