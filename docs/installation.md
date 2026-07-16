# Install and configure an agent

Semble Offline supports CPython 3.10 through 3.14 on Linux x86_64 with glibc 2.34 or later.

## 1. Activate the destination environment

Activate the Python environment that the agent will use. The installer records that environment's absolute Python path when it writes MCP configuration.

## 2. Install Semble Offline

Choose one command. The release wheel is the preferred fixed artifact:

```bash
python -m pip install "semble[mcp] @ https://github.com/pszemraj/semble-offline/releases/download/v0.5.1%2Boffline.1/semble-0.5.1%2Boffline.1-py3-none-manylinux_2_34_x86_64.whl"
```

Install from the tagged Git source when a wheel URL is not convenient:

```bash
python -m pip install "semble[mcp] @ git+https://github.com/pszemraj/semble-offline.git@v0.5.1+offline.1"
```

The Git route requires `git`, GitHub access, and access to build requirements through the configured package index. Both routes obtain ordinary Python dependencies from that index. Remove `[mcp]` only if the agent will call the CLI directly.

## 3. Verify the installation

Run the full check before configuring an agent or moving the environment behind a firewall:

```bash
HF_HUB_OFFLINE=1 python -m semble doctor --full
```

The command checks the supported platform, every bundled asset hash, representative grammar aliases, the embedding model, and the MCP dependencies. It should end with `All required checks passed.` Both `semble --version` and `python -m semble --version` should report `0.5.1+offline.1`.

## 4. Configure the agent

Detect installed agents and choose integrations interactively:

```bash
semble install
```

For unattended setup, specify the agent and integrations:

```bash
semble install --agent codex --type mcp instructions --yes
```

Replace `codex` with an ID shown by `semble install --help`. Integration types are `mcp`, `instructions`, and `subagent`; support varies by agent. The installer preserves unrelated configuration.

Remove the configuration later with the matching agent ID:

```bash
semble uninstall --agent codex --type all --yes
```

## 5. Tell the agent to use it

Restart an already-running agent so it reloads MCP configuration, then paste:

```text
Use Semble for code discovery in this repository. Search with one focused description at a time. Use `semble search "<behavior or code description>" .` from the shell, or the Semble MCP search tool when available. After finding one relevant implementation, use `semble find-related <file_path> <line> .` to find similar code. Use exact-text search only for known strings, symbols, and exhaustive occurrence checks.
```

The [README agent block](../README.md#paste-this-into-your-agent) includes installation and verification instructions for an agent that should perform the entire setup itself.

## Configuration behavior

MCP entries invoke the absolute `sys.executable` path from the environment used to run `semble install`, with arguments `-m semble`. Keep that environment in place. If it moves, rerun `semble install` to refresh the path.

Use the same wheel or Git requirement with `--upgrade --force-reinstall` to upgrade or repair the package. Do not follow it with an unqualified `python -m pip install semble`, which may replace this distribution with upstream Semble and restore runtime asset downloads.

For a target with no package-index access, use the [offline transfer procedure](offline-transfer.md).
