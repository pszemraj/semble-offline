---
name: semble
description: Code search for the current repository. Use this before Grep, Glob or find whenever you need to locate code, such as where something is implemented, which file defines a function, class or symbol, how a feature works, or where docs and config live.
---

Use `semble search` to find code by behavior or symbol name. Use one focused query at a time:

```bash
semble search "authentication flow" ./my-project --max-snippet-lines 10
semble search "save_pretrained" ./my-project
semble search "save model to disk" ./my-project --top-k 10
semble search "deployment guide" ./my-project --content docs
semble search "database host port" ./my-project --content config
semble search "authentication" ./my-project --content all
semble find-related src/auth.py 42 ./my-project
semble search "invoice endpoint" ./service-a ../service-b
```

Search returns full chunks by default; `--max-snippet-lines` limits source lines per result and `--top-k` controls the result count. Select `--content docs` for prose, `config` for configuration files, or `all` for code, docs, and config together.

Paths default to the current directory. Multiple paths share one ranked result set, with repository-prefixed result paths and a JSON `repos` map. Use the returned path and line with `find-related` and the same search roots to find similar implementations. A Git URL requests a network clone; use local paths when offline.

The index is built on first use and updated incrementally when files change. Read the relevant function or class at a returned location before editing. Use exact-text search when you need every occurrence of a known literal.

If `semble` is not on `$PATH`, use `python -m semble` from the environment where Semble Offline is installed. Keep that offline installation in place.
