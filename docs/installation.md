# Configure a coding agent

[Install and verify Semble Offline](../README.md#install-and-verify) in the Python environment your agent will use. For a disconnected target, follow the [offline transfer procedure](offline-transfer.md) first.

## Choose integrations

Detect installed agents and choose integrations interactively:

```bash
semble install
```

For unattended setup, specify an agent and integrations:

```bash
semble install --agent codex --type mcp instructions --yes
```

Replace `codex` with an ID shown by `semble install --help`. Integration types are:

| Type | Effect |
| --- | --- |
| `mcp` | Adds a server entry to the agent's configuration. Requires the `[mcp]` package extra. |
| `instructions` | Adds CLI usage guidance to the agent's instructions file. |
| `subagent` | Installs a dedicated Semble search agent. |
| `skill` | Installs the Semble skill and a pointer in the instructions file. |

Support varies by agent. Without `--type`, the installer selects supported MCP, instructions, and sub-agent integrations; skills are opt-in. It shows the paths it will change and asks for confirmation unless `--yes` is given. Existing unrelated JSON/TOML settings are preserved. Restart the agent after installation.

## Python executable

MCP entries use the resolved `sys.executable` path from the installer, with arguments `-m semble`. Keep the Python environment in place; if it moves, update the command or rerun the installer.

For a virtual environment whose Python executable is a symlink, inspect the generated command. If it resolves outside that environment, replace it with the path printed by `python -c 'import sys; print(sys.executable)'` from the intended environment.

## Share an HTTP server

Generated MCP entries start a separate stdio server for each agent. To share one running server among clients that support streamable HTTP, start it manually:

```bash
python -m semble --http --port 8000
```

Configure each client with `http://127.0.0.1:8000/mcp`. The server listens on localhost; `--port` changes its port. Keep the process running while clients use it.

## Remove integrations

```bash
semble uninstall --agent codex --type all --yes
```

Use the same agent ID and choose individual integration types to remove only those entries. For search commands after setup, see [Search a repository](../README.md#search-a-repository).
