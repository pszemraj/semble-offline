# Asset provenance

Semble Offline `0.7.3+offline.1` is based on [MinishLab/semble](https://github.com/MinishLab/semble) tag `v0.7.3`, commit `a1ba6c18a4b0a58a3d1a15217d64bc92678d1d9d`. It retains the offline model-loading distribution layer and adds two grammar libraries to upstream's `semble-grammars` parser source.

## Embedding model

The bundled model is an unmodified snapshot of [`minishlab/potion-code-16M-v2`](https://huggingface.co/minishlab/potion-code-16M-v2) at revision `e9d2a44ca6a05ac6685f3b23709ea57eb7352d5b`. The model card declares an MIT license and is included in the installed package.

## Grammar sources

The `semble-grammars` dependency ships prebuilt grammars in a package archive. Version 0.1.2 supplies 77 canonical languages per supported platform. It extracts requested libraries locally under `$XDG_CACHE_HOME/semble/grammars/<version>/` (default `~/.cache/semble/grammars/<version>/`, including on macOS), without network access. Its package owns the archive, source metadata, and licenses for those grammars; `semble doctor` reports the installed version and language count.

This distribution bundles only these extras, selected from [`tree-sitter-language-pack` 1.6.2](https://github.com/kreuzberg-dev/tree-sitter-language-pack/releases/tag/v1.6.2) at commit `6bb9761028dfc3a72329d15f0f339ec7ccb56159`:

| Extra | Source | Revision | License |
| --- | --- | --- | --- |
| CUDA | [tree-sitter-cuda](https://github.com/tree-sitter-grammars/tree-sitter-cuda) | `48b066f334f4cf2174e05a50218ce2ed98b6fd01` | MIT |
| zsh | [tree-sitter-zsh](https://github.com/georgeharker/tree-sitter-zsh) | `86b37f8d515a529722411bc7bf3c9e993a4743bf` | MIT |

Extras take precedence over dependency parsers. The CUDA grammar covers `.cu` and `.cuh`; the dedicated zsh grammar overrides the dependency's `zsh` alias to Bash. Objective-C++ (`.mm`) uses the dependency's C++ grammar.

The Linux extras are retained from the published `parsers-linux-x86_64.tar.zst` archive. The macOS bundle builds the same pinned sources natively for arm64 with tree-sitter CLI 0.26.8, Rust 1.91, and `MACOSX_DEPLOYMENT_TARGET=11.0`. The build helper uses the tracked language-pack C++ linker and pinned-revision fetch patches; their hashes are recorded in the platform manifest. Every macOS dylib receives the stable install name `@rpath/<filename>`.

`tree-sitter-language-pack` is a build-time recipe only; it is not a runtime dependency. The expected extra grammar set comes from `grammar-sources.json`, rather than a fixed library count.

## Installed metadata and verification

Each platform wheel includes:

- `asset-manifest.json`, containing its OS, architecture, compatibility floor, build provenance, and SHA-256 digest for every bundled model and extra grammar file
- `grammar-sources.json`, containing the extras' repositories, exact revisions, platform library filenames, and upstream-recorded SPDX identifiers
- `THIRD_PARTY_NOTICES.md` and the language-pack MIT license

`semble doctor --full` validates the bundled hashes, loads the embedding model, and loads every parser from both sources. Its direct `semble-grammars` checks expose extraction or loading errors rather than letting search silently degrade to line chunking.

`scripts/verify_wheel.py` checks the wheel's bundled assets, rejects mixed-platform contents, verifies ELF x86_64 or Mach-O arm64 headers, and rejects a macOS library whose deployment target is newer than 11.0 or whose install name is not canonical. With `--check-linux-policy`, it uses `auditwheel`'s ABI analysis to enforce the Linux compatibility floor. Native macOS verification with `delocate` is described in [Rebuilding and releases](rebuilding.md).
