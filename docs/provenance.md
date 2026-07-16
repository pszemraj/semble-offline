# Asset provenance

Semble Offline `0.5.1+offline.1` is based on [MinishLab/semble](https://github.com/MinishLab/semble) commit `f4c397e2ede0c16ab1772adeee9a0af1024043bf`, which reports upstream version 0.5.1.

## Embedding model

The bundled model is an unmodified snapshot of [`minishlab/potion-code-16M-v2`](https://huggingface.co/minishlab/potion-code-16M-v2) at revision `e9d2a44ca6a05ac6685f3b23709ea57eb7352d5b`. The model card declares an MIT license and is included in the installed package.

## Grammar libraries

The grammar libraries come from the `parsers-linux-x86_64.tar.zst` asset published with [`tree-sitter-language-pack` 1.6.2](https://github.com/kreuzberg-dev/tree-sitter-language-pack/releases/tag/v1.6.2):

- Archive SHA-256: `5b5a4d2d5319b7d2fae6c7a87e8bf8618c6c827842dba7641a93693980e6b5ea`
- Archive size: 19,134,009 bytes
- Included libraries: 264
- Excluded library: `libtree_sitter_ebnf.so`, because the v1.6.2 source metadata identifies `RubixDev/ebnf` as GPL-3.0

The installed package includes:

- `asset-manifest.json`, containing platform data and the SHA-256 digest of every model and grammar file
- `grammar-sources.json`, containing the repository, exact revision, library filename, and upstream-recorded SPDX identifier for every included grammar
- `THIRD_PARTY_NOTICES.md` and the language-pack MIT license

`semble doctor --full` validates the checked-in hashes against installed bytes. `scripts/verify_wheel.py` performs the same check directly against a built wheel and also validates the platform tag and license files.

## Compatibility floor

The embedded grammar libraries themselves satisfy `manylinux_2_17_x86_64` according to `auditwheel`. The distribution is tagged `manylinux_2_34_x86_64` because its pinned `tree-sitter-language-pack` dependency publishes Linux x86_64 wheels with that floor. The higher tag accurately describes the installable package as a whole.
