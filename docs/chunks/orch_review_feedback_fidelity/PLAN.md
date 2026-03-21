

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The root cause is a two-part gap in the orchestrator's FEEDBACK→re-IMPLEMENT cycle:

1. **The implementer prompt never mentions REVIEW_FEEDBACK.md.** The `chunk-implement.md.jinja2` template is silent about prior feedback. The orchestrator creates `REVIEW_FEEDBACK.md` in the chunk directory (via `create_review_feedback_file` in `src/orchestrator/review_parsing.py`), but the implementer has no instruction to read it.

2. **The orchestrator injects no feedback content into the prompt.** In `src/orchestrator/agent.py`, `run_phase()` only injects operator answers (the `answer` parameter for ESCALATE/question flows). When FEEDBACK routes back to IMPLEMENT, `session_id` is cleared (fresh session) and no feedback content is prepended.

**Strategy:** Fix both sides:

- **Template side:** Update the `chunk-implement.md.jinja2` template to instruct the implementer to check for `REVIEW_FEEDBACK.md` and address every issue with an explicit acknowledgement (fixed / deferred with reason / disputed with evidence).
- **Orchestrator side:** In `agent.py`, when running the IMPLEMENT phase, detect whether `REVIEW_FEEDBACK.md` exists in the chunk directory and prepend its full content to the prompt. This ensures the feedback is in the agent's context window regardless of whether it reads the file independently.
- **Validation side:** Add a `validate_feedback_addressed` function in `review_parsing.py` that the reviewer template can call or that the orchestrator can invoke before sending to re-review. This checks that each issue from the prior REVIEW_FEEDBACK.md has an explicit acknowledgement.

This follows the existing pattern where the orchestrator constructs prompts in `run_phase()` (lines 559-574 of `agent.py` already prepend CWD reminders and operator feedback) and uses the template system (DEC-001) for agent instructions.

## Subsystem Considerations

- **docs/subsystems/orchestrator**: This chunk IMPLEMENTS part of the orchestrator's review→implement cycle. The scheduler decomposition is respected — changes to feedback file creation stay in `review_parsing.py`, routing stays in `review_routing.py`, and agent dispatch stays in `agent.py`.
- **docs/subsystems/template_system**: This chunk USES the template system to update the `chunk-implement.md.jinja2` template. Per the template editing workflow in CLAUDE.md, edits go to the source template and are rendered via `ve init`.

## Sequence

### Step 1: Write tests for feedback injection into implementer prompt

Write tests in `tests/test_orchestrator_agent.py` (or a new `tests/test_orchestrator_feedback_injection.py`) that verify:

- When REVIEW_FEEDBACK.md exists in the chunk directory, `run_phase()` for IMPLEMENT prepends its content to the prompt
- When REVIEW_FEEDBACK.md does not exist (first iteration), the prompt is unchanged
- The injected content includes a header like `## Prior Review Feedback` to clearly delineate it

These tests can mock the ClaudeSDKClient and inspect the prompt string passed to it.

Location: `tests/test_orchestrator_feedback_injection.py`

### Step 2: Inject REVIEW_FEEDBACK.md content into the implementer prompt

In `src/orchestrator/agent.py`, modify `run_phase()` to detect and prepend feedback content when running the IMPLEMENT phase:

After the existing CWD reminder prepend (line 574) and before the operator answer injection (line 644), add logic:

```python
# If re-implementing after FEEDBACK, inject the review feedback
if phase == WorkUnitPhase.IMPLEMENT:
    feedback_path = worktree_path / "docs" / "chunks" / chunk / "REVIEW_FEEDBACK.md"
    if feedback_path.exists():
        feedback_content = feedback_path.read_text()
        feedback_header = (
            "## Prior Review Feedback (MUST ADDRESS)\n\n"
            "The following feedback was provided by the reviewer. "
            "You MUST address EVERY issue listed below. For each issue, either:\n"
            "- Fix it in the code\n"
            "- Defer it with a clear reason why it cannot be addressed now\n"
            "- Dispute it with evidence for why the current approach is correct\n\n"
            "Do NOT skip any items. Non-functional feedback (documentation, style, "
            "naming) is equally important as functional feedback.\n\n"
        )
        prompt = feedback_header + feedback_content + "\n\n---\n\n" + prompt
```

This ensures feedback is the FIRST thing in the prompt, maximizing visibility.

Location: `src/orchestrator/agent.py` in the `run_phase()` method

### Step 3: Write tests for the updated chunk-implement template

Write tests verifying that the rendered `chunk-implement.md` template includes instructions about checking for and addressing `REVIEW_FEEDBACK.md`. This is a template content test, so keep it lightweight — just verify the key instructional phrases are present.

Location: `tests/test_orchestrator_feedback_injection.py` (or alongside existing template tests)

### Step 4: Update the chunk-implement template to reference REVIEW_FEEDBACK.md

Modify `src/templates/commands/chunk-implement.md.jinja2` to add a step between the current steps 1 and 2:

```markdown
2. Check if <chunk directory>/REVIEW_FEEDBACK.md exists. If it does:
   - This is a re-implementation cycle after reviewer feedback
   - Read the file carefully — it contains specific issues from the reviewer
   - You MUST address EVERY issue listed. For each issue:
     - **Fix** it in the code, OR
     - **Defer** it with a documented reason (add to PLAN.md Deviations), OR
     - **Dispute** it with evidence for why the current approach is correct
   - Non-functional feedback (documentation, style, naming conventions) is
     equally important as functional feedback — do not skip these
   - After addressing all issues, delete the REVIEW_FEEDBACK.md file to
     signal completion
```

Then renumber subsequent steps (current step 2 becomes step 3, etc.).

Run `ve init` to re-render the template.

Location: `src/templates/commands/chunk-implement.md.jinja2`

### Step 5: Write tests for feedback acknowledgement validation

Write tests for a new `validate_feedback_addressed` function that:

- Given a REVIEW_FEEDBACK.md with N issues and the current worktree state, checks whether the file has been deleted (indicating the implementer addressed everything)
- Returns a list of unaddressed issues if the file still exists
- Returns empty list if the file is gone (all addressed)

This is intentionally simple — the validation is "did the implementer delete the file?" rather than parsing acknowledgements. Deleting the file is the implementer's signal that they've addressed everything; the reviewer will verify correctness on re-review.

Location: `tests/test_orchestrator_review_parsing.py`

### Step 6: Implement feedback acknowledgement validation

Add `validate_feedback_addressed()` to `src/orchestrator/review_parsing.py`:

```python
def validate_feedback_addressed(
    worktree_path: Path,
    chunk: str,
) -> bool:
    """Check whether review feedback has been addressed.

    The implementer signals completion by deleting REVIEW_FEEDBACK.md.
    If the file still exists, feedback has not been fully addressed.

    Returns:
        True if feedback was addressed (file deleted), False otherwise
    """
    feedback_path = worktree_path / "docs" / "chunks" / chunk / "REVIEW_FEEDBACK.md"
    return not feedback_path.exists()
```

Location: `src/orchestrator/review_parsing.py`

### Step 7: Write tests for pre-review validation check

Write tests verifying that the review routing logic checks for unaddressed feedback before allowing the REVIEW phase to proceed. When REVIEW_FEEDBACK.md still exists at the start of the REVIEW phase, the work unit should be routed back to IMPLEMENT with a warning.

Location: `tests/test_orchestrator_review_routing.py`

### Step 8: Add pre-review validation in the scheduler

In the scheduler's dispatch logic or in `agent.py`'s `run_phase()`, before executing a REVIEW phase, check if the prior REVIEW_FEEDBACK.md still exists. If it does, log a warning and route back to IMPLEMENT rather than wasting a review cycle:

```python
if phase == WorkUnitPhase.REVIEW:
    if not validate_feedback_addressed(worktree_path, chunk):
        logger.warning(
            f"Chunk {chunk}: REVIEW_FEEDBACK.md still exists, "
            f"feedback not fully addressed. Returning to IMPLEMENT."
        )
        # Route back to implement instead of running review
```

This acts as a safety net — if the implementer somehow skips addressing feedback, we catch it before the reviewer sees the same issues again.

Location: `src/orchestrator/scheduler.py` (in `_dispatch_work_unit`) or `src/orchestrator/agent.py`

### Step 9: Run full test suite and verify

Run `uv run pytest tests/` to ensure all existing tests still pass and the new tests pass. Fix any issues.

### Step 10: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter with the files touched:
- `src/orchestrator/agent.py`
- `src/orchestrator/review_parsing.py`
- `src/orchestrator/scheduler.py`
- `src/templates/commands/chunk-implement.md.jinja2`
- `tests/test_orchestrator_feedback_injection.py`
- `tests/test_orchestrator_review_parsing.py`
- `tests/test_orchestrator_review_routing.py`

## Risks and Open Questions

- **Context window pressure:** Prepending REVIEW_FEEDBACK.md to the prompt adds content. For chunks with extensive feedback, this could be significant. However, feedback files are typically small (a few hundred tokens), and the benefit of guaranteed visibility outweighs the cost.
- **File deletion as acknowledgement signal:** Using file deletion is simple but loses the audit trail. The reviewer's decision files in `docs/reviewers/baseline/decisions/` preserve the historical record, so the REVIEW_FEEDBACK.md is ephemeral by design — it's a communication channel, not a record.
- **Template re-rendering:** After editing `chunk-implement.md.jinja2`, `ve init` must be run. The worktree may not have the rendered output yet. Implementation should run `ve init` after template changes and verify the rendered `.claude/commands/chunk-implement.md` matches expectations.

## Deviations

- Steps 5/7 tests (validate_feedback_addressed, pre-review validation) were added to existing test files (`test_orchestrator_review_parsing.py` and `test_orchestrator_review_routing.py`) rather than creating separate test files, as they naturally extend the existing test classes.
- Step 8 pre-review validation was placed in `scheduler.py`'s `_dispatch_work_unit` method rather than `agent.py`, consistent with the plan's first option and the existing pattern where dispatch logic lives in the scheduler.
- Added a step 5 to the rendered template ("verify you deleted REVIEW_FEEDBACK.md") as an additional safety reminder beyond what the plan specified.
