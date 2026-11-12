# Offline transfer

The release wheel contains Semble's model and CUDA/zsh extras. The `semble-grammars` dependency contains the other parser archives; it must be transferred along with ordinary Python dependencies. A fully disconnected target needs the release wheel and compatible wheels for all dependencies.

The URLs below target the planned `0.7.3+offline.1` release and require the maintainer to publish it first. A locally built wheel can be used as the requirement before publication.

## 1. Download on a connected machine

Use a connected machine with the same supported operating system, architecture, and Python minor version as the target. Activate a staging environment, create the destination directory, then run the matching download command.

Linux x86_64:

```bash
mkdir semble-offline-wheels
python -m pip download --only-binary=:all: --dest semble-offline-wheels "semble[mcp] @ https://github.com/pszemraj/semble-offline/releases/download/v0.7.3%2Boffline.1/semble-0.7.3%2Boffline.1-py3-none-manylinux_2_34_x86_64.whl"
```

Apple Silicon macOS:

```bash
mkdir semble-offline-wheels
python -m pip download --only-binary=:all: --dest semble-offline-wheels "semble[mcp] @ https://github.com/pszemraj/semble-offline/releases/download/v0.7.3%2Boffline.1/semble-0.7.3%2Boffline.1-py3-none-macosx_11_0_arm64.whl"
```

The resulting `semble-offline-wheels/` directory is the complete transfer payload.

## 2. Transfer the wheel directory

Move `semble-offline-wheels/` to the disconnected machine through the approved transfer mechanism. Preserve every file in the directory.

## 3. Install on the disconnected target

Activate the destination environment, change to the directory containing `semble-offline-wheels/`, then paste:

```bash
python -m pip install --no-index --find-links ./semble-offline-wheels "semble[mcp]==0.7.3+offline.1"
```

`--no-index` prevents the installer from contacting a package index and `--find-links` restricts dependency resolution to the transferred directory.

## 4. Verify without network access

Run diagnostics with an empty cache and invalid proxy endpoints. This exercises local grammar extraction; for an actual network-blocking acceptance test, disconnect the machine or apply an OS network restriction as well:

```bash
XDG_CACHE_HOME="$(mktemp -d)" HF_HUB_OFFLINE=1 HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 python -m semble doctor --full
```

The command should end with `All required checks passed.` The grammar cache must be writable: dependency parsers extract into `$XDG_CACHE_HOME/semble/grammars/<version>/`, without downloads. You can now run `semble install` to configure an agent on the disconnected machine.

## Internal package index

An organization with an internal Python package repository can upload the release wheel there instead. Users can then install the exact wheel and its dependencies through the internal index; public PyPI publication is not required.

If `pip download --only-binary=:all:` cannot find a binary dependency for the target Python version, resolve that dependency on the connected staging system before transfer. Do not build arbitrary source distributions on the disconnected production target unless that is already part of the organization's package review process.
