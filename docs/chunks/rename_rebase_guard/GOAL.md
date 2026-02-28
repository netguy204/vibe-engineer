---
status: ACTIVE
ticket: null
parent_chunk: orch_rename_propagation
code_paths:
- src/orchestrator/scheduler.py
- tests/test_orch_rename_propagation.py
code_references:
  - ref: src/orchestrator/scheduler.py#Scheduler::_detect_rename
    implements: "Phase-aware rename detection that only activates during GOAL/PLAN phases, preventing false positives during post-PLAN phases"
  - ref: src/orchestrator/scheduler.py#Scheduler::_handle_agent_result
    implements: "Phase-aware ambiguity handling that only checks for 'chunk disappeared' errors during GOAL/PLAN phases"
  - ref: tests/test_orch_rename_propagation.py#TestRenameDetection::test_detect_rename_post_complete_rebase_no_false_positive
    implements: "Unit test for post-COMPLETE REBASE no false positive scenario"
  - ref: tests/test_orch_rename_propagation.py#TestRenameDetection::test_detect_rename_rebase_merging_main_no_false_positive
    implements: "Unit test for rebase merging main with ACTIVE chunks scenario"
  - ref: tests/test_orch_rename_propagation.py#TestRenameDetection::test_detect_rename_only_during_plan_phase
    implements: "Unit test verifying rename detection is phase-guarded"
  - ref: tests/test_orch_rename_propagation.py#TestRenameDetectionIntegration
    implements: "Integration tests for rename detection across phase transitions"
narrative: null
investigation: null
subsystems:
- subsystem_id: orchestrator
  relationship: implements
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- backref_language_agnostic
- integrity_deprecated_removal
- merge_safety
- orch_investigate_scenarios
- orch_retry_command
- orch_safe_branch_delete
---

# Chunk Goal

## Minor Goal

The orchestrator's `_detect_rename()` method produces false positive rename
detections. It should only consider IMPLEMENTING chunks, but something in the
detection path allows non-IMPLEMENTING chunks to influence the result.

**Observed failure:** `backref_language_agnostic` completed IMPLEMENT, then
during REBASE merged main (which contained the completed `merge_safety` chunk).
Rebase only retrieves chunks in ACTIVE or FUTURE states from main. Despite this,
the rename detection concluded `backref_language_agnostic` had been renamed to
`merge_safety`. If detection truly only considered IMPLEMENTING chunks, a rebase
could never produce a false positive — no new IMPLEMENTING chunks appear via
rebase.

**Additional scenario:** When a merge conflict occurs after COMPLETE, the chunk
returns to the REBASE step. At that point the COMPLETE phase has already changed
the chunk's status to ACTIVE. The work unit's own chunk is now ACTIVE, not
IMPLEMENTING, so `_detect_rename` sees it as "disappeared" even though it's
still present — just in a different status.

**Fix:** Ensure `_detect_rename()` strictly only considers IMPLEMENTING chunks
when computing the baseline-to-current set difference. The work unit's own chunk
identity (`work_unit.chunk`) must be used directly — not inferred from the
IMPLEMENTING set — so that the detection still works after COMPLETE has changed
the chunk to ACTIVE. The check should be: "is there an IMPLEMENTING chunk with
a different name than `work_unit.chunk`?" rather than "did my chunk disappear
from the IMPLEMENTING set?"

## Success Criteria

- `_detect_rename()` strictly considers only IMPLEMENTING chunks — chunks in
  ACTIVE, FUTURE, or any other state are excluded from both the baseline
  comparison and the current set
- The work unit's chunk identity is tracked via `work_unit.chunk`, not by
  scanning for IMPLEMENTING chunks — so detection still works correctly after
  COMPLETE has changed the chunk's status to ACTIVE
- A rename is detected only when a new IMPLEMENTING chunk appears that wasn't
  in the baseline, not when the work unit's own chunk changes status
- After a rebase that merges main into the worktree, no false rename is detected
  (since main only contains ACTIVE/FUTURE chunks)
- After a post-COMPLETE rebase (merge conflict retry), no false rename is
  detected (the chunk is now ACTIVE but `work_unit.chunk` still knows its name)
- A test verifies both scenarios
- The existing rename detection tests continue to pass

## Relationship to Parent

The parent chunk (`orch_rename_propagation`) introduced `_detect_rename()` with
the intent of only considering IMPLEMENTING chunks. This chunk fixes a defect
where non-IMPLEMENTING chunks leak into the detection, causing false positives
after rebase.