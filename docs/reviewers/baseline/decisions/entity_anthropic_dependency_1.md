---
decision: APPROVE
summary: "All success criteria satisfied — anthropic declared in pyproject.toml, import guarded with clear RuntimeError, and test covers the missing-package path"
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `anthropic` is declared in `pyproject.toml` dependencies (or as an optional extra)

- **Status**: satisfied
- **Evidence**: `pyproject.toml` line 8 declares `"anthropic>=0.40.0"` as a core dependency. This was already present from the `entity_shutdown_skill` chunk and is also a transitive dependency of `claude-agent-sdk`. No change needed here — the plan correctly identified this.

### Criterion 2: `uv run ve entity shutdown <name> --memories-file <file>` runs without ModuleNotFoundError

- **Status**: satisfied
- **Evidence**: The bare `import anthropic` at the top of `entity_shutdown.py` has been wrapped in a try/except that catches `ModuleNotFoundError` and sets `anthropic = None`. When the package is installed (normal case), the import succeeds normally. The raw `ModuleNotFoundError` can no longer surface.

### Criterion 3: If optional: import failure produces a clear error message directing user to install the extra

- **Status**: satisfied
- **Evidence**: `entity_shutdown.py` lines 463-467 — when `anthropic is None`, `run_consolidation()` raises `RuntimeError("The 'anthropic' package is required for memory consolidation. Install it with: pip install anthropic")`. The guard is placed at point-of-use (before the API call in step 5) so parsing functions remain usable without the SDK, matching the plan's intent.

### Criterion 4: Tests verify the import path works

- **Status**: satisfied
- **Evidence**: `tests/test_entity_shutdown.py` adds `test_raises_when_anthropic_missing` which patches `entity_shutdown.anthropic` to `None` and asserts `RuntimeError` with match `"anthropic.*required"`. All 34 tests pass including this new one.
