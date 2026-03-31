

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The fix is a targeted edit to a single Jinja2 template:
`src/templates/commands/chunk-execute.md.jinja2`. The current flow is linear
(plan → implement → error gate → complete). We need to insert a review →
implement feedback loop between the error gate and the complete phase.

The key insight is that `/chunk-implement` already supports re-implementation
from review feedback — it checks for `REVIEW_FEEDBACK.md` at the top of its
instructions (step 2) and addresses all issues listed there. So the loop
mechanism is:

1. After implement, run `/chunk-review`
2. If APPROVE → proceed to complete
3. If FEEDBACK → write the issues to `<chunk directory>/REVIEW_FEEDBACK.md`,
   run `/chunk-implement` again (which will read that file), then re-review
4. If ESCALATE → stop and report to operator
5. Max 5 iterations to prevent infinite loops

This respects DEC-005 (no git operations prescribed) and DEC-001 (CLI-driven).

No new tests are needed per TESTING_PHILOSOPHY.md: "We verify templates render
without error and files are created, but don't assert on template prose." The
change is purely to template prose/instructions — no code behavior changes.

## Subsystem Considerations

No subsystems are relevant to this change. This is a template-only edit.

## Sequence

### Step 1: Restructure the template to add review loop

Edit `src/templates/commands/chunk-execute.md.jinja2` to replace the current
linear flow (steps 3–5) with a review loop. The new flow:

**Current steps 1–2 remain unchanged** (determine chunk, plan phase guard).

**Replace steps 3–5 with:**

**Step 3: Implement phase.** Invoke `/chunk-implement` to execute the plan.

**Step 4: Error gate.** (Same as current — stop on build/test errors.)

**Step 5: Review loop.** After successful implementation, enter the review loop:

```
Set iteration = 1, max_iterations = 5

LOOP:
  a. Run /chunk-review
  b. If APPROVE → exit loop, proceed to complete
  c. If ESCALATE → STOP, report to operator
  d. If FEEDBACK:
     - If iteration >= max_iterations → STOP, report max iterations reached
     - Write the review issues to <chunk directory>/REVIEW_FEEDBACK.md
       (the format /chunk-implement expects: a list of issues with location,
       concern, and suggestion)
     - Run /chunk-implement (which reads REVIEW_FEEDBACK.md and addresses issues)
     - Increment iteration
     - Go to LOOP
```

The REVIEW_FEEDBACK.md file format should list each issue from the FEEDBACK
decision's `issues` array so `/chunk-implement` can address them:

```markdown
# Review Feedback (Iteration N)

The following issues were identified during review. Address each one.

## Issue 1: [concern]
- **Location**: [file:line]
- **Concern**: [what's wrong]
- **Suggestion**: [how to fix]
- **Severity**: [severity]

## Issue 2: ...
```

**Step 6: Complete phase.** Invoke `/chunk-complete` (same as current step 5).

**Step 7: Summary.** Updated to include review iteration count.

Location: `src/templates/commands/chunk-execute.md.jinja2`

### Step 2: Re-render the template

Run `uv run ve init` to re-render `.claude/commands/chunk-execute.md` from the
updated Jinja2 template.

### Step 3: Verify the rendered output

Read `.claude/commands/chunk-execute.md` and confirm:
- The review loop instructions are present
- Max iteration limit of 5 is specified
- REVIEW_FEEDBACK.md writing instructions are clear
- APPROVE/FEEDBACK/ESCALATE branches are all handled
- The loop terminates on APPROVE, ESCALATE, or max iterations

## Dependencies

None. The existing `/chunk-implement` template already supports `REVIEW_FEEDBACK.md`
(step 2 of its instructions). The `/chunk-review` template already outputs
structured FEEDBACK decisions with issues. This chunk connects the two.

## Risks and Open Questions

- **Review decision parsing**: The `/chunk-execute` agent must interpret
  `/chunk-review`'s output to decide APPROVE vs FEEDBACK vs ESCALATE. Since
  `/chunk-review` outputs structured YAML and calls the `ReviewDecision` tool,
  the executing agent should be able to read the decision. The template
  instructions should be explicit about how to determine the review outcome.
- **REVIEW_FEEDBACK.md format**: Must match what `/chunk-implement` expects.
  Looking at chunk-implement step 2, it says "Read the file carefully — it
  contains specific issues from the reviewer" — it's not prescriptive about
  format, so a clear markdown list of issues should work.

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