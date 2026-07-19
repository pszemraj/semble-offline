# Offline transfer

The release wheel contains Semble's model and grammar assets, but it does not vendor ordinary Python dependencies. A fully disconnected target needs the release wheel and compatible wheels for all dependencies.

## 1. Download on a connected machine

Use a connected machine with the same supported operating system, architecture, and Python minor version as the target. Activate a staging environment, create the destination directory, then run the matching download command.

Linux x86_64:

```bash
mkdir semble-offline-wheels
python -m pip download --only-binary=:all: --dest semble-offline-wheels "semble[mcp] @ https://github.com/pszemraj/semble-offline/releases/download/v0.5.1%2Boffline.2/semble-0.5.1%2Boffline.2-py3-none-manylinux_2_34_x86_64.whl"
```

Apple Silicon macOS:

```bash
mkdir semble-offline-wheels
python -m pip download --only-binary=:all: --dest semble-offline-wheels "semble[mcp] @ https://github.com/pszemraj/semble-offline/releases/download/v0.5.1%2Boffline.2/semble-0.5.1%2Boffline.2-py3-none-macosx_11_0_arm64.whl"
```

The resulting `semble-offline-wheels/` directory is the complete transfer payload.

## 2. Transfer the wheel directory

Move `semble-offline-wheels/` to the disconnected machine through the approved transfer mechanism. Preserve every file in the directory.

## 3. Install on the disconnected target

Activate the destination environment, change to the directory containing `semble-offline-wheels/`, then paste:

```bash
python -m pip install --no-index --find-links ./semble-offline-wheels "semble[mcp]==0.5.1+offline.2"
```

`--no-index` prevents the installer from contacting a package index and `--find-links` restricts dependency resolution to the transferred directory.

## 4. Verify without network access

Run diagnostics with invalid proxy endpoints so an accidental network request fails immediately:

```bash
HF_HUB_OFFLINE=1 HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 python -m semble doctor --full
```

The command should end with `All required checks passed.` You can now run `semble install` to configure an agent on the disconnected machine.

## Internal package index

An organization with an internal Python package repository can upload the release wheel there instead. Users can then install the exact wheel and its dependencies through the internal index; public PyPI publication is not required.

If `pip download --only-binary=:all:` cannot find a binary dependency for the target Python version, resolve that dependency on the connected staging system before transfer. Do not build arbitrary source distributions on the disconnected production target unless that is already part of the organization's package review process.
