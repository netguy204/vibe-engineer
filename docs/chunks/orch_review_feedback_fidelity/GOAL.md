---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/agent.py
- src/orchestrator/review_parsing.py
- src/orchestrator/scheduler.py
- src/templates/commands/chunk-implement.md.jinja2
- tests/test_orchestrator_feedback_injection.py
- tests/test_orchestrator_review_parsing.py
- tests/test_orchestrator_review_routing.py
code_references:
- ref: src/orchestrator/agent.py#AgentRunner::run_phase
  implements: "Injects REVIEW_FEEDBACK.md content into the implementer prompt when re-implementing after FEEDBACK"
- ref: src/orchestrator/review_parsing.py#validate_feedback_addressed
  implements: "Checks whether implementer addressed review feedback by verifying REVIEW_FEEDBACK.md deletion"
- ref: src/orchestrator/scheduler.py#Scheduler::_run_work_unit
  implements: "Pre-review validation that routes back to IMPLEMENT if REVIEW_FEEDBACK.md still exists"
- ref: src/templates/commands/chunk-implement.md.jinja2
  implements: "Template instructions for implementer to read, address, and delete REVIEW_FEEDBACK.md"
narrative: null
investigation: null
subsystems:
- subsystem_id: "orchestrator"
  relationship: implements
- subsystem_id: "template_system"
  relationship: uses
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- entity_consolidate_existing
---

# Chunk Goal

## Minor Goal

Fix the orchestrator's review→implement feedback loop so that ALL reviewer feedback items are reliably communicated to and addressed by the implementer agent.

**Root cause confirmed**: The orchestrator does NOT pass review feedback to the implementer at all. When a reviewer gives FEEDBACK, the orchestrator re-runs the entire implementation phase from scratch with the original implementation prompt. The implementer never sees the reviewer's specific feedback items.

Items that happen to be in the original plan get "fixed" by coincidence on re-implementation. Items only identified by the reviewer (deviations doc, tick marks, test labels) never get fixed because the feedback is never injected into the implementer's context. Each unnecessary full re-implementation also costs ~$0.25 in inference vs ~$0.05 for a targeted fix prompt.

Fix should:
1. When review returns FEEDBACK, read the review decision file (e.g., `docs/reviewers/baseline/decisions/chunk_name_N.md`)
2. Extract the specific issues list
3. Send the implementer a targeted feedback prompt (NOT the full implementation prompt) listing the specific issues to address
4. The code already exists in the worktree — the implementer should fix, not re-implement
5. Add a feedback checklist mechanism where each issue must be explicitly acknowledged

Reported by a design steward after manually fixing multiple escalated chunks. Root cause confirmed by examining orchestrator logs.

## Success Criteria

- Implementer agent receives the full review decision file content, not a summary
- Implementer's prompt explicitly requires addressing ALL feedback items
- Each feedback item must be acknowledged (fixed, deferred with reason, or disputed with evidence)
- Unaddressed items cause the implementer to fail validation before submitting for re-review
- Tests verify: multi-item feedback where all items are addressed, not just functional ones

