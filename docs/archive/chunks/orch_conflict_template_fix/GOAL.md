---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/oracle.py
- tests/test_orchestrator_oracle.py
code_references:
  - ref: src/orchestrator/oracle.py#ConflictOracle::_strip_html_comments
    implements: "HTML comment stripping helper to remove template boilerplate"
  - ref: src/orchestrator/oracle.py#ConflictOracle::_analyze_goal_stage
    implements: "Modified to strip HTML comments before finding common terms"
  - ref: tests/test_orchestrator_oracle.py#TestHtmlCommentStripping
    implements: "Unit tests for the HTML comment stripping helper"
  - ref: tests/test_orchestrator_oracle.py#TestGoalStageAnalysis::test_template_boilerplate_not_flagged_as_conflict
    implements: "Regression test for template false positive fix"
narrative: null
investigation: null
subsystems: []
created_after:
- orch_attention_queue
- orch_conflict_oracle
- orch_agent_skills
- orch_question_forward
---

# Chunk Goal

## Minor Goal

The conflict oracle in `src/orchestrator/oracle.py` produces false positive
conflicts when analyzing chunks at the GOAL stage. The `_analyze_goal_stage()`
method reads the entire GOAL.md file and passes it to `_find_common_terms()`,
which extracts common words between two chunks' goals.

The problem: GOAL.md files contain a large template comment block with example
paths like `src/segment/writer.rs` and `src/segment/format.rs`. When two chunks
share this template boilerplate, the oracle detects these example paths as
overlapping content and flags a potential conflict.

This was observed when `artifact_copy_backref` and `orch_sandbox_enforcement`
were flagged with `Files: src/segment/format.rs` - a file that doesn't exist.
Both chunks have the same GOAL.md template with example paths.

The fix should ensure the oracle only analyzes meaningful content from GOAL.md,
not the template comment block with example paths.

## Success Criteria

- The conflict oracle ignores content inside the `<!-- ... -->` template comment
  block in GOAL.md files when performing GOAL-stage analysis
- `_find_common_terms()` operates only on the actual goal description and success
  criteria, not example code paths in comments
- Two chunks with identical template boilerplate but distinct goals are NOT
  flagged as conflicting based on template examples
- Test case: Two GOAL.md files with the standard template but different actual
  goals should return `INDEPENDENT` verdict at GOAL stage
- Existing conflict detection for chunks with genuinely overlapping goals still
  works correctly
- All existing oracle tests pass