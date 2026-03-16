
<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk adds a conditional deploy step to two Jinja2 skill templates. The
work is purely template editing — no Python source code changes. Both templates
are in `src/templates/commands/` and are rendered by `ve init` per the template
system subsystem.

The deploy step is conditional: it only fires when the completed chunk's
`code_paths` frontmatter includes files under `workers/`. The steward reads the
chunk's GOAL.md to check this.

In `steward-watch.md.jinja2`, the new step slots into the orchestrator monitor
loop (Step 6) between "push completed work" and "publish to changelog" — when a
chunk is detected as DONE, the steward checks whether it impacts worker code and
deploys if so.

In `steward-setup.md.jinja2`, the deploy step is added to the autonomous mode
suggested behavior section between step 5 ("Push completed work") and step 6
("Publish to changelog").

Per DEC-005 (commands don't prescribe git operations), the deploy step itself is
project-specific operational guidance inside the SOP template, not a ve command —
this is appropriate because the steward SOP is operator-authored content that the
template merely suggests as a starting point.

**Testing**: Per TESTING_PHILOSOPHY.md, we do not assert on template prose. The
existing template render tests (`ve init` renders without error and files are
created) provide sufficient coverage. No new tests are needed — this is prose
content inside `{% raw %}` blocks that does not affect rendering logic.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template
  system. We are editing Jinja2 source templates and relying on `ve init` to
  render them. No template system code is modified — only template content.

## Sequence

### Step 1: Add conditional deploy step to steward-watch template

Edit `src/templates/commands/steward-watch.md.jinja2`. In Step 6 (the
orchestrator monitor section), add guidance for DONE chunks: before posting the
changelog entry, the steward should check the chunk's `code_paths` frontmatter
for paths under `workers/`. If present, run `cd workers/leader-board && npm run
deploy` and verify it succeeds before continuing to the changelog post.

Insert the new guidance into the numbered list item for **DONE** chunks (item 2
in the `/loop` instructions), between the current "posts a changelog entry" and
"removes the chunk from the monitoring prompt" actions.

Location: `src/templates/commands/steward-watch.md.jinja2`, inside Step 6's
`{% raw %}` block.

The text should explain:
1. Read the completed chunk's `GOAL.md` frontmatter
2. Check if any `code_paths` entry starts with `workers/`
3. If yes, run `cd workers/leader-board && npm run deploy`
4. Verify the deploy command exits 0
5. If deploy fails, include the failure in the changelog entry but don't block
6. Proceed to the changelog post

### Step 2: Add deploy step to steward-setup autonomous behavior section

Edit `src/templates/commands/steward-setup.md.jinja2`. In the "Autonomous mode
suggested behavior section", add a new numbered step between step 5 ("Push
completed work") and step 6 ("Publish to changelog"). Renumber step 6 → 7.

The new step 6 should be:

> **Deploy Durable Object worker** (conditional) — After pushing, check whether
> the completed chunk's `code_paths` include files under `workers/`. If so, run
> `cd workers/leader-board && npm run deploy` and verify it succeeds. If the
> deploy fails, include the error in the changelog entry.

Location: `src/templates/commands/steward-setup.md.jinja2`, inside the
`{% raw %}` block, in the autonomous mode markdown code fence.

### Step 3: Render and verify

Run `uv run ve init` to re-render both templates. Then verify:
1. The rendered `.claude/commands/steward-watch.md` contains the deploy step
2. The rendered `.claude/commands/steward-setup.md` contains the deploy step
3. No rendering errors occurred

### Step 4: Add backreference comment to both templates

Add a `{# Chunk: docs/chunks/steward_deploy_step #}` Jinja2 comment near the
deploy step in each template file, so future agents can trace this content back
to its governing chunk.

## Risks and Open Questions

- The deploy command (`cd workers/leader-board && npm run deploy`) is
  project-specific. If the worker directory structure changes, the steward SOP
  will need updating. This is acceptable — the SOP is operator-authored content
  that the template merely suggests as a default.
- The `code_paths` check relies on chunk authors correctly populating this
  frontmatter field. If a chunk modifies worker code but doesn't list the paths,
  the deploy won't trigger. This is a known limitation documented by the
  conditional nature of the step.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->