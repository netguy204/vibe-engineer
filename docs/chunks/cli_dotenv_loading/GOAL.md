---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- pyproject.toml
- src/cli/dotenv_loader.py
- src/cli/__init__.py
- tests/test_dotenv_loader.py
code_references:
- ref: src/cli/dotenv_loader.py#load_dotenv_from_project_root
  implements: "Loads .env from resolved project root into os.environ with no-override semantics"
- ref: src/cli/__init__.py#cli
  implements: "Wires dotenv loading into CLI startup via Click group callback"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_monitor_guardrails
---

# Chunk Goal

## Minor Goal

Auto-load `.env` files in the `ve` CLI entrypoint so environment variables like `ANTHROPIC_API_KEY` are available without manual `export`.

Currently, `ve entity shutdown` requires `ANTHROPIC_API_KEY` for memory consolidation, but the key must be manually exported or prefixed on each invocation. The CLI should check for `.env` files using the same project root resolution chain (`.ve-task.yaml` → `.git` → CWD) and load them early in the CLI startup.

This makes it convenient for operators to drop a `.env` file in their project root with API keys and other config that the CLI needs.

## Success Criteria

- `ve` CLI loads `.env` from the resolved project root on startup
- Variables in `.env` are available as environment variables to all subcommands
- Existing environment variables take precedence over `.env` values (no override)
- Missing `.env` file is silently ignored (not an error)
- Works from subdirectories (uses project root resolution, not CWD)
- Tests verify: `.env` loaded, env var precedence, missing file handling

