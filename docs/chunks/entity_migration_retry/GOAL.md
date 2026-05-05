---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/entity_migration.py
- src/cli/entity.py
code_references:
- ref: src/entity_migration.py#migrate_entity
  implements: "Cleanup-on-failure: wraps post-create_entity_repo() work in try/except BaseException; rmtrees partial repo on any failure"
- ref: tests/test_entity_migration.py#TestMigrateEntityAtomicity
  implements: "Regression test class verifying atomicity: failed migration leaves no directory and retry succeeds"
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- chunk_demote
---

# Chunk Goal

## Minor Goal

`migrate_entity()` treats the destination repo as an all-or-nothing artifact: a
failed migration leaves no partial directory on disk, and the operator-facing
error reflects the underlying cause (LLM auth/network failure, classification
error, etc.) rather than a downstream "directory exists" collision on retry.
Re-running `ve entity migrate <name>` after any failure is safe and surfaces the
real reason the prior run failed.

## Success Criteria

- `src/entity_migration.py#migrate_entity` is atomic with respect to the
  destination directory: if any step after `create_entity_repo()` raises, the
  partially-created repo at `dest_parent/new_name` is removed before the
  exception propagates.
- A second invocation of `ve entity migrate <name>` after a failed first
  invocation succeeds (assuming the original failure cause is resolved) without
  the operator manually deleting any directory.
- The CLI error surfaced by `src/cli/entity.py#migrate` on a failed run is the
  underlying cause (e.g., missing `ANTHROPIC_API_KEY`, network error, malformed
  legacy entity), not a `"Entity directory '...' already exists"` collision.
- A regression test in `tests/` exercises the failure-then-retry path: simulate
  an LLM failure (e.g., monkeypatch `anthropic.Anthropic` or
  `synthesize_identity_page` to raise), assert the destination directory does
  not exist after the failure, then run the migration again with the failure
  removed and assert it succeeds.
- The original error remains visible to the operator (don't swallow it during
  cleanup; if cleanup itself fails, that should be surfaced as a secondary
  warning but not mask the primary cause).

## Approach

**Cleanup-on-failure (Approach 1)** is used: all work after `create_entity_repo()`
is wrapped in a `try/except BaseException`. On any exception, `shutil.rmtree`
removes the partially-created `repo_path` and the original exception is
re-raised (any cleanup error is chained via `raise RuntimeError(...) from exc`).
`BaseException` scope is deliberate — `KeyboardInterrupt` and `SystemExit` also
trigger cleanup, preventing partial dirs from lingering after a user cancels
mid-migration.

## Reproduction (the friction that prompted this work)

```
$ ve entity migrate steward
# ... TypeError: Could not resolve authentication method.
#     Expected either api_key or auth_token to be set.

$ # operator sets ANTHROPIC_API_KEY

$ ve entity migrate steward
Error: Entity directory '/Users/btaylor/Projects/vibe-engineer/steward'
       already exists. Choose a different name or remove the existing
       directory.
```

The second error is misleading — the operator did not run a successful
migration; the directory exists only because the first run created the stub
before the LLM call failed.

## Source pointers

- `src/entity_migration.py#migrate_entity` — main orchestration function. The
  `try/except BaseException` cleanup block wraps everything after the call to
  `create_entity_repo()`.
- `src/cli/entity.py#migrate` — CLI entrypoint that catches
  `ValueError` / `RuntimeError` and re-raises as `click.ClickException`.
- The "already exists" guard lives inside `create_entity_repo()` and is not
  triggered on retry because the cleanup block removes the partial dir.

## Constraints

- Do not change the public CLI signature of `ve entity migrate`.
- Do not change the on-disk shape of a successfully-migrated entity.
- Preserve the existing behavior when `anthropic` is not installed (the
  function still completes, just without LLM-synthesized wiki pages).