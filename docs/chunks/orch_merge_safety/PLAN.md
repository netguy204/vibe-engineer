<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The core problem is that `merge_to_base()` performs `git checkout` in the main repository (lines 730-739 in worktree.py), which disrupts the user's working tree during parallel orchestrator execution. Additionally, `_get_repo_current_branch()` is called at merge time (line 791) rather than at worktree creation time, introducing a race condition.

**Strategy**: Use worktree-based merge operations that never touch the main repository's checked-out branch:

1. **Eliminate `git checkout` from merge**: Instead of checking out the base branch in the main repo and then merging, we can perform the merge operation from within a temporary context or use `git fetch` + ref manipulation to merge without checkout. The cleanest approach is to use `git merge-base` and `git merge-tree` or to perform the merge in the worktree itself before merging to base via `git push` to the local branch.

   **Chosen approach**: Merge in the worktree by fetching the base branch into the worktree, merging locally, then using `git push . HEAD:base_branch` to update the base branch ref without checkout. This leverages Git's ability to push to a local ref.

2. **Capture base branch at worktree creation time**: Store the base branch in a metadata file (`.ve/chunks/<chunk>/base_branch`) when creating the worktree. Read this during merge instead of querying the current branch.

3. **Lock worktrees against prune**: Call `git worktree lock` after creating worktrees and `git worktree unlock` before removal. This prevents `git worktree prune` from removing active worktrees.

Following TDD per TESTING_PHILOSOPHY.md, tests will be written first for each behavioral change.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS improvements to the WorktreeManager component within the orchestrator subsystem, specifically addressing worktree lifecycle management and merge safety. The invariant "Worktrees are isolated execution environments" is being strengthened by this work.

## Sequence

### Step 1: Add tests for base branch capture at creation time

Write failing tests that verify:
- A file `.ve/chunks/<chunk>/base_branch` is created when a worktree is created
- The base branch file contains the branch name at creation time
- `merge_to_base()` reads from this file instead of querying `_get_repo_current_branch()`
- If the main repo switches branches after worktree creation, merge still targets the original base branch

Location: `tests/test_orchestrator_worktree.py`

### Step 2: Implement base branch persistence

Add methods to store and retrieve the base branch:
- `_save_base_branch(chunk: str, branch: str, repo_dir: Optional[Path] = None)` - writes to `.ve/chunks/<chunk>/base_branch` (or `.ve/chunks/<chunk>/base_branches/<repo_name>` for multi-repo)
- `_load_base_branch(chunk: str, repo_dir: Optional[Path] = None) -> str` - reads from the file
- Modify `_create_single_repo_worktree()` to call `_save_base_branch()` after determining the base branch
- Modify `_create_task_context_worktrees()` to save per-repo base branches

Location: `src/orchestrator/worktree.py`

### Step 3: Add tests for checkout-free merge

Write failing tests that verify:
- `merge_to_base()` does NOT change the checked-out branch in the main repository
- A file can be modified in the main repo's working tree before merge, and it remains after merge
- Merge conflicts are still detected and reported with WorktreeError

Location: `tests/test_orchestrator_worktree.py`

### Step 4: Implement checkout-free merge for single-repo mode

Replace the current `_merge_to_base_single_repo()` implementation:
1. Read the base branch from the persisted file
2. In the worktree: `git fetch origin base_branch` (or `git fetch .. refs/heads/base_branch` for local fetch)
3. In the worktree: `git merge FETCH_HEAD --no-edit` to merge base into worktree
4. If merge succeeds, push back: `git push .. HEAD:refs/heads/base_branch`
5. No `git checkout` needed in the main repository

Alternative if the above is complex: Use `git merge-base` + `git merge-tree` + `git commit-tree` + `git update-ref` to create the merge commit without checkout.

**Chosen approach after research**: The simplest approach that works is to do the merge in the worktree and then use `git push . worktree_branch:base_branch` from the main repo, or to use `git worktree`-relative refs. Actually, the cleanest is:
1. From main repo: `git merge --no-checkout orch/<chunk>` - but this still requires being on base branch
2. Better: From worktree, merge base into worktree, resolve there, then fast-forward base to worktree

Final approach: Perform all merge work in the worktree:
1. Fetch base branch into worktree: `git fetch origin base_branch`
2. Merge in worktree: first merge base into worktree branch (handles any upstream changes)
3. Then from main repo, use `git branch -f base_branch orch/<chunk>` to fast-forward base to the worktree branch (only works if worktree already includes all base commits)
4. Or use `git push . orch/<chunk>:base_branch` from main repo

Location: `src/orchestrator/worktree.py`

### Step 5: Implement checkout-free merge for multi-repo mode

Apply the same pattern to `_merge_to_base_multi_repo()`:
1. Read per-repo base branches from persisted files
2. For each repo, perform the merge without checkout in that repo's main directory
3. Use the same push-based or branch-update approach

Location: `src/orchestrator/worktree.py`

### Step 6: Add tests for worktree locking

Write failing tests that verify:
- After `create_worktree()`, `git worktree list --porcelain` shows the worktree as locked
- `git worktree prune` does not remove a locked worktree
- `remove_worktree()` unlocks before removing
- `unlock` doesn't error if worktree wasn't locked (idempotent)

Location: `tests/test_orchestrator_worktree.py`

### Step 7: Implement worktree locking

Add locking calls:
- After `git worktree add` succeeds: `git worktree lock <path> --reason "orchestrator active"`
- Before `git worktree remove`: `git worktree unlock <path>` (ignore errors if already unlocked)
- Apply to both single-repo and multi-repo modes

Location: `src/orchestrator/worktree.py`

### Step 8: Update GOAL.md code_paths

Add the touched files to the chunk's frontmatter:
- `src/orchestrator/worktree.py`
- `tests/test_orchestrator_worktree.py`

Location: `docs/chunks/orch_merge_safety/GOAL.md`

### Step 9: Run full test suite and fix any regressions

Verify all existing tests still pass. The merge behavior is tested in `TestMergeToBase` class and must continue to work correctly.

Command: `uv run pytest tests/test_orchestrator_worktree.py -v`

---

**BACKREFERENCE COMMENTS**

When implementing, add backreference comments:
- `# Chunk: docs/chunks/orch_merge_safety - Merge safety without git checkout`

At the method level for `_merge_to_base_single_repo`, `_merge_to_base_multi_repo`, `_save_base_branch`, `_load_base_branch`.

## Dependencies

None. This chunk modifies existing code with no new external dependencies.

## Risks and Open Questions

1. **Git version compatibility**: `git worktree lock` was added in Git 2.10 (2016). This should be fine for modern systems, but if we need to support older Git versions, we may need to skip locking gracefully.

2. **Merge strategy complexity**: The checkout-free merge is more complex than the current implementation. If it proves too fragile, we could fall back to a simpler approach: creating a temporary bare clone for merge operations, though this has performance implications.

3. **Fast-forward assumption**: The planned approach assumes we can fast-forward the base branch to include the worktree changes. If base has advanced (someone else pushed), we need a proper merge. The worktree-based merge handles this by first merging base into worktree, then updating base to point to the merged result.

4. **Reflog safety**: Using `git branch -f` or `git push . src:dst` updates refs directly. This should still create reflog entries, but we should verify reflog preservation for recovery scenarios.

5. **Multi-repo atomicity**: If merge succeeds in repo A but fails in repo B, we currently roll back A. The checkout-free approach should maintain this rollback capability.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->