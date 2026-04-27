
<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk adds an intent-judgment gate to the `/chunk-create` skill template (`src/templates/commands/chunk-create.md.jinja2`). The gate is a new step inserted **before** the existing goal-refinement step (current step 4). It instructs the agent to apply the `docs/trunk/CHUNKS.md` principle 2 test ("does this code need to remember why it exists?") and route accordingly:

- **Clearly intent-bearing** → proceed silently.
- **Suspected non-intent-bearing** → ask the operator with a one-line rationale.
- **Orchestrator-execution signals present** → proceed silently regardless.

The change is purely to the Jinja2 template text — no Python code, no model changes, no CLI changes. The template is rendered via `ve init` through the template_system subsystem (DEC-001 / `src/template_system.py`). After editing, `uv run ve init` re-renders, and `uv run pytest tests/` confirms nothing breaks.

Per `docs/trunk/TESTING_PHILOSOPHY.md`, template prose is not tested for exact wording. The existing test suite already covers template rendering (files created without error). No new tests are needed — the gate is agent instruction text, not executable code.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system. The edit target is a Jinja2 template (`src/templates/commands/chunk-create.md.jinja2`) rendered through the canonical `render_to_directory` path. No rendering logic changes; the subsystem is used as-is.

## Sequence

### Step 1: Read the current template and identify insertion point

Read `src/templates/commands/chunk-create.md.jinja2` in full. The new intent-judgment step must be inserted **before** the current step 4 (goal refinement). All subsequent step numbers will shift by one.

Location: `src/templates/commands/chunk-create.md.jinja2`

### Step 2: Insert the intent-judgment step

Add a new step between the current step 3 (run `ve chunk create`) and step 4 (refine GOAL.md). The new step instructs the agent to:

1. **Apply the principle-2 intent test** from `docs/trunk/CHUNKS.md`: *"Does this code need to remember why it exists?"*

2. **Route based on the answer:**
   - **Clearly intent-bearing** (architectural decision, constraint to remember, contract being established, behavioral invariant, design boundary) → proceed to goal refinement silently. No operator prompt.
   - **Suspected non-intent-bearing** (mechanical change, typo fix, dependency bump, performance tweak that doesn't change shape, comment cleanup, one-off bug patch) → surface to the operator with a one-line summary of *why* the work looks vibe-able (i.e., why it lacks architectural intent), and ask: *"This looks like it could be vibed — [reason]. Create the chunk anyway?"* If the operator declines, stop. If the operator confirms, proceed.
   - **Orchestrator-execution signals detected** in the operator's request (phrases like: "in the background", "in parallel", "via the orchestrator", "queue these up", "have an agent do this", "spawn all the chunks in this narrative", or semantically equivalent variants) → proceed silently regardless of intent-bearing judgment. The operator has signaled they want a unit of delegated work.

3. **Reference the source principle** by name: *"This gate enforces docs/trunk/CHUNKS.md principle 2 — chunks exist only for intent-bearing work."*

The asymmetry rationale should be included as a brief comment in the template so future contributors understand: operators routinely spawn entire narratives' worth of chunks; re-confirming each would be unbearable. The agent only interrupts on suspected scope creep.

Location: `src/templates/commands/chunk-create.md.jinja2`

### Step 3: Renumber subsequent steps

All steps after the insertion point shift by one. Current steps 4–9 become steps 5–10. Update all internal cross-references (e.g., "step 5 above" in the depends_on section currently references step 5 — verify it still points to the correct content after renumbering).

Location: `src/templates/commands/chunk-create.md.jinja2`

### Step 4: Re-render and verify

Run `uv run ve init` to re-render the template. Verify the rendered output at `.claude/commands/chunk-create.md` contains the new intent-judgment step and correct step numbering.

### Step 5: Run the test suite

Run `uv run pytest tests/` and confirm all tests pass. No new tests are needed per the testing philosophy — template prose is not tested for exact wording.

### Step 6: Update code_paths in GOAL.md

Update the `code_paths` frontmatter in `docs/chunks/intent_create_gate/GOAL.md` to list the file touched:

```yaml
code_paths:
  - src/templates/commands/chunk-create.md.jinja2
```

## Dependencies

- **intent_principles** (ACTIVE): Landed `docs/trunk/CHUNKS.md` with the four principles. This chunk references principle 2 by name. The dependency is satisfied — `intent_principles` is already ACTIVE.

## Risks and Open Questions

- **Step numbering fragility**: The template has internal cross-references between steps (e.g., "step 5 above" in the depends_on guidance). Renumbering must be done carefully to avoid dangling references. Mitigated by a careful read-through in Step 3.
- **Orchestrator-signal detection scope**: The list of orchestrator-execution phrases is illustrative, not exhaustive. The template instructs the agent to match "semantically equivalent variants," which relies on the agent's judgment. This is intentional — a rigid keyword list would miss natural phrasing.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->