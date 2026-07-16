# Offline transfer

The release wheel contains Semble's model and grammar assets, but it does not vendor ordinary Python dependencies. A fully disconnected target therefore needs the release wheel and compatible wheels for all dependencies.

Run the download step on a connected Linux x86_64 system with the same Python minor version as the target. Activate a temporary environment, then download the complete wheel set:

```bash
mkdir semble-offline-wheels
python -m pip download --only-binary=:all: --dest semble-offline-wheels "semble[mcp] @ https://github.com/pszemraj/semble-offline/releases/download/v0.5.1%2Boffline.1/semble-0.5.1%2Boffline.1-py3-none-manylinux_2_34_x86_64.whl"
```

Transfer `semble-offline-wheels/` through the approved mechanism. On the disconnected target, activate the destination environment and install only from that directory:

```bash
python -m pip install --no-index --find-links ./semble-offline-wheels "semble[mcp]==0.5.1+offline.1"
```

Then prove that runtime operation does not need the network:

```bash
HF_HUB_OFFLINE=1 HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 python -m semble doctor --full
```

An organization with an internal Python package repository can upload the release wheel there instead. In that setup, users can install the exact wheel through the internal index after the repository administrator makes it available; no public PyPI publication is required.

If `pip download --only-binary=:all:` cannot find a binary dependency for the target Python version, resolve that dependency in the connected staging environment before transfer. Do not build arbitrary source distributions on the disconnected production target unless that is already part of the organization's package review process.
