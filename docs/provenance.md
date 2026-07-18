# Asset provenance

Semble Offline `0.5.1+offline.2` is based on [MinishLab/semble](https://github.com/MinishLab/semble) commit `f4c397e2ede0c16ab1772adeee9a0af1024043bf`, which reports upstream version 0.5.1. No newer upstream Semble changes are included.

## Embedding model

The bundled model is an unmodified snapshot of [`minishlab/potion-code-16M-v2`](https://huggingface.co/minishlab/potion-code-16M-v2) at revision `e9d2a44ca6a05ac6685f3b23709ea57eb7352d5b`. The model card declares an MIT license and is included in the installed package.

## Grammar libraries

Both wheels contain the same 264 grammar sources selected from [`tree-sitter-language-pack` 1.6.2](https://github.com/kreuzberg-dev/tree-sitter-language-pack/releases/tag/v1.6.2) at commit `6bb9761028dfc3a72329d15f0f339ec7ccb56159`. `grammar-sources.json` records the separate upstream repository and exact revision for every grammar.

The Linux bundle retains 260 libraries from the published `parsers-linux-x86_64.tar.zst` archive and rebuilds `mojo`, `nim`, `norg`, and `wolfram` from the same pinned sources. Those four grammars contain C++ scanners and required a corrected final link through the C++ runtime. They were built with conda-forge GCC 11.4 and a Linux 2.17 sysroot; the complete wheel is verified by `auditwheel` as `manylinux_2_34_x86_64`.

The macOS bundle builds all 264 libraries from those pinned sources on the native arm64 runner. Generation uses tree-sitter CLI 0.26.8 with ABI 14, Rust 1.91, and `MACOSX_DEPLOYMENT_TARGET=11.0`. One tracked patch changes only the language-pack link command for the four C++ scanner grammars. A second makes the language-pack vendor helper explicitly fetch a pinned revision when it is not reachable from a repository's advertised refs. Neither patch alters parser sources or Semble upstream code, and both hashes are recorded in the platform manifest.

The EBNF grammar is deliberately excluded because the v1.6.2 source metadata identifies `RubixDev/ebnf` as GPL-3.0. `.ebnf` files use Semble's line chunker.

## Installed metadata and verification

Each platform wheel includes:

- `asset-manifest.json`, containing its OS, architecture, compatibility floor, build provenance, and SHA-256 digest for every model and grammar file
- `grammar-sources.json`, containing each grammar's repository, exact revision, platform library filename, and upstream-recorded SPDX identifier
- `THIRD_PARTY_NOTICES.md` and the language-pack MIT license

`semble doctor --full` validates all installed hashes and loads all 264 parsers. `scripts/verify_wheel.py` performs the same integrity checks directly against a wheel, rejects mixed-platform contents, verifies ELF x86_64 or Mach-O arm64 headers, and rejects a macOS library whose deployment target is newer than 11.0. CI additionally uses `auditwheel` for Linux and `delocate` for macOS dynamic dependencies and architectures.
