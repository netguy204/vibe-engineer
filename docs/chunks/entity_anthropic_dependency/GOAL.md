---
status: HISTORICAL
ticket: null
parent_chunk: null
code_paths:
- src/entity_shutdown.py
- tests/test_entity_shutdown.py
- tests/test_entity_shutdown_cli.py
code_references:
- ref: src/entity_shutdown.py#run_consolidation
  implements: "Guard check for anthropic import before API call"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: implementation
depends_on: []
created_after:
- entity_memory_decay
- entity_memory_schema
- entity_shutdown_skill
- entity_startup_skill
- entity_touch_command
- orch_retry_single
---

# Chunk Goal

## Minor Goal

Add `anthropic` as a dependency of vibe-engineer so that `ve entity shutdown` consolidation works.

`entity_shutdown.py` imports `anthropic` for LLM-driven memory consolidation, but `anthropic` is not declared in vibe-engineer's package dependencies. When installed via `uv tool install`, the package is missing from the tool environment, causing `ModuleNotFoundError` at runtime.

Fix: add `anthropic` to `pyproject.toml` dependencies. If the dependency should be optional (not all users need entity features), add it as an optional extra (e.g., `[entity]`) with a clear error message when missing.

Reported by Database Savings Plans Steward.

## Success Criteria

- `anthropic` is declared in `pyproject.toml` dependencies (or as an optional extra)
- `uv run ve entity shutdown <name> --memories-file <file>` runs without ModuleNotFoundError
- If optional: import failure produces a clear error message directing user to install the extra
- Tests verify the import path works

