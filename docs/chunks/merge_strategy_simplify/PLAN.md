<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk replaces the orchestrator's complex plumbing-based merge strategy with a simpler branch-aware approach that uses native `git merge` when appropriate.

**Current problem:** The existing code uses `git merge-tree`/`commit-tree`/`update-ref` plumbing commands for all merges, then attempts to sync the working tree with `reset --mixed` + `checkout -- .`. This leaves the working tree in a broken state when the user is on the target branch: git log shows the merge, git diff is clean, but git status shows all merged files as modified.

**New strategy:**
1. **User on target branch** → Use `git merge {chunk_branch}`. Git handles index + working tree + ref atomically. Git merge handles dirty working trees correctly (merges non-conflicting files, refuses if uncommitted changes conflict).
2. **User on different branch** → Use the existing `update-ref` plumbing path (no working tree sync needed).

The key insight is that `git merge` does exactly what we need when the user is on the target branch—it's atomic and correct. The plumbing approach only makes sense when we can't checkout the target branch. A clean working tree is NOT required; git merge handles dirty trees natively.

**Testing approach:** Following TESTING_PHILOSOPHY.md, we'll write tests that verify semantic behavior:
- After merge while on target branch, working tree matches the merged state
- After merge while on different branch, target ref is updated but working tree unchanged
- Conflicts during merge trigger abort and route to REBASE phase

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS the orchestrator subsystem by modifying merge strategy. The subsystem is DOCUMENTED status, so no deviations will be addressed beyond this chunk's scope.

## Sequence

### Step 1: Add helper function to detect current branch state

Add two helper functions to `src/orchestrator/merge.py`:
- `is_on_branch(branch: str, repo_dir: Path) -> bool` - Returns True if the current HEAD is on the given branch
- `has_clean_working_tree(repo_dir: Path) -> bool` - Returns True if working tree is clean (no staged or unstaged changes to tracked files)

Location: `src/orchestrator/merge.py`

### Step 2: Add native merge function

Add `merge_native(source_branch: str, target_branch: str, repo_dir: Path) -> None`:
- Runs `git merge {source_branch}` with no-edit flag
- On success, returns normally
- On conflict (non-zero exit with CONFLICT in output), runs `git merge --abort` and raises `WorktreeError` with merge conflict message

This function assumes the caller has verified we're on the target branch.

Location: `src/orchestrator/merge.py`

### Step 3: Refactor merge_without_checkout to use branch-aware strategy

Modify `merge_without_checkout()` to:
1. Check if source is already an ancestor of target (already merged) - no-op
2. Check if user is on target branch:
   - If yes: call `merge_native()` (git merge handles dirty trees correctly)
   - If no (on different branch): use existing plumbing approach
3. Delete the call to `update_working_tree_if_on_branch()` from the plumbing paths

The fast-forward case should also use `merge_native()` when on target branch (git merge handles fast-forward correctly).

Location: `src/orchestrator/merge.py`

### Step 4: Delete update_working_tree_if_on_branch function

Remove the `update_working_tree_if_on_branch()` function entirely. It is no longer needed because:
- When on target branch with clean tree, `git merge` handles working tree updates atomically
- When on different branch, no working tree update is needed

Also remove it from any call sites in `merge_via_index()`.

Location: `src/orchestrator/merge.py`

### Step 5: Write tests for new merge strategy

Add/update tests in `tests/test_orchestrator_merge.py`:

**Test 1: `test_merge_on_target_branch_clean_tree_uses_native_merge`**
- Given: user on target branch, clean working tree
- When: merge_without_checkout called
- Then: working tree, index, and ref all consistent; new files appear in working tree

**Test 2: `test_merge_on_target_branch_conflict_aborts_and_raises`**
- Given: user on target branch, clean tree, conflicting changes
- When: merge_without_checkout called
- Then: WorktreeError raised with "Merge conflict", working tree is clean (merge aborted)

**Test 3: `test_merge_on_different_branch_updates_ref_only`**
- Given: user on different branch than target
- When: merge_without_checkout called
- Then: target branch ref updated, user's working tree unchanged

**Test 4: `test_merge_on_target_branch_dirty_tree_uses_plumbing`**
- Given: user on target branch, uncommitted changes
- When: merge_without_checkout called
- Then: ref updated via plumbing, uncommitted changes preserved

Location: `tests/test_orchestrator_merge.py`

### Step 6: Update backreferences

Update chunk backreference comments in `src/orchestrator/merge.py` to reference this chunk for the new merge strategy.

### Step 7: Run full test suite and fix any regressions

Run `uv run pytest tests/` to ensure all existing tests pass. Fix any regressions introduced by the changes.

## Risks and Open Questions

- **Dirty working tree handling:** When the user is on the target branch but has uncommitted changes, we fall back to the plumbing approach. This preserves their changes but leaves the working tree behind the branch tip (same as current behavior with `merge_safety` chunk's early return). This is acceptable as documented behavior.

- **Git version compatibility:** `git merge --no-edit` and `git merge --abort` are widely supported. No version concerns expected.

- **Multi-repo case:** The same strategy applies per-repo in `_merge_to_base_multi_repo`. Each repo's merge uses the same logic independently.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->