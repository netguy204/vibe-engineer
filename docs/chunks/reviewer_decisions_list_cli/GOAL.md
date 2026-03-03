---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/reviewer.py
- tests/test_reviewer_decisions.py
code_references:
  - ref: src/cli/reviewer.py#reviewer
    implements: "CLI reviewer command group for managing reviewer agent operations and decisions"
  - ref: src/cli/reviewer.py#decisions
    implements: "CLI reviewer decisions command with --recent N and --reviewer filtering for few-shot context"
  - ref: tests/test_reviewer_decisions.py
    implements: "Comprehensive test suite for reviewer decisions CLI command"
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

Add CLI command to aggregate decisions for few-shot context. This enables the reviewer agent to learn from past decisions that have received operator feedback.

## Success Criteria

- `ve reviewer decisions --recent N` command exists
- Accepts `--reviewer` flag (default: baseline)
- Filters to only decisions where `operator_review` is not null (curated examples only)
- Outputs for each decision: working-directory-relative path, decision, summary, operator_review
- Output sorted by recency (most recent first)
- Paths are valid for the agent to read with the Read tool for progressive discovery
- See `docs/investigations/reviewer_log_concurrency/prototypes/fewshot_output_example.md` for format reference