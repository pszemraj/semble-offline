# Asset provenance

Semble Offline `0.7.3+offline.1` is based on [MinishLab/semble](https://github.com/MinishLab/semble) tag `v0.7.3`, commit `a1ba6c18a4b0a58a3d1a15217d64bc92678d1d9d`. The installed package contains the following assets.

## Embedding model

The bundled model is an unmodified snapshot of [`minishlab/potion-code-16M-v2`](https://huggingface.co/minishlab/potion-code-16M-v2). Its model card and license are [included with the model](../src/semble/_bundled/model/README.md); the revision is recorded in the asset manifest below.

## Grammar sources

The `semble-grammars` dependency ships prebuilt grammars in a package archive. Version 0.1.2 supplies 77 canonical languages per supported platform. Requested libraries extract locally under `$XDG_CACHE_HOME/semble/grammars/<version>/<platform>/`, defaulting to `~/.cache/semble/grammars/<version>/<platform>/`, including on macOS. This directory must be writable. The dependency owns its parser archive, source metadata, and licenses.

This wheel adds CUDA and zsh from [`tree-sitter-language-pack` 1.6.2](https://github.com/kreuzberg-dev/tree-sitter-language-pack/releases/tag/v1.6.2), loaded directly from the installed package before the dependency's parsers.

CUDA covers `.cu` and `.cuh`. The dedicated zsh grammar overrides the dependency's `zsh` alias to Bash. Objective-C++ (`.mm`) uses the dependency's C++ grammar.

The Linux extras come from the published `parsers-linux-x86_64.tar.zst` archive. macOS builds the same pinned sources natively using the [bundle builder](rebuilding.md#bundle-builder-behavior). `tree-sitter-language-pack` is a build-time recipe, not a runtime dependency.

## Installed metadata

- [asset-manifest.json](../src/semble/_bundled/asset-manifest.json) records the platform, compatibility floor, build provenance, and SHA-256 digest of each bundled model and extra grammar file.
- [grammar-sources.json](../src/semble/_bundled/grammar-sources.json) declares the extra libraries, repositories, source revisions, and licenses. Build and verification tools derive the expected grammar set from it.
- [Third-party notices](../src/semble/_bundled/THIRD_PARTY_NOTICES.md) and the [language-pack license](../src/semble/_bundled/LICENSE.tree-sitter-language-pack) ship in the wheel.

[Runtime diagnostics](../README.md#install-and-verify) exercise the installed assets; the [wheel verifier](rebuilding.md#linux-wheel) checks their package layout and native compatibility before installation.
