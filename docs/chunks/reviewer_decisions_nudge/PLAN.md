<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The change is localized to the `ve reviewer decisions --recent N` output logic in `src/ve.py`. Currently, after outputting each decision's header, decision, summary, and operator review, the function moves on to the next decision. We'll add a conditional nudge message after the operator review line when that review is a `FeedbackReview` (i.e., contains detailed feedback text).

**Strategy:**
1. After formatting and outputting the `operator_review` field for each decision, check whether the `operator_review` is a `FeedbackReview` instance (which contains a `feedback` field with text).
2. If so, append a nudge message pointing the agent to the full decision file path.
3. Decisions with simple `"good"` or `"bad"` strings do not get the nudge—they lack detailed corrective feedback worth reading.

**Existing code to build on:**
- `src/ve.py` lines ~4304-4318: The `decisions` function already iterates through curated decisions and outputs each one. The operator_review is already checked with `isinstance(decision.operator_review, FeedbackReview)` to format FeedbackReview differently from string values.
- `src/models.py`: `FeedbackReview` model with a `feedback` field for structured feedback.

**Tests following TDD:**
- Write failing tests first in `tests/test_reviewer_decisions.py`
- Test that decisions with `FeedbackReview` operator_review get the nudge message
- Test that decisions with `"good"` or `"bad"` operator_review do NOT get the nudge
- Test the exact format of the nudge message

## Subsystem Considerations

No subsystems are directly relevant to this chunk. This is a small enhancement to CLI output formatting.

## Sequence

### Step 1: Write failing tests for the nudge behavior

Add tests to `tests/test_reviewer_decisions.py` that verify:

1. **Test nudge appears for FeedbackReview decisions**: Create a decision file with `operator_review: {feedback: "..."}` and verify the output includes the nudge message in the expected format.

2. **Test nudge does NOT appear for string operator_review**: Create decision files with `operator_review: good` and `operator_review: bad` and verify the nudge message does NOT appear in the output.

3. **Test nudge message format**: Verify the exact format is:
   ```
   NOTE TO AGENT: Read the full decision context if this may be relevant to your current review: <relative_path>
   ```

4. **Test nudge appears on its own line after operator review**: Verify the nudge appears after the operator review line for each relevant decision, not at the end of all decisions.

Location: `tests/test_reviewer_decisions.py`

### Step 2: Implement the nudge in the decisions command

Modify the `decisions` function in `src/ve.py` (~lines 4304-4318) to add the nudge message after formatting FeedbackReview operator reviews.

Current code structure:
```python
for filepath, decision, _mtime in curated_decisions:
    # ... output header, decision, summary ...
    if isinstance(decision.operator_review, str):
        click.echo(f"- **Operator review**: {decision.operator_review}")
    elif isinstance(decision.operator_review, FeedbackReview):
        click.echo("- **Operator review**:")
        click.echo(f"  - feedback: {decision.operator_review.feedback}")
    click.echo()
```

Change to:
```python
for filepath, decision, _mtime in curated_decisions:
    # ... output header, decision, summary ...
    if isinstance(decision.operator_review, str):
        click.echo(f"- **Operator review**: {decision.operator_review}")
    elif isinstance(decision.operator_review, FeedbackReview):
        click.echo("- **Operator review**:")
        click.echo(f"  - feedback: {decision.operator_review.feedback}")
        click.echo()
        click.echo(f"NOTE TO AGENT: Read the full decision context if this may be relevant to your current review: {rel_path}")
    click.echo()
```

The nudge uses `rel_path` which is already computed for the header.

Add chunk backreference comment before the modified section.

Location: `src/ve.py`

### Step 3: Run tests and verify

Run `uv run pytest tests/test_reviewer_decisions.py -v` to verify:
- Previously passing tests still pass
- New tests for nudge behavior pass

## Dependencies

This chunk depends on chunks that established the reviewer decision infrastructure:
- `reviewer_decision_schema` - Defined `FeedbackReview` model
- `reviewer_decisions_list_cli` - Implemented the `ve reviewer decisions --recent N` command

Both are ACTIVE, so no blocking dependencies exist.

## Risks and Open Questions

- **None identified.** This is a straightforward output enhancement with clear success criteria and a small code surface area.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->