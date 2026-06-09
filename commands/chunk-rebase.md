---
name: chunk-rebase
description: Merge trunk into a chunk worktree branch and resolve conflicts before review. Use when a worktree branch is behind main, when the operator asks to rebase or merge trunk into a chunk branch, or as the REBASE phase of orchestrated chunk execution.
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(git status:*), Bash(git merge:*), Bash(git add:*), Bash(git commit:*), Bash(uv run pytest:*)
---

<!-- Chunk: docs/chunks/plugin_core_commands - Static plugin port of chunk-rebase -->

## Context

- ve CLI: !`ve --help >/dev/null 2>&1 && echo "installed" || echo "(ve CLI not found)"`
- Task workspace: !`cat .ve-task.yaml 2>/dev/null || cat ../.ve-task.yaml 2>/dev/null || echo "(not a task workspace)"`
- Project config: !`cat .ve-config.yaml 2>/dev/null || echo "(no .ve-config.yaml — defaults apply)"`

## Runtime context

Interpret the context above before following the instructions:

- **ve CLI**: The `ve` command is an installed CLI tool, not a file in the
  repository. Do not search for it — run it directly via Bash. If the
  context shows "(ve CLI not found)", tell the operator that the
  vibe-engineer plugin requires the separately installed `ve` CLI, suggest
  `uv tool install vibe-engineer` (or `pip install vibe-engineer`), and
  stop.
- **Uninitialized project**: If `ve` is installed but commands fail because
  there is no `docs/chunks/` structure, tell the operator to run `ve init`
  in the project root, then stop.
- **Task workspace**: If the Task workspace context shows YAML (keys
  `external_artifact_repo` and `projects`) instead of "(not a task
  workspace)", you are in a multi-project task workspace. Artifacts
  (chunks, narratives, investigations) live in the external artifact repo
  named by `external_artifact_repo`; code changes happen in the
  participating `projects`. Command-specific task guidance appears below.
- **Project config**: `.ve-config.yaml` holds project configuration.
  Known keys: `cluster_subsystem_threshold` (default 5 — the cluster size
  at which to suggest subsystem documentation). When the context shows
  "(no .ve-config.yaml — defaults apply)", use the defaults.

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
