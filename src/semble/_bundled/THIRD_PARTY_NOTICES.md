# Bundled third-party assets

This distribution includes an embedding model and dedicated CUDA and zsh grammars for firewalled and air-gapped Linux x86_64 and Apple Silicon macOS environments.

## Embedding model

`model/` is an unmodified snapshot of [`minishlab/potion-code-16M-v2`](https://huggingface.co/minishlab/potion-code-16M-v2) at revision `e9d2a44ca6a05ac6685f3b23709ea57eb7352d5b`. Its model card declares the model MIT licensed and is included as `model/README.md`.

## Extra tree-sitter grammars

`grammars/` contains only CUDA and zsh libraries selected from [`tree-sitter-language-pack` 1.6.2](https://github.com/kreuzberg-dev/tree-sitter-language-pack/releases/tag/v1.6.2). The Linux wheel retains these binaries from the published Linux x86_64 parser archive. The macOS wheel builds the same pinned source revisions natively. The language pack is MIT licensed; its license is included as `LICENSE.tree-sitter-language-pack`.

Each grammar has its own source repository and MIT license: [tree-sitter-cuda](https://github.com/tree-sitter-grammars/tree-sitter-cuda) and [tree-sitter-zsh](https://github.com/georgeharker/tree-sitter-zsh). `grammar-sources.json` records the exact repositories, revisions, library filenames, and SPDX identifiers reported by the language pack's v1.6.2 source metadata. `asset-manifest.json` records a SHA-256 digest for every included binary.

Other parsers come from the separate `semble-grammars` dependency, which contains its own prebuilt archives and third-party notices. It extracts them locally without downloading grammars at runtime. The language-pack Python package is not required at runtime.
