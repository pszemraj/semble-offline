# Bundled third-party assets

This distribution contains assets that would otherwise be downloaded when Semble first runs. They are included to support firewalled and air-gapped Linux x86_64 environments.

## Embedding model

`model/` is an unmodified snapshot of [`minishlab/potion-code-16M-v2`](https://huggingface.co/minishlab/potion-code-16M-v2) at revision `e9d2a44ca6a05ac6685f3b23709ea57eb7352d5b`. Its model card declares the model MIT licensed and is included as `model/README.md`.

## Tree-sitter grammars

`grammars/` contains 264 shared libraries extracted from the Linux x86_64 parser archive published with [`tree-sitter-language-pack` 1.6.2](https://github.com/kreuzberg-dev/tree-sitter-language-pack/releases/tag/v1.6.2). The language pack is MIT licensed; its license is included as `LICENSE.tree-sitter-language-pack`.

Each grammar is built from a separate upstream repository. `grammar-sources.json` records the exact repository, revision, library filename, and SPDX identifier reported by the language pack's v1.6.2 source metadata. `asset-manifest.json` records a SHA-256 digest for every included binary.

The EBNF grammar from `RubixDev/ebnf` is deliberately excluded because the v1.6.2 language pack metadata identifies it as GPL-3.0. Semble handles `.ebnf` files with its line-based chunker instead.
