---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/reviewer.py
- src/reviewers.py
- tests/test_reviewer_decisions_review.py
code_references:
  - ref: src/reviewers.py#Reviewers
    implements: "Business logic class for reviewer operations"
  - ref: src/reviewers.py#Reviewers::update_operator_review
    implements: "Updates operator_review field in decision file frontmatter"
  - ref: src/reviewers.py#Reviewers::get_pending_decisions
    implements: "Returns decisions with null operator_review for --pending flag"
  - ref: src/reviewers.py#Reviewers::is_decision_file
    implements: "Validates that a path is a valid decision file"
  - ref: src/reviewers.py#validate_decision_path
    implements: "Resolves and validates decision file paths from CLI arguments"
  - ref: src/cli/reviewer.py#reviewer
    implements: "CLI reviewer command group"
  - ref: src/cli/reviewer.py#decisions
    implements: "CLI reviewer decisions subcommand with --pending flag"
  - ref: src/cli/reviewer.py#decisions_review
    implements: "CLI reviewer decisions review command"
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

Add CLI commands for operator review workflow. This enables the trust graduation loop where operator feedback on decisions becomes few-shot examples for future reviews.

## Success Criteria

- `ve reviewer decisions review <path> good` marks the decision as good
- `ve reviewer decisions review <path> bad` marks the decision as bad
- `ve reviewer decisions review <path> --feedback "<message>"` marks with feedback message
- Updates the `operator_review` field in the decision file frontmatter using the union type:
  - `good` or `bad` stored as string literal
  - feedback stored as `{ feedback: "<message>" }` map
- `ve reviewer decisions --pending` lists decisions where `operator_review` is null
- Path argument accepts working-directory-relative paths