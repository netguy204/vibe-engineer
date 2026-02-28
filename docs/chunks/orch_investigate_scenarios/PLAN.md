<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a documentation-only change to the `/orchestrator-investigate` skill template. The approach:

1. **Add Scenario F** to Phase 2 covering the "partial merge illusion" where docs are on main but implementation lives on the orch branch
2. **Add Scenario G** covering systematic code bugs affecting all chunks in the same phase
3. **Add a warning box** distinguishing `work-unit status DONE` (preserves branch) from `work-unit delete` (force-deletes branch with `-D`)
4. **Re-render** via `ve init` to update the rendered command file

No tests required per TESTING_PHILOSOPHY.md — we don't test template prose content, only that templates render without error (which `ve init` validates).

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS additional operator guidance for the orchestrator subsystem's `/orchestrator-investigate` skill. The existing template patterns (Phase 1-4 structure, Scenario A-E format) will be followed exactly.

## Sequence

### Step 1: Add Scenario F to Phase 2

Add a new "Scenario F: Implementation on branch, docs on main (partial merge)" section immediately after Scenario E in Phase 2: Diagnose Root Cause.

**Content structure:**
- **Symptoms**: `git log` shows chunk commits on main but `git diff main..orch/<chunk>` shows implementation changes; main has GOAL.md/PLAN.md but not implementation code; work unit may show as merged/DONE when code is still on branch only
- **Diagnosis**: The FUTURE chunk's documentation was committed to main (via chunk-create commit), and the orchestrator ran PLAN/IMPLEMENT in a worktree. A later phase (REVIEW or COMPLETE) failed, leaving implementation code on the `orch/` branch while main only has the docs.
- **Diagnostic commands**:
  - `git log --oneline orch/<chunk> ^main` to see unmerged implementation commits
  - `git diff --name-status main..orch/<chunk>` to see files on branch but not main
  - Check if GOAL.md/PLAN.md exist on main but implementation files don't

**Location**: `src/templates/commands/orchestrator-investigate.md.jinja2`, Phase 2 section after Scenario E

### Step 2: Add Resolution F to Phase 3

Add corresponding resolution for Scenario F after Resolution E.

**Content structure:**
- **Critical warning box**: Before proceeding, warn that `work-unit delete` will force-delete the branch. Use `work-unit status DONE` instead if unsure.
- **Step-by-step recovery**:
  1. Verify branch exists: `git branch -a | grep <chunk>`
  2. Check unmerged commits: `git log --oneline orch/<chunk> ^main`
  3. Merge the branch: `git merge orch/<chunk> --no-edit` (resolve conflicts if needed)
  4. If chunk status was wrongly set to ACTIVE, revert to IMPLEMENTING: `ve chunk activate <chunk> --status IMPLEMENTING`
  5. Run chunk-complete: invoke `/chunk-complete` to populate code_references, update status, remove comment blocks
  6. Commit the completion changes
  7. Clean up: `git branch -d orch/<chunk>` and `ve orch work-unit status <chunk> DONE`

**Location**: `src/templates/commands/orchestrator-investigate.md.jinja2`, Phase 3 section after Resolution E

### Step 3: Add Scenario G to Phase 2

Add a new "Scenario G: Systematic code bug affecting all chunks in same phase" section after Scenario F.

**Content structure:**
- **Symptoms**: Multiple chunks in NEEDS_ATTENTION with the same or similar `attention_reason`; errors reference VE code (src/orchestrator/*, src/ve.py) rather than chunk content; pattern: all chunks reaching phase X fail identically
- **Diagnosis**: A bug in VE/orchestrator code (missing import, schema error, API change) is causing every chunk that reaches a particular phase to fail. The fix is in the VE codebase, not in any individual chunk.
- **Diagnostic commands**:
  - `ve orch status` to see NEEDS_ATTENTION count
  - `ve orch attention list` to compare `attention_reason` across work units
  - `grep -i "error\|exception\|traceback" .ve/orchestrator.log | tail -50`
  - Check if error references `src/orchestrator/*` or `src/ve.py`

**Location**: `src/templates/commands/orchestrator-investigate.md.jinja2`, Phase 2 section after Scenario F

### Step 4: Add Resolution G to Phase 3

Add corresponding resolution for Scenario G after Resolution F.

**Content structure:**
- **Step-by-step recovery**:
  1. Identify the code bug from the error message
  2. Fix the bug in the VE codebase (e.g., `src/orchestrator/scheduler.py`)
  3. Commit the fix
  4. Stop and restart the orchestrator: `ve orch stop && ve orch start`
  5. Batch retry all affected work units: for each NEEDS_ATTENTION chunk, run `ve orch work-unit status <chunk> READY`
  6. Verify chunks resume execution: `ve orch status`
- **Warning**: If a future `ve orch retry-all` command is added, use that instead of manual iteration
- **Note**: This is NOT a case for `work-unit delete` — the implementation work exists on branches and should be retried, not discarded

**Location**: `src/templates/commands/orchestrator-investigate.md.jinja2`, Phase 3 section after Resolution F

### Step 5: Add warning about status DONE vs delete

Add a warning box or note to the Resolution section (before Resolution A) that distinguishes the two commands:

**Content:**
> ⚠️ **CRITICAL: status DONE vs delete**
>
> - `ve orch work-unit status <chunk> DONE` — Marks the work unit complete but **preserves the branch**. Use this when you've manually merged the branch to main.
> - `ve orch work-unit delete <chunk>` — Removes the work unit AND **force-deletes the branch** (uses `git branch -D`). Use this ONLY when you're certain the branch has no unmerged work.
>
> **When in doubt, use `status DONE`** — you can always delete the branch later with `git branch -d` which will warn if unmerged commits exist.

**Location**: `src/templates/commands/orchestrator-investigate.md.jinja2`, beginning of Phase 3 section, before Resolution A

### Step 6: Re-render templates via `ve init`

Run `uv run ve init` to re-render the template and update `.claude/commands/orchestrator-investigate.md`.

Verify:
- The rendered file includes Scenarios F and G in Phase 2
- The rendered file includes Resolutions F and G in Phase 3
- The warning box appears at the beginning of Phase 3
- Existing Scenarios A-E and Resolutions A-E are unchanged

### Step 7: Update code_paths in GOAL.md

Update the `code_paths` field in the chunk's GOAL.md to reflect the files touched:
- `src/templates/commands/orchestrator-investigate.md.jinja2`

## Dependencies

None. This is a documentation-only change to an existing template file.

## Risks and Open Questions

- **Risk**: The scenarios may not cover all edge cases from the investigation. Mitigation: The investigation (docs/investigations/orch_stuck_recovery/OVERVIEW.md) thoroughly analyzed the incident; Scenarios F and G directly address the documented gaps (F4, F5).
- **Open question**: Should Scenario F reference the future `ve orch work-unit retry` command? Decision: No — that command doesn't exist yet (it's chunk `orch_retry_command`). Keep scenarios focused on currently available commands. The retry command chunk can update this documentation when it ships.

## Deviations

*To be populated during implementation.*