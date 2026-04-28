

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The entire change lives in one file: `src/templates/chunk/GOAL.md.jinja2`. The
`## Minor Goal` placeholder comment (lines 236–242 in the current template) is
replaced with new guidance that teaches stative, intent-owning prose at the
point of authorship. After editing the template, `ve init` re-renders all
derived files so the change is immediately live for new chunks.

No schema, no validator, no CLI code touches — this is a pure template-wording
change, consistent with the chunk's out-of-scope statement.

No new decisions need to be recorded in DECISIONS.md; the existing principle
("ACTIVE: Fully owns the intent that governs the code") already captures the
architectural intent — this chunk just surfaces it at the right moment.

## Sequence

### Step 1: Rewrite the `## Minor Goal` placeholder in the GOAL.md template

**File:** `src/templates/chunk/GOAL.md.jinja2`

Replace the current placeholder comment:

```
<!--
What does this chunk accomplish? Frame it in terms of docs/trunk/GOAL.md.
Why is this the right next step? What does completing this enable?

Keep this focused. If you're describing multiple independent outcomes,
you may need multiple chunks.
-->
```

With new guidance that:

1. **Anchors the author to the ACTIVE status definition** — a short inline
   reminder that "ACTIVE: Fully owns the intent that governs the code" means
   the goal must read as a present-tense architectural fact, not a description
   of work being done.

2. **Removes all transitory phrasings** — eliminate "accomplish", "next step",
   "completing this", "enable". These verbs make the author describe an
   in-flight action rather than a durable state.

3. **Gives concrete positive direction** — instruct the author to:
   - Describe the state of the architecture *once this chunk owns its intent*
   - Write as if the chunk is already ACTIVE (present tense, evergreen)
   - Prefer state verbs: "emits", "enforces", "exposes", "tolerates", "owns",
     "validates"
   - Avoid action verbs: "add", "wire", "make", "implement", "migrate"
   - Phrase it so the sentence remains true years later if the intent persists

4. **Includes a concrete contrast** — show a transitory example (bad) and its
   stative rewrite (good) so the author can self-correct:

   > ❌ Transitory: "Wire progress() calls into the snapshot pipeline so the
   >    CLI can show completion estimates."
   >
   > ✅ Stative: "The snapshot pipeline emits progress() events at each
   >    natural unit-of-work boundary, enabling downstream consumers to
   >    report completion estimates."

5. **Keeps the single-chunk scope reminder** in stative form: "If multiple
   independent architectural states are described, split into separate chunks."

### Step 2: Re-render templates

Run `uv run ve init` to regenerate all derived files from the updated Jinja2
template. Confirm the rendered `CLAUDE.md` and any other rendered outputs are
unchanged (only the chunk GOAL template content is affected).

### Step 3: Verify with a test chunk creation

Run:
```
uv run ve chunk create test_stative_voice_verification
```

Open the generated `docs/chunks/test_stative_voice_verification/GOAL.md` and
confirm the `## Minor Goal` section displays the new stative-voice guidance.

Then delete the test chunk directory:
```
rm -rf docs/chunks/test_stative_voice_verification
```

### Step 4: Update `code_paths` in this chunk's GOAL.md

Update the `code_paths` frontmatter field in
`docs/chunks/chunk_goal_stative_voice/GOAL.md` to reflect the actual file
touched:

```yaml
code_paths:
- src/templates/chunk/GOAL.md.jinja2
```

(This field is already set correctly per the chunk's current GOAL.md
frontmatter — confirm it is accurate after implementation.)

## Risks and Open Questions

- The Jinja2 template comment block is inside an HTML comment (`<!-- -->`).
  Care must be taken not to accidentally close the comment early or introduce
  syntax errors. Verify the rendered output is valid Markdown after editing.
- `ve init` re-renders `CLAUDE.md` and slash command templates. A quick diff
  after running it will confirm no unintended changes snuck through.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?
-->