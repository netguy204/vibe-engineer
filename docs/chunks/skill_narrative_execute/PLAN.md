

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Create a new Jinja2 command template `narrative-execute.md.jinja2` that instructs
the agent to parse a narrative's `proposed_chunks`, build a dependency DAG, create
any missing chunks, and execute them in topological waves using Claude Code's
native Agent tool for parallelism.

This follows the established command template pattern (DEC-001, DEC-009): a Jinja2
file in `src/templates/commands/` with frontmatter description, auto-generated
header, and step-by-step agent instructions. The skill is purely a prompt
template — no new Python library code is needed. The agent executing the skill
orchestrates via `ve` CLI commands and the Agent tool.

Register the new skill in `CLAUDE.md.jinja2` under Available Commands alongside
the existing `/narrative-create` and `/narrative-compact` entries.

Per DEC-005, the skill does not prescribe git operations — chunk lifecycle
commands handle their own artifacts and the operator controls version control.

**Testing**: This is a prompt template (no Python behavior to test). Per
TESTING_PHILOSOPHY.md, we verify templates render without error. The existing
template rendering test infrastructure covers this — adding the file to
`src/templates/commands/` is sufficient for it to be included in render tests.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template
  system to add a new command template. The new file follows the established
  Jinja2 command template pattern (frontmatter + partials + instructions).
  Re-rendering via `ve init` will produce the `.claude/commands/` output.

## Sequence

### Step 1: Create the command template

Create `src/templates/commands/narrative-execute.md.jinja2` following the
established pattern:

```
---
description: Execute a narrative's proposed chunks in dependency order with parallel subagents.
---
{% set source_template = "narrative-execute.md.jinja2" %}
{% include "partials/auto-generated-header.md.jinja2" %}
## Tips
{% include "partials/common-tips.md.jinja2" %}
## Instructions
...
```

The instructions must guide the executing agent through these phases:

**Phase 1 — Parse and validate the narrative**
- Accept `$ARGUMENTS` as the narrative short name
- Read `docs/narratives/<name>/OVERVIEW.md`
- Extract `proposed_chunks` from frontmatter
- Validate that the narrative exists and has proposed_chunks
- Validate that the narrative status is ACTIVE (not DRAFTING or COMPLETED)

**Phase 2 — Build the dependency DAG**
- For each proposed chunk, resolve `depends_on` indices to chunk directory names
  (using the `chunk_directory` field of referenced entries)
- Identify root chunks (those with empty `depends_on` or no dependencies)
- Detect any cycles and abort with error message if found
- Display the execution plan to the operator: which chunks will run in which
  wave, showing the parallelism structure

**Phase 3 — Create missing chunks**
- For proposed chunks where `chunk_directory` is null (chunk not yet created):
  - Run `ve chunk create <name>` using a reasonable name derived from the prompt
  - Populate the created GOAL.md with content from the narrative's prompt field
  - Update the narrative's OVERVIEW.md to set `chunk_directory` for that entry
- For proposed chunks where `chunk_directory` is already set:
  - Verify the chunk directory exists on disk
  - If it doesn't exist, warn the operator

**Phase 4 — Execute in topological waves**
- Compute execution waves: group chunks so that each wave contains only chunks
  whose dependencies are all in prior (already-completed) waves
- For each wave:
  - For each chunk in the wave:
    - Set chunk status to IMPLEMENTING via `ve chunk activate <name>`
    - Launch a background Agent to execute the full lifecycle:
      `/chunk-plan` → `/chunk-implement` → `/chunk-review` (loop until
      approved) → `/chunk-complete`
  - Launch ALL chunks in the wave as parallel Agent calls in a single message
  - Wait for all agents in the wave to complete
  - Check results: if any chunk failed, pause and report to operator
  - Once all in wave succeed, proceed to next wave

**Phase 5 — Handle failures**
- If a chunk's agent reports failure:
  - Report the failure details to the operator
  - Do NOT launch any chunks that depend on the failed chunk
  - Allow independent chunks in future waves to continue if they don't
    depend on the failed chunk (operator can choose to pause all or
    continue unblocked work)
  - Provide a clear summary: which chunks succeeded, which failed, which
    are blocked

**Phase 6 — Finalize**
- When all proposed chunks have completed successfully:
  - Update the narrative's OVERVIEW.md frontmatter status to COMPLETED
  - Report a summary of all executed chunks

**Agent invocation pattern**: Each subagent prompt should include:
- The chunk name to work on
- Instruction to run `ve chunk activate <name>` first
- Instruction to execute `/chunk-plan`, then `/chunk-implement`, then
  `/chunk-review` (repeating implement/review if review finds issues),
  then `/chunk-complete`
- Instruction to report success or failure with details

Location: `src/templates/commands/narrative-execute.md.jinja2`

### Step 2: Register the skill in CLAUDE.md.jinja2

Add `/narrative-execute` to the Available Commands section in
`src/templates/claude/CLAUDE.md.jinja2`, alongside the existing narrative
commands:

```
- `/narrative-create` - Create a new narrative for multi-chunk initiatives
- `/narrative-compact` - Consolidate multiple chunks into a narrative
- `/narrative-execute` - Execute a narrative's chunks in dependency order with parallel agents
```

Add the backreference comment for this chunk above the new entry.

Location: `src/templates/claude/CLAUDE.md.jinja2` (around line 124)

### Step 3: Re-render templates

Run `uv run ve init` to render the new command template into
`.claude/commands/narrative-execute.md` and update `CLAUDE.md` with the
new command listing.

Verify:
- `.claude/commands/narrative-execute.md` exists and contains rendered content
- `CLAUDE.md` lists `/narrative-execute` in the Available Commands section

### Step 4: Verify template renders cleanly

Run `uv run pytest tests/` to ensure the existing template rendering tests
pass with the new template included. No new test files are needed — the
template rendering infrastructure automatically discovers and renders all
templates in `src/templates/commands/`.

## Dependencies

None. This chunk creates a new command template using existing infrastructure:
- The Jinja2 template system already handles command rendering
- The `ve chunk` CLI commands already support the lifecycle operations
- The narrative frontmatter model already includes `proposed_chunks` with `depends_on`
- Claude Code's Agent tool provides native parallelism

## Risks and Open Questions

- **Chunk creation naming**: When `chunk_directory` is null and we need to create
  a chunk, the skill must derive a reasonable directory name from the prompt text.
  The instruction should tell the agent to derive a name following the naming
  conventions in CLAUDE.md (initiative-based prefixes, underscore-separated).

- **`ve chunk activate` existence**: The GOAL.md references `ve chunk activate`
  to set a chunk to IMPLEMENTING status. Need to verify this command exists.
  If not, the instruction should use a direct frontmatter edit to set
  `status: IMPLEMENTING`. Check during implementation.

- **Agent tool limitations**: The skill relies on Claude Code's Agent tool
  supporting multiple concurrent background agents. If the runtime limits
  parallelism, waves will execute with reduced concurrency but still correctly
  (the dependency ordering is what matters for correctness, parallelism is
  an optimization).

- **Review loop**: The `/chunk-review` → `/chunk-implement` loop could
  theoretically run indefinitely. The subagent instruction should cap review
  iterations (e.g., max 3 cycles) and report to the operator if still failing.

- **Partial completion and resume**: If the operator pauses execution after a
  failure and later wants to resume, the skill should detect which chunks are
  already ACTIVE (completed) and skip them, only executing remaining chunks.
  This is handled naturally by checking chunk status before launching.

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