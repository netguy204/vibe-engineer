<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The orchestrator scheduler currently assumes a work unit's chunk name remains
constant throughout its lifecycle. When an operator accepts a rename suggestion
during the PLAN phase (via `ve chunk suggest-prefix`), the filesystem directory
changes but the work unit's `chunk` field retains the old name. This causes
failures in finalization when `verify_chunk_active_status` can't find the old
chunk directory.

**Solution Strategy:**

1. **Baseline snapshot at worktree creation**: Record the set of IMPLEMENTING
   chunk names in the worktree immediately after `activate_chunk_in_worktree`
   succeeds. This captures the baseline against which renames are detected.

2. **Post-phase rename detection**: After each phase completes successfully,
   compare current IMPLEMENTING chunks against the baseline. If the work unit's
   original chunk is missing but a new IMPLEMENTING chunk exists, a rename
   occurred.

3. **Atomic propagation**: When a rename is detected, atomically update:
   - Database `work_units.chunk` (INSERT + DELETE transaction since it's PK)
   - Filesystem `.ve/chunks/{old}/` → `.ve/chunks/{new}/`
   - Git branch `orch/{old}` → `orch/{new}`
   - Cross-references in other work units (`blocked_by`, `conflict_verdicts`)
   - `conflict_analyses` table entries
   - In-memory `_running_agents` dict key
   - The baseline snapshot itself (so subsequent phases don't re-trigger)

**Existing Patterns Leveraged:**

- `StateStore.transaction()` for atomic database operations
- `WorktreeManager` git operations for branch renaming
- `Chunks.list_chunks_by_status()` (new helper) for enumerating IMPLEMENTING chunks

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS rename
  propagation as part of the orchestrator's work unit lifecycle management.
  The pattern of detecting state changes after phase completion fits naturally
  alongside existing phase advancement logic in `_handle_agent_result`.

## Sequence

### Step 1: Add `baseline_implementing` field to WorkUnit model

Add a new field `baseline_implementing: list[str] = []` to the `WorkUnit` model
in `src/orchestrator/models.py`. This field stores the set of IMPLEMENTING chunk
names that existed in the worktree at creation time.

Location: `src/orchestrator/models.py`

### Step 2: Add database migration for baseline_implementing column

Add migration `_migrate_v14` to `StateStore` that adds the `baseline_implementing`
column (stored as JSON TEXT). Update `CURRENT_VERSION` to 14. Update
`_row_to_work_unit` and `create_work_unit`/`update_work_unit` to handle the new field.

Location: `src/orchestrator/state.py`

### Step 3: Add `list_implementing_chunks` helper to Chunks class

Add a new method `list_implementing_chunks() -> list[str]` to the `Chunks` class
that returns all chunk names with IMPLEMENTING status. This is similar to
`get_current_chunk()` but returns all IMPLEMENTING chunks, not just the first one.

Location: `src/chunks.py`

### Step 4: Capture baseline in `_run_work_unit` after activation

After `activate_chunk_in_worktree` succeeds during the PLAN phase, use the new
`list_implementing_chunks()` helper to snapshot the current IMPLEMENTING chunks
and persist to `work_unit.baseline_implementing`.

Location: `src/orchestrator/scheduler.py` in `_run_work_unit`

### Step 5: Implement `_detect_rename` helper method

Add a private method `_detect_rename(work_unit, worktree_path) -> tuple[str, str] | None`
that:
1. Loads current IMPLEMENTING chunks from the worktree
2. Computes `current_set - baseline_set`
3. If the result is exactly one chunk different from `work_unit.chunk`, returns
   `(old_name, new_name)`
4. If ambiguous (zero or >1 new chunks), returns `None` (caller will escalate)

Location: `src/orchestrator/scheduler.py`

### Step 6: Implement `_propagate_rename` method

Add a method `_propagate_rename(old_name: str, new_name: str) -> None` that
performs the atomic propagation:

1. **Database transaction**:
   - Create new work unit row with new chunk name (copy all fields)
   - Delete old work unit row
   - Update `blocked_by` lists in other work units
   - Update `conflict_verdicts` keys in other work units
   - Update `conflict_analyses` table rows

2. **Filesystem**:
   - Rename `.ve/chunks/{old}/` → `.ve/chunks/{new}/`

3. **Git branch**:
   - `git branch -m orch/{old} orch/{new}`

4. **In-memory state**:
   - Update `_running_agents` dict key if present

5. **Baseline update**:
   - Update `baseline_implementing` to use new name

Location: `src/orchestrator/scheduler.py`

### Step 7: Integrate rename detection into `_handle_agent_result`

After a successful phase completion (before calling `_advance_phase`), call
`_detect_rename`. If a rename is detected, call `_propagate_rename`. If detection
is ambiguous, mark the work unit NEEDS_ATTENTION with a diagnostic message.

Location: `src/orchestrator/scheduler.py` in `_handle_agent_result`

### Step 8: Add WorktreeManager branch rename method

Add a `rename_branch(old_chunk: str, new_chunk: str) -> None` method to
`WorktreeManager` that renames the git branch `orch/{old}` to `orch/{new}`.

Location: `src/orchestrator/worktree.py`

### Step 9: Add StateStore methods for rename propagation

Add methods to `StateStore`:
- `rename_work_unit(old_chunk: str, new_chunk: str) -> WorkUnit`: Atomic rename
  with INSERT + DELETE in transaction
- `update_blocked_by_references(old_chunk: str, new_chunk: str) -> int`: Update
  blocked_by lists referencing old chunk
- `update_conflict_verdicts_references(old_chunk: str, new_chunk: str) -> int`:
  Re-key conflict_verdicts dicts
- `update_conflict_analyses_references(old_chunk: str, new_chunk: str) -> int`:
  Update chunk_a/chunk_b columns

Location: `src/orchestrator/state.py`

### Step 10: Write integration test for end-to-end rename propagation

Write a test that:
1. Creates a work unit for chunk "old_name"
2. Injects it into the orchestrator
3. Simulates PLAN phase completion with renamed chunk directory "new_name"
4. Advances the phase
5. Verifies all references are updated:
   - Work unit chunk field
   - `.ve/chunks/` directory name
   - Git branch name
   - Any blocked_by references in other work units

Location: `tests/test_orch_rename_propagation.py`

### Step 11: Write unit tests for rename detection edge cases

Test cases:
- Normal rename: old → new
- No rename: same chunk name before and after
- Ambiguous: multiple new IMPLEMENTING chunks (should escalate)
- Missing: chunk disappeared entirely (should escalate)

Location: `tests/test_orch_rename_propagation.py`

### Step 12: Update status_log table semantics documentation

Document that old entries retain the old chunk name for audit trail purposes,
while new entries use the new name. This preserves archaeology while maintaining
correct forward references.

Location: `src/orchestrator/state.py` (docstring updates)

## Risks and Open Questions

1. **Race condition during rename**: If the scheduler is processing multiple work
   units concurrently, and one renames while another has the old name in its
   `blocked_by`, the update could happen mid-flight. Mitigation: all rename
   propagation happens within a database transaction and the work unit is
   RUNNING (not dispatchable) during rename detection.

2. **Filesystem rename atomicity**: `shutil.move` may not be atomic across
   filesystems. Risk is low since source and destination are in the same `.ve/`
   directory. If needed, we can use `os.rename` which is atomic on POSIX.

3. **Branch rename failure recovery**: If `git branch -m` fails (e.g., new branch
   name already exists), the database and filesystem have already been updated.
   Mitigation: perform git operation first, then database/filesystem, so we can
   roll back more easily. Or: check branch existence before starting propagation.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->