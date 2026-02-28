---
decision: APPROVE
summary: All success criteria satisfied - Scenarios F and G added with comprehensive symptoms, diagnosis, and resolution steps; warning box distinguishes status DONE vs delete; template renders correctly; existing scenarios A-E unchanged.
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: Scenario F added to Phase 2 of the orchestrator-investigate template with: symptoms, diagnosis, diagnostic steps (verify branch has unmerged commits, check what's on main), critical warning about delete, and full resolution workflow (merge → resolve conflicts → set IMPLEMENTING → chunk-complete → commit)

- **Status**: satisfied
- **Evidence**: Scenario F added at lines 137-161 of template with: symptoms (git log "merge illusion", git diff shows implementation changes, GOAL.md/PLAN.md on main but not impl code, work unit shows merged/DONE incorrectly), diagnosis explaining FUTURE chunk docs committed to main while impl lives on branch, and diagnostic steps (`git log --oneline orch/$ARGUMENTS ^main`, `git diff --name-status main..orch/$ARGUMENTS`, `git show main:docs/chunks/$ARGUMENTS/GOAL.md`). Resolution F at lines 299-330 includes: critical warning about delete, step-by-step recovery (verify branch → merge → resolve conflicts → reset to IMPLEMENTING → run chunk-complete → commit → cleanup with `git branch -d` and `status DONE`).

### Criterion 2: Scenario G added with: symptoms (multiple NEEDS_ATTENTION with same error), diagnosis, diagnostic steps (compare attention_reasons, check orchestrator.log), and resolution (fix code → commit → restart → batch retry with state reset)

- **Status**: satisfied
- **Evidence**: Scenario G added at lines 163-188 of template with: symptoms (multiple chunks in NEEDS_ATTENTION with same `attention_reason`, errors reference VE code paths, pattern of all chunks at phase X failing identically), diagnosis explaining this is a VE/orchestrator code bug. Diagnostic steps include `ve orch status`, `ve orch attention list`, `grep` for errors/exceptions/traceback in orchestrator.log, and grep for VE code paths. Resolution G at lines 332-357 provides: identify bug → fix VE code → commit → stop/restart orchestrator → batch retry via `ve orch work-unit status <chunk> READY` for each → verify with `ve orch status`. Includes notes about not using delete and future retry-all command.

### Criterion 3: A warning box or note added to the Resolution section distinguishing `work-unit status DONE` from `work-unit delete` and when to use each

- **Status**: satisfied
- **Evidence**: Warning box added at lines 194-200 of template, at the beginning of Phase 3: Resolution section before Resolution A. Uses the ⚠️ emoji and **CRITICAL** heading. Clearly distinguishes: `status DONE` marks complete but **preserves the branch** (use after manual merge), while `delete` removes work unit AND **force-deletes the branch** (uses `git branch -D`). Includes "When in doubt, use `status DONE`" guidance and notes that `git branch -d` will warn about unmerged commits.

### Criterion 4: Template re-rendered via `ve init` and the rendered command file is updated

- **Status**: satisfied
- **Evidence**: Git diff shows `.claude/commands/orchestrator-investigate.md` is modified vs main. Running `ve init` confirms template renders without error. The rendered file at `.claude/commands/orchestrator-investigate.md` contains all the new content including Scenarios F and G, Resolution F and G, and the warning box. File is committed on branch with commit message "feat: add scenarios F and G to orchestrator-investigate skill".

### Criterion 5: Existing scenarios A-E are unchanged

- **Status**: satisfied
- **Evidence**: Git diff of the template file shows only additions (lines 137-200 for Phase 2 additions, lines 289-357 for Phase 3 additions). Comparing the original Scenarios A-E (lines 95-134 in main) with the current version shows identical text. The diff shows clean insertions after Scenario E and after Resolution E, with no modifications to existing scenario content.
