---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/orchestrator/models.py
  - src/orchestrator/state.py
  - src/orchestrator/scheduler.py
  - src/orchestrator/worktree.py
  - src/chunks.py
  - tests/test_orch_rename_propagation.py
code_references:
- ref: src/orchestrator/scheduler.py#Scheduler::_detect_rename
  implements: "Detect chunk renames by comparing baseline to current IMPLEMENTING chunks"
- ref: src/orchestrator/scheduler.py#Scheduler::_propagate_rename
  implements: "Propagate rename through work units, branches, directories, and conflict data"
- ref: src/orchestrator/state.py#StateStore::_migrate_v15
  implements: "Schema migration for baseline_implementing column"
- ref: src/orchestrator/worktree.py#WorktreeManager::rename_branch
  implements: "Rename orchestrator branch for renamed chunk"
- ref: tests/test_orch_rename_propagation.py
  implements: "Tests for rename detection and propagation"
narrative: null
investigation: null
subsystems:
- subsystem_id: orchestrator
  relationship: implements
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- dead_code_removal
- narrative_compact_extract
- persist_retry_state
- repo_cache_dry
- reviewer_decisions_dedup
- worktree_merge_extract
- phase_aware_recovery
---

# Chunk Goal

## Minor Goal

When a chunk is renamed during the orchestrator's PLAN phase (via `ve chunk
suggest-prefix` and the operator accepting), the scheduler detects the rename
after the phase completes and propagates the new name through the work unit's
identity. Without this propagation, the work unit's stale reference to the old
name would cause failures in subsequent phases — most critically during
finalization, where `verify_chunk_active_status` would look for the old
directory name, fail with "Chunk not found or GOAL.md missing", and leave the
work unit stuck in NEEDS_ATTENTION.

The orchestrator scheduler runs post-phase rename detection so that when a
chunk directory is renamed inside a worktree during any phase, the work unit's
identity updates to match — propagating the new name through the database
primary key, `.ve/chunks/` directory structure, git branch name, conflict
verdicts, and blocked_by lists in other work units.

## Success Criteria

- At worktree creation time, the scheduler snapshots the set of IMPLEMENTING
  chunk names in the worktree and persists it alongside the work unit (e.g.,
  as a field on the WorkUnit model or a file in `.ve/chunks/{name}/`).
- After any phase completes, the scheduler computes
  `(current IMPLEMENTING chunks) - (baseline IMPLEMENTING snapshot)`. If the
  result differs from `work_unit.chunk`, a rename is detected.
- On detected rename, the scheduler updates the work unit's `chunk` field to
  the new name before advancing to the next phase.
- The `.ve/chunks/{old_name}/` directory (containing worktree, logs,
  base_branch) is renamed to `.ve/chunks/{new_name}/`.
- The git branch `orch/{old_name}` is renamed to `orch/{new_name}`.
- Any other work units with the old name in their `blocked_by` list are updated.
- Any `conflict_verdicts` entries (in other work units) keyed by the old name
  are re-keyed to the new name.
- The `conflict_analyses` table rows referencing the old name in `chunk_a` or
  `chunk_b` are updated.
- The `_running_agents` dict key is updated (if applicable).
- The status_log table entries continue to provide a coherent audit trail (old
  entries retain old name for history; new entries use new name).
- A test verifies the end-to-end rename propagation: inject a chunk, simulate
  a rename during PLAN, advance the phase, and confirm all references are
  updated.
- If rename detection is ambiguous (e.g., the set difference yields zero or
  more than one chunk), the work unit is marked NEEDS_ATTENTION with a
  diagnostic message rather than silently proceeding with the stale name.

## Approach

The worktree may have been created from a branch that already had unrelated
IMPLEMENTING chunks. Naively scanning for "the IMPLEMENTING chunk" would
conflate the work unit's chunk with pre-existing ones. The solution is a
set-difference approach:

**At worktree creation time** (in `_run_work_unit`, after
`activate_chunk_in_worktree` succeeds): snapshot the full set of IMPLEMENTING
chunk names in the worktree and persist it on the work unit (new field:
`baseline_implementing: list[str]`). This captures all chunks that were already
IMPLEMENTING on the base branch plus the one just activated.

**After each phase completes** (in `_handle_agent_result`, before
`_advance_phase`): enumerate the current IMPLEMENTING chunks in the worktree,
compute `current_set - baseline_set`. The result should be exactly
`{work_unit.chunk}`. If it's `{new_name}` instead, a rename occurred.

**Propagation steps** when rename is detected (`old` → `new`):

1. **Database**: Rename the primary key (`work_units.chunk`) — requires
   INSERT + DELETE since SQLite doesn't support PK updates, done in a
   transaction.
2. **Filesystem**: Rename `.ve/chunks/{old}/` → `.ve/chunks/{new}/`.
3. **Git branch**: `git branch -m orch/{old} orch/{new}`.
4. **Cross-references**: Update `blocked_by` lists and `conflict_verdicts`
   dicts in all work units. Update `conflict_analyses` table rows where
   `chunk_a` or `chunk_b` matches the old name.
5. **In-memory state**: Update `_running_agents` dict key.
6. **Baseline update**: Update the `baseline_implementing` snapshot to reflect
   the new name so subsequent phases don't re-trigger detection.

This detection runs after every phase (not just PLAN) for robustness, but the
rename will typically only happen during PLAN.