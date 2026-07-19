# Bundled third-party assets

This distribution contains assets that would otherwise be downloaded when Semble first runs. They are included to support firewalled and air-gapped Linux x86_64 and Apple Silicon macOS environments.

## Embedding model

`model/` is an unmodified snapshot of [`minishlab/potion-code-16M-v2`](https://huggingface.co/minishlab/potion-code-16M-v2) at revision `e9d2a44ca6a05ac6685f3b23709ea57eb7352d5b`. Its model card declares the model MIT licensed and is included as `model/README.md`.

## Tree-sitter grammars

`grammars/` contains 264 platform-specific shared libraries selected from [`tree-sitter-language-pack` 1.6.2](https://github.com/kreuzberg-dev/tree-sitter-language-pack/releases/tag/v1.6.2). The Linux wheel retains 260 binaries from the published Linux x86_64 parser archive and rebuilds the four C++ scanner grammars from the same pinned sources. The macOS wheel builds all 264 from those source revisions. The language pack is MIT licensed; its license is included as `LICENSE.tree-sitter-language-pack`.

Each grammar is built from a separate upstream repository. `grammar-sources.json` records the exact repository, revision, library filename, and SPDX identifier reported by the language pack's v1.6.2 source metadata. `asset-manifest.json` records a SHA-256 digest for every included binary.

The EBNF grammar from `RubixDev/ebnf` is deliberately excluded because the v1.6.2 language pack metadata identifies it as GPL-3.0. Semble handles `.ebnf` files with its line-based chunker instead.
