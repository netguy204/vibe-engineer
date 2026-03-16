

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Edit the steward-watch Jinja2 template (`src/templates/commands/steward-watch.md.jinja2`)
to add a prominent callout in Step 5 (the ack step) making it explicit that **every**
received message must be acked — not just messages that produce chunks or actionable work.

The note should call out the failure mode: without acking, the cursor never advances and
the steward re-receives the same message on the next watch cycle, looping forever.

This is a documentation-only change to a single template file. After editing the template,
run `ve init` to re-render the output file and verify correctness. Per
docs/trunk/TESTING_PHILOSOPHY.md, we don't assert on template prose content, so the
existing rendering tests in `tests/test_steward_skills.py` already cover the verification
that the template renders without error.

<!-- No subsystems are relevant to this documentation-only change. -->

## Sequence

### Step 1: Add ack-all callout to Step 5 of the steward-watch template

Edit `src/templates/commands/steward-watch.md.jinja2`, within the `{% raw %}` block
at Step 5 ("Ack to advance cursor"). Add a callout note after the existing "Critical"
paragraph that makes clear:

1. **Every message must be acked**, regardless of whether it produced a chunk, was a
   no-op, was a question answered inline, or was a bootstrap/initialization message.
2. **The failure mode**: without acking, the cursor stays at the same position and the
   next `ve board watch` re-delivers the same message, causing an infinite loop.

The callout should be visually distinct (e.g., bold prefix or blockquote) so an agent
scanning the skill doesn't miss it. Place it directly after the existing "Critical: Do
NOT ack before processing is complete" paragraph to keep all ack guidance in one place.

Suggested wording (adjust for tone/flow):

```
**Every message must be acked.** This includes messages that don't produce
actionable work — bootstrap/initialization messages, questions answered inline,
no-ops, and duplicates. The ack advances the cursor past the message. Without it,
the cursor stays in place and the next watch cycle re-delivers the same message,
causing the steward to loop on it indefinitely.
```

Location: `src/templates/commands/steward-watch.md.jinja2`, inside Step 5.

### Step 2: Re-render and verify

Run `uv run ve init` to re-render the template into `.claude/commands/steward-watch.md`.
Read the rendered output to confirm:

- The new callout appears in the rendered file
- The surrounding content is intact
- No Jinja2 rendering errors

### Step 3: Run existing tests

Run `uv run pytest tests/test_steward_skills.py -v` to verify the template still
renders correctly. Per the testing philosophy, we don't assert on prose content, so
no new tests are needed — the existing rendering tests confirm the template produces
valid output.

<!-- No dependencies — the template already exists from leader_board_steward_skills. -->

## Risks and Open Questions

- Placement: The note needs to be prominent enough that an agent doesn't skip it, but
  not so verbose that it drowns out the existing critical guidance about not acking
  before processing is complete. The two rules are complementary (always ack, but only
  after processing), so keeping them adjacent is important.

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