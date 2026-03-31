

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Create a new Jinja2 slash command template `orchestrator-inject.md.jinja2` that
follows the established pattern of the other `orchestrator-*.md.jinja2` commands.
The skill wraps `ve orch inject <chunk>` with a pre-flight commit check.

**Key design tension with DEC-005 (commands don't prescribe git operations):**
DEC-005 says commands should not prescribe when git operations occur. However,
the GOAL.md explicitly calls for auto-committing uncommitted chunk files because
this is the #1 failure mode when injecting chunks — the orchestrator worktree
won't have the files. This is a pragmatic exception: the commit is a pre-flight
safety check to ensure the orchestrator can function, not a workflow prescription.
The skill only commits the chunk's own GOAL.md and PLAN.md, not arbitrary work.

Build on the existing command template patterns:
- Frontmatter with `description` field (triggers skill matching)
- `{% include "partials/..." %}` for auto-generated header and common tips
- `$ARGUMENTS` for argument parsing
- `ve chunk list --current` as default chunk resolution

Also update `CLAUDE.md.jinja2` to list the new command alongside the other
orchestrator commands.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk USES the orchestrator
  subsystem — it creates a slash command that wraps `ve orch inject`. No new
  orchestrator functionality is added; this is a convenience layer.
- **docs/subsystems/template_system** (DOCUMENTED): This chunk USES the template
  system to create a new Jinja2 command template following established patterns.

## Sequence

### Step 1: Create the slash command template

Create `src/templates/commands/orchestrator-inject.md.jinja2` following the
established pattern from `orchestrator-monitor.md.jinja2` and
`orchestrator-submit-future.md.jinja2`.

**Frontmatter:**
```yaml
---
description: "Commit and inject a chunk into the orchestrator for background execution."
---
```

The `description` field drives skill trigger matching. It should match phrases
like "inject the chunk", "inject it", "send to orchestrator".

**Template structure:**
```
{% set source_template = "orchestrator-inject.md.jinja2" %}
{% include "partials/auto-generated-header.md.jinja2" %}
{# Chunk: docs/chunks/skill_orchestrator_inject - ... #}

## Tips
{% include "partials/common-tips.md.jinja2" %}

## Instructions
...
```

**Instructions content (inside `{% raw %}...{% endraw %}` if needed):**

1. **Argument Parsing** — Parse `$ARGUMENTS` for an optional chunk name. If
   none provided, run `ve chunk list --current` to resolve the current
   IMPLEMENTING chunk. If that returns nothing, try `ve chunk list` filtered
   for FUTURE status. If still ambiguous, ask the operator.

2. **Pre-flight: Ensure chunk is committed** — Run
   `git status --porcelain docs/chunks/<chunk>/` to check if GOAL.md or
   PLAN.md have uncommitted changes (modified, untracked, etc.). If changes
   exist:
   - Stage just the chunk files: `git add docs/chunks/<chunk>/GOAL.md docs/chunks/<chunk>/PLAN.md`
   - Also stage PLAN.md even if clean (the GOAL.md comment block says to commit both)
   - Commit with a conventional message: `docs: commit <chunk> for orchestrator injection`
   - Report to the operator that files were auto-committed

   If the chunk files are already committed and clean, report that and skip
   the commit step.

3. **Ensure orchestrator is running** — Run `ve orch status`. If the
   orchestrator is not running, start it with `ve orch start`.

4. **Inject the chunk** — Run `ve orch inject <chunk>` and capture the output.
   Report success or failure to the operator.

5. **Optional: Offer monitoring** — After successful injection, suggest:
   "Would you like me to monitor this chunk? I can run
   `/orchestrator-monitor <chunk>`." Do not auto-start monitoring unless
   the operator confirms.

Location: `src/templates/commands/orchestrator-inject.md.jinja2`

### Step 2: Update CLAUDE.md template with the new command

Edit `src/templates/claude/CLAUDE.md.jinja2` to add `/orchestrator-inject` to
the orchestrator commands listing.

Change line:
```
Commands: `/orchestrator-submit-future`, `/orchestrator-investigate`, `/orchestrator-monitor`
```
To:
```
Commands: `/orchestrator-inject`, `/orchestrator-submit-future`, `/orchestrator-investigate`, `/orchestrator-monitor`
```

Place `/orchestrator-inject` first since it's the most common entry point
(inject a single chunk → then optionally monitor it).

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 3: Re-render templates and verify

Run `uv run ve init` to re-render all templates from their Jinja2 sources.
Verify:
- `.claude/commands/orchestrator-inject.md` exists and contains the rendered skill
- `CLAUDE.md` contains the updated orchestrator commands listing with
  `/orchestrator-inject`

### Step 4: Manual smoke test

Run `uv run ve init` in a clean state and confirm:
- The new command file renders without Jinja2 errors
- The CLAUDE.md orchestrator section includes the new command
- The rendered command file has the AUTO-GENERATED header

## Dependencies

No implementation dependencies. The orchestrator CLI (`ve orch inject`) and the
template system already exist. This chunk only adds a new template file and
updates an existing one.

## Risks and Open Questions

- **DEC-005 tension:** The auto-commit behavior is a deliberate pragmatic
  exception to DEC-005's "don't prescribe git operations" principle. The commit
  is scoped narrowly (only chunk GOAL.md/PLAN.md) and is a pre-condition for
  the orchestrator to function. If this pattern expands beyond this narrow
  scope, it should be revisited as a DEC-005 amendment.
- **Non-git environments:** Per DEC-002, git is not assumed. If the project has
  no git repo, the pre-flight commit step should be skipped gracefully (the
  `git status` command will fail, and we should proceed to injection). The
  orchestrator itself requires git for worktrees, so this scenario is unlikely
  but worth handling cleanly.

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