---
description: Investigate and resolve a stuck orchestrator work unit.
---


<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

Run `ve init` to regenerate.
-->

## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.

## Instructions

This command investigates why an orchestrator work unit is stuck (typically in
NEEDS_ATTENTION status) and guides you through resolution.

**Chunk to investigate:** `$ARGUMENTS`

If no chunk name is provided, first run `ve orch status` to identify
chunks needing attention.

Follow these phases systematically. Do not skip phases or propose fixes without
completing the investigation.

---

## Phase 1: Gather Evidence

### 1.1 Check orchestrator status

```bash
ve orch status
```

Confirm the chunk is in NEEDS_ATTENTION (or unexpected state). Note the work
unit counts.

### 1.2 Check work unit details

```bash
ve orch work-unit show $ARGUMENTS
```

Note the `status`, `phase`, `attention_reason`, and `displaced_chunk` fields.

### 1.3 Check log directory structure

```bash
ls -la .ve/chunks/$ARGUMENTS/log/
```

Determine current phase by which logs exist:
- `plan.txt` only → PLAN phase
- `plan.txt` + `implement.txt` → IMPLEMENT phase
- All three files → COMPLETE phase

### 1.4 Check worktree state

```bash
# Does worktree exist?
ls -la .ve/chunks/$ARGUMENTS/worktree 2>/dev/null && echo "worktree exists" || echo "no worktree"

# Check git worktree list
git worktree list | grep $ARGUMENTS

# Check if branch exists
git branch -a | grep $ARGUMENTS
```

### 1.5 Check orchestrator log for errors

```bash
grep -i "$ARGUMENTS\|error\|failed\|merge" .ve/orchestrator.log | tail -50
```

Look for error messages that explain why the chunk is stuck.

### 1.6 Check end of agent log

If logs exist, check the end of the most recent phase log:

```bash
tail -c 20000 .ve/chunks/$ARGUMENTS/log/complete.txt 2>/dev/null || \
tail -c 20000 .ve/chunks/$ARGUMENTS/log/implement.txt 2>/dev/null || \
tail -c 20000 .ve/chunks/$ARGUMENTS/log/plan.txt 2>/dev/null
```

Look for `ResultMessage` at the end - `subtype='success'` means the agent
completed, `subtype='error'` means it failed.

---

## Phase 2: Diagnose Root Cause

Based on evidence gathered, identify which scenario applies:

### Scenario A: Merge failed due to uncommitted changes

**Symptoms:**
- Log shows: `error: Your local changes to the following files would be overwritten by merge`
- Agent completed successfully (ResultMessage subtype='success')
- Branch exists but wasn't merged

**Diagnosis:** Main repo had uncommitted changes when orchestrator tried to merge.

### Scenario B: Merge failed due to conflicts

**Symptoms:**
- Log shows: `CONFLICT` or `Automatic merge failed`
- Branch exists, worktree may be cleaned up

**Diagnosis:** Branch and main diverged with conflicting changes.

### Scenario C: Agent failed during execution

**Symptoms:**
- ResultMessage shows `subtype='error'` or no ResultMessage at end
- Phase log ends with error output

**Diagnosis:** Agent encountered an error during the phase.

### Scenario D: Chunk activation failed

**Symptoms:**
- Log shows: `Chunk '<name>' not found in worktree`
- Happens early in phase execution

**Diagnosis:** Worktree was created but chunk docs weren't present (race condition
or branch issue).

### Scenario E: Worktree corruption

**Symptoms:**
- Worktree directory exists but git operations fail
- `git worktree list` shows prunable entries

**Diagnosis:** Git worktree is in inconsistent state.

### Scenario F: Implementation on branch, docs on main (partial merge)

**Symptoms:**
- `git log` shows commits mentioning the chunk on main (creating a "merge illusion")
- `git diff main..orch/$ARGUMENTS` shows implementation changes that aren't on main
- Main has GOAL.md/PLAN.md for the chunk but not implementation code
- Work unit may show as merged/DONE when implementation code is only on branch

**Diagnosis:** The FUTURE chunk's documentation (GOAL.md, PLAN.md) was committed to main
via the initial chunk-create commit. The orchestrator ran PLAN/IMPLEMENT in a worktree,
but a later phase (REVIEW or COMPLETE) failed. This leaves implementation code on the
`orch/` branch while main only has the docs.

**Diagnostic steps:**

```bash
# Check for unmerged implementation commits on the branch
git log --oneline orch/$ARGUMENTS ^main

# See which files exist on branch but not main
git diff --name-status main..orch/$ARGUMENTS

# Verify GOAL.md exists on main but implementation doesn't
git show main:docs/chunks/$ARGUMENTS/GOAL.md >/dev/null 2>&1 && echo "GOAL.md on main"
```

### Scenario G: Systematic code bug affecting all chunks in same phase

**Symptoms:**
- Multiple chunks in NEEDS_ATTENTION with the same or similar `attention_reason`
- Errors reference VE code (`src/orchestrator/*`, `src/ve.py`) rather than chunk content
- Pattern: all chunks reaching phase X fail identically

**Diagnosis:** A bug in VE/orchestrator code (missing import, schema error, API change)
is causing every chunk that reaches a particular phase to fail. The fix is in the VE
codebase, not in any individual chunk.

**Diagnostic steps:**

```bash
# Check how many chunks are in NEEDS_ATTENTION
ve orch status

# List all work units needing attention and compare reasons
ve orch attention list

# Check orchestrator log for repeated errors
grep -i "error\|exception\|traceback" .ve/orchestrator.log | tail -50

# Look for errors referencing VE code
grep -E "src/(orchestrator|ve)" .ve/orchestrator.log | tail -20
```

---

## Phase 3: Resolution

> ⚠️ **CRITICAL: `status DONE` vs `delete`**
>
> - `ve orch work-unit status <chunk> DONE` — Marks the work unit complete but **preserves the branch**. Use this when you've manually merged the branch to main.
> - `ve orch work-unit delete <chunk>` — Removes the work unit AND **force-deletes the branch** (uses `git branch -D`). Use this ONLY when you're certain the branch has no unmerged work.
>
> **When in doubt, use `status DONE`** — you can always delete the branch later with `git branch -d` which will warn if unmerged commits exist.

Execute the resolution for the diagnosed scenario:

### Resolution A: Complete the merge manually

```bash
# Check main is clean
git status

# If main has uncommitted changes, commit or stash them first
# git stash  OR  git add . && git commit -m "..."

# Attempt merge
git merge orch/$ARGUMENTS --no-edit

# If conflicts occur, resolve them:
# 1. Edit conflicted files to resolve
# 2. git add <resolved-files>
# 3. git commit --no-edit

# Delete merged branch
git branch -d orch/$ARGUMENTS

# Update work unit to DONE
ve orch work-unit status $ARGUMENTS DONE
```

### Resolution B: Resolve conflicts and merge

```bash
# Start merge (expect conflicts)
git merge orch/$ARGUMENTS --no-edit || echo "Conflicts expected"

# List conflicted files
git diff --name-only --diff-filter=U

# For each conflicted file:
# 1. Open and resolve conflicts (look for <<<<<<< markers)
# 2. Choose appropriate resolution based on context
# 3. git add <file>

# Complete merge
git commit --no-edit

# Cleanup
git branch -d orch/$ARGUMENTS
ve orch work-unit status $ARGUMENTS DONE
```

### Resolution C: Reset and retry

If the agent failed and you want to retry:

```bash
# Reset work unit to allow retry
ve orch work-unit status $ARGUMENTS READY
```

Or if the failure is unrecoverable, mark as needing manual intervention:

```bash
# Delete work unit and handle manually
ve orch work-unit delete $ARGUMENTS
```

### Resolution D: Recreate worktree

```bash
# Remove corrupted worktree
rm -rf .ve/chunks/$ARGUMENTS/worktree
git worktree prune

# Reset to READY to trigger worktree recreation
ve orch work-unit status $ARGUMENTS READY
```

### Resolution E: Clean up corrupted worktree

```bash
# Prune worktrees
git worktree prune

# Remove directory if it exists
rm -rf .ve/chunks/$ARGUMENTS/worktree

# Check branch state
git branch -a | grep $ARGUMENTS

# If branch has useful commits, merge manually (see Resolution A)
# Otherwise, reset work unit to retry
```

### Resolution F: Merge implementation branch with partial docs on main

> ⚠️ **WARNING:** Do NOT use `work-unit delete` here — it will force-delete the branch
> with `git branch -D`, losing your implementation commits. Use `status DONE` after
> merging instead.

```bash
# 1. Verify the branch exists and has unmerged commits
git branch -a | grep $ARGUMENTS
git log --oneline orch/$ARGUMENTS ^main

# 2. Merge the implementation branch to main
git merge orch/$ARGUMENTS --no-edit

# 3. If conflicts occur, resolve them:
#    - Edit conflicted files
#    - git add <resolved-files>
#    - git commit --no-edit

# 4. If the chunk status was wrongly set to ACTIVE, reset it
ve chunk activate $ARGUMENTS --status IMPLEMENTING

# 5. Run chunk-complete to update code_references and finalize
# (invoke /chunk-complete skill manually)

# 6. Commit the completion changes
git add docs/chunks/$ARGUMENTS && git commit -m "Complete chunk: $ARGUMENTS"

# 7. Clean up: delete the merged branch and mark work unit done
git branch -d orch/$ARGUMENTS
ve orch work-unit status $ARGUMENTS DONE
```

### Resolution G: Fix code bug and batch retry affected chunks

This resolution is for bugs in VE/orchestrator code, NOT individual chunk failures.

```bash
# 1. Identify the bug from error messages
grep -E "error|exception" .ve/orchestrator.log | tail -30

# 2. Fix the bug in the VE codebase
# (e.g., src/orchestrator/scheduler.py, src/orchestrator/phases.py)

# 3. Commit the fix
git add src/ && git commit -m "Fix: <describe the bug>"

# 4. Stop and restart the orchestrator to pick up the fix
ve orch stop
ve orch start

# 5. Batch retry all affected work units
# For each NEEDS_ATTENTION chunk, reset to READY:
ve orch attention list
# Then for each chunk listed:
ve orch work-unit status <chunk-name> READY

# 6. Verify chunks resume execution
ve orch status
```

> **Note:** This is NOT a case for `work-unit delete` — the implementation work exists
> on branches and should be retried, not discarded.
>
> If a future `ve orch retry-all` command is added, use that instead of manual iteration.

---

## Phase 4: Verify Resolution

After applying resolution:

```bash
# Check orchestrator status
ve orch status

# Verify work unit state
ve orch work-unit show $ARGUMENTS

# If merged, verify changes are on main
git log --oneline -5
```

---

## Report Summary

Present findings to the user:

| Field | Value |
|-------|-------|
| **Chunk** | `$ARGUMENTS` |
| **Root Cause** | (describe what caused the stuck state) |
| **Resolution** | (describe what was done to fix it) |
| **Current Status** | (DONE / READY for retry / Deleted) |

If the chunk was merged, confirm the implementation is now on main.