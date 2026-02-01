---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/ve.py
- tests/test_reviewer_decisions.py
code_references:
- ref: src/ve.py#decisions
  implements: "Nudge message output for FeedbackReview decisions in --recent mode"
- ref: tests/test_reviewer_decisions.py#TestReviewerDecisionsNudge
  implements: "Test coverage for nudge behavior with FeedbackReview vs good/bad"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- reviewer_decision_template
- reviewer_remove_migration
---

# Chunk Goal

## Minor Goal

Enhance the `ve reviewer decisions --recent N` command output to nudge reviewer agents toward reading detailed decision files when those decisions contain operator feedback that may be relevant to their current review.

**Problem observed:** Reviewer agents run `ve reviewer decisions --recent 10` to get few-shot context but only receive summaries. They don't open individual decision files to read detailed criteria assessments, evidence, or operator feedback. This means they miss valuable calibration signals—especially from decisions where the operator provided corrective feedback.

**Solution:** For each decision listed that has operator feedback (not just "good"/"bad" but actual text feedback), append a note prompting the agent to read the full file:

```
NOTE TO AGENT: Read the full decision context if this may be relevant
to your current review: docs/reviewers/baseline/decisions/example_1.md
```

This nudges agents toward deeper few-shot learning without requiring them to read every decision file.

## Success Criteria

- When `ve reviewer decisions --recent N` displays a decision with `operator_review` containing feedback text (i.e., a `FeedbackReview` object with a `feedback` field, not just "good" or "bad"), append a nudge message after that decision's output
- The nudge message format is: `NOTE TO AGENT: Read the full decision context if this may be relevant to your current review: <relative_path_to_decision_file>`
- Decisions marked simply "good" or "bad" do NOT get the nudge (they don't contain detailed corrective feedback worth reading)
- The nudge appears on its own line after the operator review line for each relevant decision
- Existing test coverage in `tests/test_reviewer_decisions.py` is extended to verify the nudge appears for feedback decisions and not for simple good/bad decisions

