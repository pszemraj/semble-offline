# Contributing

Semble Offline is a Linux x86_64 and Apple Silicon macOS distribution layer over upstream [Semble](https://github.com/MinishLab/semble). Contributions should improve installation, offline reliability, asset provenance, platform wheels, or compatibility with a newer upstream release. General search features and additional platform support usually belong upstream.

Open an issue before starting a large change so the scope and upstream destination are clear. Small fixes can go directly to a focused pull request.

## Development setup

Activate a development environment and install the project and development dependencies:

```bash
python -m pip install -e ".[dev,mcp]"
```

On macOS, prepare the [native grammar bundle](docs/rebuilding.md#macos-arm64-wheel) before installing from source.

## Checks

Run tests, lint, formatting, docstring checks, and type checks locally:

```bash
make check
```

Use `make help` to list individual targets. Changes to bundled assets or packaging also need a [wheel build and verification](docs/rebuilding.md). Keep generated wheels, archives, caches, and validation reports outside Git.

## Pull requests

- Explain whether the change belongs in this distribution or could be shared upstream.
- Test behavior changes and update the affected user instructions.
- Preserve the [offline behavior](README.md#offline-behavior) and [supported platforms](README.md#supported-platforms).
- Leave tags, releases, and publication to the maintainer after review.

When a change is useful upstream, prefer a small standalone commit that can be shared or cherry-picked there.
