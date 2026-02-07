---
description: Merge trunk into worktree and resolve conflicts
---


<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

Run `ve init` to regenerate.
-->

## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.

## Purpose

This phase integrates the current trunk (main branch) into the worktree branch
before review. This ensures the REVIEW phase sees code that has already been
merged with any concurrent changes from other parallel chunks.

## Instructions

### 1. Commit Any Uncommitted Work

First, check for and commit any uncommitted changes from the IMPLEMENT phase:

```bash
git status
```

If there are uncommitted changes:
1. Stage all changes: `git add -A`
2. Commit with a descriptive message summarizing what was implemented

### 2. Merge Current Trunk

Merge the current main branch into this worktree branch:

```bash
git merge main
```

Note: Worktrees share the same git object store as the main repo, so `main`
always reflects the latest local state. Do NOT use `origin/main` — in
orchestrator mode, other chunks merge to local `main` without pushing, so
`origin/main` will be stale.

### 3. Handle Merge Conflicts (If Any)

If conflicts arise:

1. Identify conflicting files from the merge output
2. Read the chunk's GOAL.md to understand what this chunk is trying to accomplish
3. For each conflict:
   - **Keep chunk changes** where they implement the goal
   - **Accept trunk changes** for unrelated code modifications
   - **Preserve both** when changes are complementary
4. After resolving all conflicts, stage and commit:
   ```bash
   git add -A
   git commit -m "Merge main into chunk branch, resolve conflicts"
   ```

### 4. Run Tests

Verify the integrated result passes tests:

```bash
uv run pytest tests/
```

If tests fail:
1. Analyze the failure - is it due to the merge or a pre-existing issue?
2. If the failure is related to this chunk's changes, fix the issue
3. If the failure is due to trunk changes, report as NEEDS_ATTENTION

### 5. Report Outcome

**On Success (clean merge or resolved conflicts, tests pass):**
- The phase will automatically advance to REVIEW

**On Failure (unresolvable conflicts or test failures):**
- Report clearly which files have unresolvable conflicts
- Or report which tests are failing and why
- The work unit will be marked NEEDS_ATTENTION for operator help

## Important Notes

- Do NOT skip the test run - we need to verify the integrated code works
- Do NOT modify implementation code beyond conflict resolution
- Do NOT change the chunk's status or advance to the next phase manually
- If you cannot resolve a conflict because you're unsure of intent, mark as NEEDS_ATTENTION