---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/ve.py
- src/chunks.py
- tests/test_reviewer_decision_create.py
code_references:
  - ref: src/chunks.py#Chunks::get_success_criteria
    implements: "Extracts success criteria from chunk GOAL.md for decision template"
  - ref: tests/test_reviewer_decision_create.py#TestReviewerDecisionCreateCommand
    implements: "Test suite verifying CLI command behavior"
  - ref: src/cli/reviewer.py#reviewer
    implements: "CLI reviewer command group for reviewer agent operations"
  - ref: src/cli/reviewer.py#decision
    implements: "Decision subgroup under reviewer for decision file commands"
  - ref: src/cli/reviewer.py#create_decision
    implements: "Creates decision file at docs/reviewers/{reviewer}/decisions/{chunk}_{iteration}.md with frontmatter and criteria assessment template"
narrative: null
investigation: reviewer_log_concurrency
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- reviewer_decision_schema
created_after:
- reviewer_init_templates
- integrity_bidirectional
- integrity_code_backrefs
- integrity_fix_existing
- integrity_proposed_chunks
- integrity_validate
- orch_reviewer_decision_mcp
---

# Chunk Goal

## Minor Goal

The CLI exposes a command to instantiate decision templates for the reviewer agent. New decisions follow a consistent format and contain the expected fields, derived from the chunk's success criteria.

## Success Criteria

- `ve reviewer decision create <chunk>` command exists
- Accepts `--reviewer` flag (default: baseline) and `--iteration` flag (default: 1)
- Creates file at `docs/reviewers/{reviewer}/decisions/{chunk}_{iteration}.md`
- Pre-populates frontmatter with decision: null, summary: null, operator_review: null
- Pre-populates body with criteria assessment template derived from chunk's GOAL.md success criteria
- Validates that the chunk exists before creating decision file
- See `docs/investigations/reviewer_log_concurrency/prototypes/decision_template.md` for format reference