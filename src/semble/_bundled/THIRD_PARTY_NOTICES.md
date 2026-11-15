# Bundled third-party assets

## Embedding model

`model/` contains [`minishlab/potion-code-16M-v2`](https://huggingface.co/minishlab/potion-code-16M-v2), licensed under MIT. Its [model card](model/README.md) is included unchanged. The revision and file hashes are recorded in [asset-manifest.json](asset-manifest.json).

## Extra tree-sitter grammars

`grammars/` contains CUDA and zsh libraries from [`tree-sitter-language-pack` 1.6.2](https://github.com/kreuzberg-dev/tree-sitter-language-pack/releases/tag/v1.6.2). The language pack's [MIT license](LICENSE.tree-sitter-language-pack) is included.

The grammar sources are [tree-sitter-cuda](https://github.com/tree-sitter-grammars/tree-sitter-cuda) and [tree-sitter-zsh](https://github.com/georgeharker/tree-sitter-zsh), both MIT licensed. [grammar-sources.json](grammar-sources.json) records their revisions and library filenames.

Other parsers come from the separate `semble-grammars` dependency, which includes its own third-party notices.
