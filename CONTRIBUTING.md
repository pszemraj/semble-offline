# Contributing

Semble Offline is a narrow Linux x86_64 and Apple Silicon macOS distribution layer over upstream [MinishLab/semble](https://github.com/MinishLab/semble). Contributions should improve installation, offline reliability, asset provenance, platform wheel quality, or compatibility with a newer upstream release. General search features and additional platform support usually belong upstream.

Open an issue before starting a large change so the scope and upstream destination are clear. Small bug fixes and documentation corrections can go directly to a focused pull request.

## Development setup

Activate your development environment, then install the project and its development dependencies:

```bash
python -m pip install -e ".[dev,mcp]"
```

The project does not prescribe an environment manager. Development commands use the interpreter from the active environment.

## Checks

Run the complete local check set:

```bash
make check
```

The individual commands are:

```bash
python -m pytest
python -m ruff check src tests scripts setup.py
python -m ruff format --check src tests scripts setup.py
pydoclint src
python -m mypy src
```

Changes to bundled assets or packaging must also build and inspect the wheel:

```bash
python -m pip install build auditwheel
python -m build --wheel
python scripts/verify_wheel.py dist/semble-0.5.1+offline.2-py3-none-manylinux_2_34_x86_64.whl
python -m auditwheel show dist/semble-0.5.1+offline.2-py3-none-manylinux_2_34_x86_64.whl
```

## Pull requests

- Keep each change focused and explain whether it is fork-specific or suitable for upstream.
- Add tests for behavior changes and update user-facing documentation when commands or guarantees change.
- Do not add automatic runtime downloads. Explicit user requests such as searching a remote Git URL are a separate concern.
- Preserve the Linux x86_64/glibc 2.34 and Apple Silicon macOS 11 support statements unless fully built, tested, and distributable replacements are included.
- Do not commit generated wheels, archives, caches, or local environments.
- Do not publish packages, push tags, or create releases as part of an ordinary pull request.

When a change is broadly useful to upstream Semble, prefer a small standalone commit that can be shared or cherry-picked there.
