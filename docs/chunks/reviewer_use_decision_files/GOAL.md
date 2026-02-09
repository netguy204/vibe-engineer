---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/chunk-review.md.jinja2
- src/ve.py
- src/reviewers.py
- tests/test_chunk_review_skill.py
code_references:
  - ref: src/templates/commands/chunk-review.md.jinja2
    implements: "Updated skill template using per-file decision workflow"
  - ref: tests/test_chunk_review_skill.py
    implements: "Tests verifying skill template uses new decision commands"
  - ref: src/cli/reviewer.py#decisions
    implements: "CLI reviewer decisions --recent for few-shot context retrieval"
narrative: null
investigation: reviewer_log_concurrency
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- reviewer_decision_create_cli
- reviewer_decisions_list_cli
- reviewer_decisions_review_cli
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

Update the chunk-review skill to use the new per-file decision system instead of appending to DECISION_LOG.md. This is the migration point where concurrent reviews become conflict-free.

## Success Criteria

- Reviewer skill calls `ve reviewer decision create <chunk>` before writing its decision
- Reviewer skill calls `ve reviewer decisions --recent 10` to get few-shot context from past operator-reviewed decisions
- Reviewer fills in the decision template rather than free-form writing
- No more appends to DECISION_LOG.md
- Reviewer prompt updated to reference decision files for past examples
- Existing DECISION_LOG.md entries migrated to individual decision files, preserving any existing operator feedback
- Decisions with migrated operator feedback appear in few-shot context immediately
- Concurrent chunk reviews in separate worktrees produce no merge conflicts