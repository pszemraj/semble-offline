# Installation and agent setup

Semble Offline supports CPython 3.10 through 3.14 on Linux x86_64 systems with glibc 2.34 or later. Activate the environment where Semble and its agent integrations should run before installing it.

## Install a release wheel

The release wheel is the preferred installation because its exact contents and SHA-256 checksum are attached to a versioned GitHub Release:

```bash
python -m pip install "semble[mcp] @ https://github.com/pszemraj/semble-offline/releases/download/v0.5.1%2Boffline.1/semble-0.5.1%2Boffline.1-py3-none-manylinux_2_34_x86_64.whl"
```

Your configured package index supplies ordinary dependencies. If MCP is not needed, remove `[mcp]` from the requirement.

## Install from Git

The tagged Git source produces the same platform-specific wheel locally through the standard Python build interface:

```bash
python -m pip install "semble[mcp] @ git+https://github.com/pszemraj/semble-offline.git@v0.5.1+offline.1"
```

This route requires `git`, access to GitHub, and access to build requirements through the configured package index. Prefer the release wheel when build isolation cannot reach an index.

## Verify

Run the quick installation check:

```bash
semble doctor
```

Before transferring an environment into a restricted network, validate every asset hash and load representative grammar aliases and the embedding model:

```bash
HF_HUB_OFFLINE=1 python -m semble doctor --full
```

`semble --version` and `python -m semble --version` should both report `0.5.1+offline.1`.

## Configure agents

Install with the `[mcp]` extra, then run the interactive installer:

```bash
semble install
```

For unattended setup, select agents and integration types explicitly:

```bash
semble install --agent claude codex --type mcp instructions --yes
```

The installer supports MCP entries, instruction blocks, and dedicated search sub-agents where each target permits them. It preserves unrelated configuration and can reverse its own changes:

```bash
semble uninstall --agent claude codex --type all --yes
```

MCP entries invoke the absolute `sys.executable` path from the environment used to run `semble install`, with arguments `-m semble`. Keep that environment in place after setup. If the environment moves, rerun the installer so it refreshes the path.

## Upgrade or reinstall

Use the same wheel or Git requirement with `--upgrade --force-reinstall`. Do not follow it with an unqualified `python -m pip install semble`, which may replace this distribution with upstream Semble and restore runtime asset downloads.

For a target with no package-index access, use the [offline transfer procedure](offline-transfer.md).
