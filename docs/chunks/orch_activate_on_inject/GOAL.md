---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/orchestrator/scheduler.py
  - src/orchestrator/models.py
  - src/orchestrator/state.py
  - src/orchestrator/api.py
  - tests/test_orchestrator_scheduler.py
code_references:
  - ref: src/orchestrator/scheduler.py#activate_chunk_in_worktree
    implements: "Activate target chunk in worktree, displacing any existing IMPLEMENTING chunk"
  - ref: src/orchestrator/scheduler.py#restore_displaced_chunk
    implements: "Restore a displaced chunk back to IMPLEMENTING before merge"
  - ref: src/orchestrator/scheduler.py#verify_chunk_active_status
    implements: "Refactored to use Chunks class for frontmatter parsing"
  - ref: src/orchestrator/scheduler.py#Scheduler::_run_work_unit
    implements: "Integration of chunk activation after worktree creation"
  - ref: src/orchestrator/scheduler.py#Scheduler::_advance_phase
    implements: "Restore displaced chunk before merge when work unit completes"
  - ref: src/orchestrator/models.py#WorkUnit
    implements: "Added displaced_chunk field to track displaced IMPLEMENTING chunks"
  - ref: src/orchestrator/state.py#StateStore::_migrate_v5
    implements: "Database migration adding displaced_chunk column"
  - ref: src/orchestrator/state.py#StateStore::_row_to_work_unit
    implements: "Handle displaced_chunk column in row-to-model conversion"
  - ref: src/orchestrator/api.py#_parse_chunk_status
    implements: "Refactored to use Chunks class for consistent frontmatter parsing"
  - ref: tests/test_orchestrator_scheduler.py#TestActivateChunkInWorktree
    implements: "Unit tests for activate_chunk_in_worktree helper"
  - ref: tests/test_orchestrator_scheduler.py#TestRestoreDisplacedChunk
    implements: "Unit tests for restore_displaced_chunk helper"
  - ref: tests/test_orchestrator_scheduler.py#TestChunkActivationInWorkUnit
    implements: "Integration tests for chunk activation during work unit execution"
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
created_after: ["orch_verify_active"]
---

# Chunk Goal

## Minor Goal

When the orchestrator injects a chunk (via `ve orch inject`), it must transition the chunk's status from FUTURE to IMPLEMENTING before running agent phases. Currently, the orchestrator injects FUTURE chunks and immediately runs the PLAN phase, but the `/chunk-plan` skill uses `ve chunk list --latest` to find the active chunk - which only returns IMPLEMENTING chunks. This causes agents to either:

1. Fail immediately with "No implementing chunk found"
2. Find a different chunk that happens to be IMPLEMENTING and work on the wrong chunk

The fix: When a work unit enters the RUNNING state for its first phase, the orchestrator should update the chunk's GOAL.md frontmatter to change `status: FUTURE` to `status: IMPLEMENTING` before spawning the agent.

**Edge case - existing IMPLEMENTING chunk in worktree:**

When the orchestrator creates a worktree from main, there may already be a chunk in IMPLEMENTING status (the user was working on something manually). If we just set our chunk to IMPLEMENTING, there would be two IMPLEMENTING chunks, which violates the invariant that only one chunk can be IMPLEMENTING at a time.

Solution:
1. On worktree creation, detect if any chunk is already IMPLEMENTING
2. If so, temporarily set that chunk to FUTURE in the worktree (not main)
3. Set the orchestrator's target chunk to IMPLEMENTING
4. Run all agent phases
5. Before commit/merge, restore the displaced chunk back to IMPLEMENTING
6. This ensures the merge back to main doesn't change the status of the user's active chunk

## Success Criteria

1. **Status transition on first dispatch**
   - When a work unit transitions from READY to RUNNING for the first time (PLAN phase), the scheduler activates the chunk in the worktree
   - If status is FUTURE, it updates to IMPLEMENTING before spawning the agent
   - If status is already IMPLEMENTING (edge case), no change needed

2. **Displaced chunk handling**
   - If the worktree already has an IMPLEMENTING chunk (inherited from main), it is temporarily set to FUTURE
   - The displaced chunk's identity is stored in the work unit state
   - Before commit/merge, the displaced chunk is restored to IMPLEMENTING
   - Net effect: the merge doesn't change the status of the user's manually-active chunk

3. **Worktree contains exactly one IMPLEMENTING chunk**
   - After activation, only the orchestrator's target chunk is IMPLEMENTING
   - `ve chunk list --latest` returns the correct chunk

4. **Agent correctly identifies the chunk**
   - After the fix, agents running `/chunk-plan` successfully find their assigned chunk
   - Test: inject a FUTURE chunk, verify the agent works on the correct chunk (not a different one)

5. **Tests verify the behavior**
   - Unit test: status transition happens when dispatching FUTURE chunk
   - Unit test: displaced IMPLEMENTING chunk is set to FUTURE
   - Unit test: displaced chunk is restored before merge
   - Unit test: no displacement needed when no existing IMPLEMENTING chunk
   - Integration test: full inject → agent execution successfully identifies correct chunk

