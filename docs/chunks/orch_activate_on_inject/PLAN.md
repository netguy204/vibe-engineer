<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The orchestrator currently creates worktrees and dispatches agents for FUTURE chunks, but doesn't update the chunk's status before running phase agents. This causes agents to fail because `/chunk-plan` uses `ve chunk list --latest` which only returns IMPLEMENTING chunks.

The fix integrates chunk activation into the scheduler's dispatch flow by **reusing existing VE infrastructure**:

1. **Use `Chunks` class in worktree context**: The worktree IS a valid VE project. Instantiate `Chunks(worktree_path)` to get access to all existing chunk operations.

2. **Detect displaced chunks**: Use `chunks.get_current_chunk()` to find any IMPLEMENTING chunk inherited from main. If found (and it's not our target), use `update_frontmatter_field` to temporarily demote it to FUTURE.

3. **Activate target chunk**: Use `chunks.activate_chunk(target_chunk)` to properly transition FUTURE → IMPLEMENTING with all existing validation.

4. **Restore before merge**: Before merging, restore any displaced chunk to IMPLEMENTING.

This approach reuses:
- `chunks.py#Chunks.get_current_chunk()` - finds IMPLEMENTING chunk
- `chunks.py#Chunks.activate_chunk()` - activates FUTURE chunks with proper guards
- `chunks.py#Chunks.parse_chunk_frontmatter()` - parses frontmatter properly
- `task_utils.py#update_frontmatter_field` - modifies frontmatter fields

**Tech debt cleanup (in scope)**: The orchestrator has duplicated frontmatter parsing in `scheduler.py#verify_chunk_active_status` and `api.py`. This chunk will refactor those to use the `Chunks` class.

## Sequence

### Step 1: Add displaced_chunk field to WorkUnit model

Add an optional `displaced_chunk: Optional[str]` field to the WorkUnit model. This stores the name of any chunk that was IMPLEMENTING when the worktree was created and had to be temporarily set to FUTURE.

Location: src/orchestrator/models.py

### Step 2: Add database migration for displaced_chunk column

Add migration v5 to add the `displaced_chunk` column to the work_units table. Update the `CURRENT_VERSION` and add column handling in `_row_to_work_unit`.

Location: src/orchestrator/state.py

### Step 3: Create activate_chunk_in_worktree helper

Create a single helper function in `scheduler.py` that encapsulates the activation workflow:

```python
def activate_chunk_in_worktree(
    worktree_path: Path,
    target_chunk: str
) -> Optional[str]:
    """Activate target chunk in worktree, displacing any existing IMPLEMENTING chunk.

    Returns the name of the displaced chunk (if any), or None.
    """
```

Implementation:
1. Instantiate `Chunks(worktree_path)`
2. Call `chunks.get_current_chunk()` to find existing IMPLEMENTING chunk
3. If found and not our target: use `update_frontmatter_field` to set it to FUTURE, return its name
4. Call `chunks.activate_chunk(target_chunk)` to activate our chunk
5. Handle the case where target is already IMPLEMENTING (no-op)

Location: src/orchestrator/scheduler.py

### Step 4: Implement chunk activation in _run_work_unit

Modify `_run_work_unit` to activate the chunk after creating the worktree but before running the agent:

1. After `create_worktree()`: Call `activate_chunk_in_worktree(worktree_path, chunk)`
2. Store returned displaced chunk name in `work_unit.displaced_chunk`
3. Update the work unit in the database

This ensures exactly one IMPLEMENTING chunk exists in the worktree when the agent runs.

Location: src/orchestrator/scheduler.py#Scheduler::_run_work_unit

### Step 5: Implement displaced chunk restoration in _advance_phase

Modify `_advance_phase` to restore displaced chunks before merge:

1. In the `next_phase is None` branch (work unit completed all phases)
2. Before calling `merge_to_base()`: Check if `work_unit.displaced_chunk` is set
3. If so: Use `update_frontmatter_field` to restore it to IMPLEMENTING in the worktree
4. This ensures the merge doesn't change the status of the user's manually-active chunk

Location: src/orchestrator/scheduler.py#Scheduler::_advance_phase

### Step 6: Write tests for chunk activation and displacement

Test the displaced chunk workflow:

1. Test: Worktree with existing IMPLEMENTING chunk gets it displaced
2. Test: Displaced chunk is restored before merge
3. Test: No displacement when no existing IMPLEMENTING chunk
4. Test: Correct chunk is IMPLEMENTING after activation

Location: tests/test_orchestrator_scheduler.py

### Step 7: Refactor verify_chunk_active_status to use Chunks class

Replace the duplicated frontmatter parsing in `verify_chunk_active_status` with `Chunks` class:

```python
def verify_chunk_active_status(worktree_path: Path, chunk: str) -> VerificationResult:
    chunks = Chunks(worktree_path)
    frontmatter = chunks.parse_chunk_frontmatter(chunk)
    if frontmatter is None:
        return VerificationResult(status=VerificationStatus.ERROR, error="...")
    # Map frontmatter.status to VerificationStatus
```

This removes the regex-based YAML parsing and uses the established pattern.

Location: src/orchestrator/scheduler.py

### Step 8: Refactor get_chunk_status in api.py to use Chunks class

Replace the duplicated frontmatter parsing in `get_chunk_status` with `Chunks` class:

```python
def get_chunk_status(goal_path: Path) -> Optional[str]:
    # Derive project_dir and chunk_name from goal_path
    chunks = Chunks(project_dir)
    frontmatter = chunks.parse_chunk_frontmatter(chunk_name)
    return frontmatter.status.value if frontmatter else None
```

Location: src/orchestrator/api.py

### Step 9: Write integration test for full inject workflow

Test the complete flow:

1. Create a FUTURE chunk in a test worktree
2. Call `activate_chunk_in_worktree`
3. Verify `ve chunk list --latest` returns the correct chunk
4. Verify the chunk ends up IMPLEMENTING in the worktree

This validates that the fix resolves the original problem from the GOAL.md.

Location: tests/test_orchestrator_scheduler.py

## Dependencies

- **orch_scheduling chunk**: Provides the scheduler infrastructure. Already ACTIVE.
- **chunks.py module**: Provides `Chunks` class with `get_current_chunk()` and `activate_chunk()`.
- **task_utils.py module**: Provides `update_frontmatter_field()` for status changes.

## Risks and Open Questions

1. **Race condition with manual chunk activation**: If the operator manually runs `ve chunk activate` on the same chunk while the orchestrator is setting up, there could be a conflict. Mitigation: The orchestrator operates in an isolated worktree, so the main repo state is unaffected until merge.

2. **Worktree may not have latest chunk data**: If the user creates a new chunk after the orchestrator starts but before worktree creation, that chunk won't be in the worktree's `docs/chunks/`. However, since we only inject existing chunks, this shouldn't be an issue - the chunk must exist before `ve orch inject` is called.

3. **activate_chunk guard behavior**: `Chunks.activate_chunk()` raises if another chunk is already IMPLEMENTING. We need to displace the existing chunk BEFORE calling activate, not after. The helper handles this ordering.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->