

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The `anthropic>=0.40.0` dependency was already added to `pyproject.toml` as part
of the `entity_shutdown_skill` chunk (commit `ec16eb5`). It is also pulled in
transitively via `claude-agent-sdk`. The core fix is already in place.

However, `entity_shutdown.py` uses a bare top-level `import anthropic` (line 21)
with no graceful fallback. While the dependency is now declared, the GOAL's
suggestion about an optional extra with a clear error message is worth
considering. Since `anthropic` is already a transitive dependency of
`claude-agent-sdk` (which is a core dependency), making it optional would be
misleading — it's always installed. The correct approach is:

1. **Keep `anthropic` as a core dependency** — it's already there and is also
   transitive via `claude-agent-sdk`. No change needed to `pyproject.toml`.
2. **Guard the import in `entity_shutdown.py`** — wrap the top-level import in
   a try/except that produces a clear, actionable error message. This is
   defensive programming: if a future refactor removes `claude-agent-sdk` or
   changes the dependency tree, the user gets a clear message instead of a raw
   `ModuleNotFoundError`.
3. **Add a test** verifying the guarded import path produces the expected error
   when `anthropic` is missing.

This aligns with DEC-001 (uvx-based CLI utility — the tool should work
predictably when installed via `uvx`).

No new DECISIONS.md entry is needed — this is a straightforward dependency fix,
not an architectural choice.

## Sequence

### Step 1: Guard the `anthropic` import in `entity_shutdown.py`

Replace the bare `import anthropic` at line 21 with a try/except block that
catches `ModuleNotFoundError` and raises a clear error message directing the
user to install the `anthropic` package.

The guard should set `anthropic = None` on failure and defer the actual error
to the point of use (`run_consolidation`), so that pure-parsing functions like
`parse_extracted_memories` and `parse_consolidation_response` remain usable
without the SDK.

Location: `src/entity_shutdown.py`

Pattern:
```python
try:
    import anthropic
except ModuleNotFoundError:
    anthropic = None
```

Then at the top of `run_consolidation()`, before the API call:
```python
if anthropic is None:
    raise RuntimeError(
        "The 'anthropic' package is required for memory consolidation. "
        "Install it with: pip install anthropic"
    )
```

### Step 2: Add a backreference comment

Add a chunk backreference to the guarded import:
```python
# Chunk: docs/chunks/entity_anthropic_dependency - Guard anthropic import
```

Location: `src/entity_shutdown.py`, above the try/except block.

### Step 3: Add test for missing `anthropic` error message

Add a test in `tests/test_entity_shutdown.py` that patches `entity_shutdown.anthropic`
to `None` and verifies `run_consolidation` raises `RuntimeError` with the
expected message when the API call would be reached (i.e., with enough memories
to trigger consolidation).

This is a meaningful behavior test per TESTING_PHILOSOPHY.md: it verifies a
user-facing error path, not a trivial property.

Location: `tests/test_entity_shutdown.py`, new test in `TestRunConsolidation`.

### Step 4: Verify existing tests still pass

Run `uv run pytest tests/test_entity_shutdown.py tests/test_entity_shutdown_cli.py -v`
to confirm the guarded import doesn't break existing test mocking patterns
(which use `@patch("entity_shutdown.anthropic")`).

### Step 5: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter `code_paths` to list the files touched.

## Risks and Open Questions

- **Mock compatibility**: Existing tests mock `entity_shutdown.anthropic` via
  `@patch`. The guarded import sets `anthropic` to the module or `None`. The
  patch should still work since it replaces the module-level name. Verify in
  Step 4.
- **CLI error propagation**: The `shutdown` CLI command wraps
  `run_consolidation` in a generic `except Exception` that converts to
  `ClickException`. The `RuntimeError` from the guard will surface as
  "Consolidation failed: The 'anthropic' package is required..." — this is
  acceptable and readable.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->