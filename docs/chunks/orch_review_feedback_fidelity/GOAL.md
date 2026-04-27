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

The orchestrator's review→implement feedback loop reliably communicates ALL reviewer feedback items to the implementer agent and requires them to be addressed.

When a reviewer returns FEEDBACK, the orchestrator writes the reviewer's specific issues to `REVIEW_FEEDBACK.md` in the chunk directory. On re-entry to IMPLEMENT, the implementer reads `REVIEW_FEEDBACK.md`, addresses every item (fix, defer with reason, or dispute with evidence), and deletes the file to signal completion. The code already exists in the worktree — the implementer fixes targeted issues rather than re-implementing from scratch.

Before re-entering REVIEW, the scheduler validates that `REVIEW_FEEDBACK.md` was deleted; if it still exists, the chunk is routed back to IMPLEMENT with an explicit instruction to address every remaining item. This ensures items only identified by the reviewer (deviations doc, tick marks, test labels, naming conventions) are always addressed rather than being silently dropped on re-implementation.

## Success Criteria

- Implementer agent receives the full review decision file content, not a summary
- Implementer's prompt explicitly requires addressing ALL feedback items
- Each feedback item must be acknowledged (fixed, deferred with reason, or disputed with evidence)
- Unaddressed items cause the implementer to fail validation before submitting for re-review
- Tests verify: multi-item feedback where all items are addressed, not just functional ones

