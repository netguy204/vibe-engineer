

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Two template files are out of sync. The fix is purely documentary: rewrite the
`PROPOSED_CHUNKS` comment block in the OVERVIEW.md template so it tells the
agent to populate the array at narrative-creation time, then audit the
`narrative-create` skill prompt to confirm (and tighten if needed) that it
gives consistent guidance. Re-render with `ve init` and smoke-test with an
ephemeral narrative to confirm the rendered output is coherent.

No schema changes. No code logic changes. This chunk touches only Jinja2
templates and documentation.

## Subsystem Considerations

This chunk USES the **template_system** subsystem (STABLE). The templates being
edited (`src/templates/narrative/OVERVIEW.md.jinja2` and
`src/templates/commands/narrative-create.md.jinja2`) are part of the template
system's scope, but the changes here are purely to comment/prose content inside
those templates — not to the rendering infrastructure itself. No compliance
deviations to record.

## Sequence

### Step 1: Rewrite the `PROPOSED_CHUNKS` comment block in OVERVIEW.md.jinja2

In `src/templates/narrative/OVERVIEW.md.jinja2`, replace the existing
`PROPOSED_CHUNKS:` comment block (lines 18–38) with a corrected version that:

1. Removes the "DO NOT POPULATE this array during narrative creation" line
   entirely — this is the root cause of the bug.

2. Adds an explicit instruction that the agent **must** populate this array at
   narrative-creation time, as part of completing the OVERVIEW.md template.

3. Documents which fields are set when:
   - `prompt` — written at narrative-creation time (the refinement output)
   - `depends_on` — written at narrative-creation time (per the semantics table)
   - `chunk_directory` — left as `null` at narrative-creation time; filled in
     automatically by `/chunk-create` when the proposed chunk is reified

4. Preserves the existing `depends_on` semantics table verbatim (null vs [] vs
   indices), since those semantics are correct and cross-referenced by the skill
   prompt.

5. Keeps the `ve chunk list-proposed` tip.

The updated block should read as a single, coherent instruction: "populate now,
leave chunk_directory null until /chunk-create."

### Step 2: Audit and tighten the `narrative-create` skill prompt

Open `src/templates/commands/narrative-create.md.jinja2` and review Step 3 and
Step 4:

- **Step 3** currently says "Complete the template in <narrative_path>/OVERVIEW.md
  with the information supplied by the operator." This is correct in intent but
  does not explicitly mention populating `proposed_chunks`. Add a parenthetical
  or clarifying sentence making it clear that completing the template includes
  writing the `proposed_chunks` frontmatter array.

- **Step 4** already focuses on `depends_on` semantics and doesn't imply the
  array should be left empty. Verify no wording does so implicitly. If the
  existing wording is clean, leave Step 4 otherwise unchanged.

The goal is that an agent reading Steps 3 and 4 in sequence gets an unambiguous
directive: populate `proposed_chunks` now, use Step 4's guidance to set
`depends_on` correctly for each entry.

### Step 3: Re-render with `ve init`

Run:

```bash
uv run ve init
```

Confirm the command exits cleanly and reports the expected rendered files. The
rendered commands (`.claude/commands/narrative-create.md`) and any CLAUDE.md
sections should be updated if they reference the affected templates.

### Step 4: Smoke-test with an ephemeral narrative

Create a temporary narrative to verify the template produces coherent guidance:

```bash
uv run ve narrative create verify_proposed_chunks_fix
```

Open `docs/narratives/verify_proposed_chunks_fix/OVERVIEW.md` and confirm:

- The `PROPOSED_CHUNKS` comment block instructs the agent to populate the array
  **now**, not later.
- The comment specifies `chunk_directory: null` until reification.
- The `depends_on` semantics table is present and intact.
- No contradictory "DO NOT POPULATE" text appears anywhere in the file.

Then delete the ephemeral narrative:

```bash
rm -rf docs/narratives/verify_proposed_chunks_fix
```

### Step 5: Update chunk GOAL.md code_paths

Update the `code_paths` field in
`docs/chunks/narrative_proposed_chunks_doc/GOAL.md` to reflect both files
touched:

```yaml
code_paths:
- src/templates/narrative/OVERVIEW.md.jinja2
- src/templates/commands/narrative-create.md.jinja2
```

(These are already listed; confirm they are accurate and complete.)

## Dependencies

None. Both files are standalone templates with no code dependencies.

## Risks and Open Questions

- **`ve init` scope**: `ve init` re-renders all templates. Confirm the command
  doesn't overwrite any locally modified files unexpectedly. The CLAUDE.md in
  this worktree has a VE:MANAGED section that is managed by `ve init` — verify
  it doesn't regress.

- **Rendered command location**: After `ve init`, the rendered
  `.claude/commands/narrative-create.md` should reflect Step 3's updated
  wording. Check that the rendered file matches the template change.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?
-->
