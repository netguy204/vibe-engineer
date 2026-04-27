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
  implements: "Loads .env from resolved project root (or parent dirs) into os.environ with no-override semantics"
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

The `ve` CLI auto-loads `.env` files at startup so environment variables like `ANTHROPIC_API_KEY` are available to every subcommand without manual `export`.

The CLI's Click group callback resolves the project root (`.ve-task.yaml` → `.git` → CWD) and loads any `.env` found there into `os.environ` before dispatching to a subcommand. Existing environment variables always win — `.env` values are only set when a key is not already present. A missing `.env` is silently ignored so CLI startup is never broken by dotenv issues.

Operators can therefore drop a `.env` file in their project root with API keys and other config that any `ve` subcommand needs.

## Success Criteria

- `ve` CLI loads `.env` from the resolved project root on startup
- Variables in `.env` are available as environment variables to all subcommands
- Existing environment variables take precedence over `.env` values (no override)
- Missing `.env` file is silently ignored (not an error)
- Works from subdirectories (uses project root resolution, not CWD)
- Tests verify: `.env` loaded, env var precedence, missing file handling

