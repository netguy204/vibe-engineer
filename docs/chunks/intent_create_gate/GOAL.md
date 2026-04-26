---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/commands/chunk-create.md.jinja2
code_references:
  - ref: src/templates/commands/chunk-create.md.jinja2
    implements: "Intent-judgment gate (step 4) enforcing CHUNKS.md principle 2 before goal refinement"
narrative: intent_ownership
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- intent_principles
---

# Chunk Goal

## Minor Goal

The `/chunk-create` skill applies the principle-2 intent test before refining a goal. The agent — not the operator — judges whether the work is intent-bearing. The gate is asymmetric: silent on the easy cases, escalate only on suspicion.

Behavior at chunk creation:

- **Clearly intent-bearing** (architectural decision, constraint to remember, contract being established) → proceed silently. No operator prompt.
- **Suspected non-intent-bearing** (mechanical change, typo, dep bump, performance tweak that doesn't change shape, comment cleanup) → surface to operator with a one-line summary of *why* it looks vibe-able, and ask: *"Create the chunk anyway?"* Operator confirms or skips.
- **Orchestrator-execution signals present** (`in the background`, `in parallel`, `via the orchestrator`, `queue these up`, `have an agent do this`, `spawn all the chunks in this narrative`, etc.) → proceed silently regardless of intent-bearing judgment. The operator has signaled they want a unit of delegated work, not just a piece of architectural memory.

The asymmetry is load-bearing: operators routinely spawn entire narratives' worth of chunks in one prompt. Re-confirming each one would be unbearable. The agent only interrupts when it suspects scope creep into the chunk system.

The principle the gate enforces: `docs/trunk/CHUNKS.md` principle 2 — *chunks exist only for intent-bearing work*. Reference the principle by name in the skill so future contributors can trace the rule back to its source.

## Success Criteria

1. `src/templates/commands/chunk-create.md.jinja2` includes an intent-judgment step before goal refinement. The step instructs the agent to apply the principle-2 test itself.
2. The skill instructs the agent to proceed silently for clearly intent-bearing work (no operator prompt).
3. The skill instructs the agent to ask the operator only when it suspects the work could be vibed, with a one-line summary of why.
4. The skill instructs the agent to detect orchestrator-execution signals (the listed phrases or semantically equivalent variants) and proceed silently when they're present.
5. The skill text references `docs/trunk/CHUNKS.md` principle 2 by name.
6. `uv run ve init` runs cleanly after the template change.
7. `uv run pytest tests/` passes.

## Out of Scope

- Changing `/chunk-create`'s existing status routing (FUTURE vs IMPLEMENTING) or its existing-implementing-chunk handling.
- The completion-time verification pass (chunk 3 covers that).
- Updating the existing `respect_future_intent` chunk's GOAL.md (chunk 6 audit will catch it).