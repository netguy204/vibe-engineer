---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/orchestrator/models.py
  - src/orchestrator/scheduler.py
  - src/orchestrator/review_parsing.py
  - src/orchestrator/agent.py
  - src/orchestrator/state.py
  - tests/test_orchestrator_scheduler.py
code_references:
  - ref: src/orchestrator/models.py#WorkUnitPhase
    implements: "Added REVIEW enum value between IMPLEMENT and COMPLETE"
  - ref: src/orchestrator/models.py#WorkUnit::review_iterations
    implements: "Track how many IMPLEMENT → REVIEW cycles have occurred for loop detection"
  - ref: src/orchestrator/models.py#ReviewDecision
    implements: "Enum for review decisions: APPROVE, FEEDBACK, ESCALATE"
  - ref: src/orchestrator/models.py#ReviewIssue
    implements: "Structured representation of a single review issue"
  - ref: src/orchestrator/models.py#ReviewResult
    implements: "Structured output from /chunk-review skill"
  - ref: src/orchestrator/review_parsing.py#create_review_feedback_file
    implements: "Creates REVIEW_FEEDBACK.md with reviewer feedback for implementer"
  - ref: src/orchestrator/review_parsing.py#parse_review_decision
    implements: "Parse YAML decision block from /chunk-review skill output"
  - ref: src/orchestrator/review_parsing.py#load_reviewer_config
    implements: "Load reviewer config for loop detection settings"
  - ref: src/orchestrator/scheduler.py#Scheduler::_handle_review_result
    implements: "Route work unit based on review decision (APPROVE/FEEDBACK/ESCALATE)"
  - ref: src/orchestrator/scheduler.py#Scheduler::_advance_phase
    implements: "Updated phase progression map to include REVIEW between IMPLEMENT and COMPLETE"
  - ref: src/orchestrator/scheduler.py#Scheduler::_handle_agent_result
    implements: "Special handling for REVIEW phase to route to _handle_review_result"
  - ref: src/orchestrator/agent.py#PHASE_SKILL_FILES
    implements: "Added chunk-review.md as skill for REVIEW phase"
  - ref: src/orchestrator/state.py#StateStore::_migrate_v9
    implements: "Schema migration adding review_iterations column"
  - ref: tests/test_orchestrator_scheduler.py#TestReviewPhase
    implements: "Tests for REVIEW phase transitions and handling"
  - ref: tests/test_orchestrator_scheduler.py#TestReviewDecisionParsing
    implements: "Tests for parsing review decision from agent output"
  - ref: tests/test_orchestrator_scheduler.py#TestReviewFeedbackFile
    implements: "Tests for REVIEW_FEEDBACK.md file creation"
narrative: null
investigation: orchestrator_quality_assurance
subsystems:
  - subsystem_id: orchestrator
    relationship: implements
friction_entries: []
bug_type: null
depends_on:
- chunk_review_skill
created_after:
- explicit_deps_command_prompts
- chunk_list_flags
- progressive_disclosure_external
- progressive_disclosure_refactor
- progressive_disclosure_validate
---

# Chunk Goal

## Minor Goal

Add a REVIEW phase to the orchestrator scheduler between IMPLEMENT and COMPLETE. This creates a mandatory quality gate where every chunk must pass review before it can be marked complete.

The review phase invokes the `/chunk-review` skill, parses its decision, and routes accordingly: APPROVE proceeds to COMPLETE, FEEDBACK returns to IMPLEMENT with context, ESCALATE triggers NEEDS_ATTENTION.

## Success Criteria

1. **New phase enum**: `WorkUnitPhase.REVIEW` added between IMPLEMENT and COMPLETE

2. **Phase transitions**:
   - IMPLEMENT → REVIEW (after implementation completes)
   - REVIEW → COMPLETE (on APPROVE)
   - REVIEW → IMPLEMENT (on FEEDBACK, with iteration increment)
   - REVIEW → NEEDS_ATTENTION (on ESCALATE)

3. **Feedback context file**: On FEEDBACK decision, create `docs/chunks/{chunk}/REVIEW_FEEDBACK.md` containing:
   - Reviewer's feedback (issues, suggestions)
   - Current iteration count
   - Issues to address
   - The implementer skill should read this file on retry

4. **Iteration tracking**: Work unit metadata tracks `review_iterations` count

5. **Loop detection integration**: Auto-escalate when iterations exceed reviewer's `max_iterations` config

6. **Skill invocation**: REVIEW phase invokes `/chunk-review` in the worktree and parses YAML output

7. **Tests cover phase transitions**: Unit tests verify APPROVE/FEEDBACK/ESCALATE routing and iteration tracking