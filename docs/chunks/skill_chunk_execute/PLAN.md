

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Create a new Jinja2 command template `chunk-execute.md.jinja2` that orchestrates
the plan → implement → complete lifecycle inline (same agent, same session). This
follows the established pattern: each slash command is a rendered Jinja2 template
in `src/templates/commands/` that becomes a `.claude/commands/*.md` file after
`ve init`.

The skill delegates to the existing `/chunk-plan`, `/chunk-implement`, and
`/chunk-complete` skills sequentially, with guard checks between each stage. It
does NOT re-implement any of those skills' logic — it composes them.

The CLAUDE.md template must also be updated to list `/chunk-execute` in the
Available Commands section, with a description that differentiates it from
orchestrator injection (per DEC-005, we don't prescribe git ops; per DEC-007,
the orchestrator is the daemon-based parallel path).

No Python code changes needed — this is purely a template/documentation change.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system
  to create a new command template and update the CLAUDE.md template. Both follow
  established patterns (Jinja2 templates, `ve init` rendering). No deviations expected.

## Sequence

### Step 1: Create the chunk-execute command template

Create `src/templates/commands/chunk-execute.md.jinja2` following the established
pattern from existing command templates.

**Frontmatter:**
```yaml
---
description: "Run a chunk's full plan → implement → complete cycle in the current session. Use /chunk-execute to run a chunk inline. Use ve orch inject to delegate to a background agent."
---
```

The description must serve double duty: it's what Claude Code uses for skill
matching AND what differentiates this from orchestrator injection. It should
trigger on phrases like "execute the chunk", "implement the chunk in this
session", "run the chunk lifecycle".

**Template structure:**
- Include `partials/auto-generated-header.md.jinja2`
- Include `partials/common-tips.md.jinja2`
- Task context conditional block (like other commands)

**Instructions section — the core logic:**

1. Accept an optional chunk name argument. If not provided, determine the
   current IMPLEMENTING chunk via `ve chunk list --current`.

2. **Plan phase guard:** Check if `<chunk directory>/PLAN.md` already has
   content beyond the template skeleton. If it's still a bare template (look
   for the `## Approach` section being empty / still containing only HTML
   comments), invoke `/chunk-plan`. If a plan already exists, skip this step
   and report "Plan already exists, skipping /chunk-plan".

3. **Implement phase:** Invoke `/chunk-implement` to execute the plan.

4. **Error gate:** If implementation encounters errors, STOP and report the
   error to the operator. Do NOT proceed to the complete phase. The operator
   may want to intervene, run `/chunk-review`, or adjust the plan.

5. **Complete phase:** Invoke `/chunk-complete` to finalize code references,
   run overlap analysis, and transition the chunk to ACTIVE/HISTORICAL status.

6. **Summary:** Report the final status of the chunk execution — which phases
   ran, whether any were skipped, and the chunk's final status.

Location: `src/templates/commands/chunk-execute.md.jinja2`

### Step 2: Add /chunk-execute to the CLAUDE.md template

Update `src/templates/claude/CLAUDE.md.jinja2` to list `/chunk-execute` in the
Available Commands section. Place it after `/chunk-implement` and before
`/chunk-review`, since it logically encompasses plan + implement + complete:

```
- `/chunk-execute` - Run a chunk's full lifecycle (plan → implement → complete) in the current session
```

Add a chunk backreference comment above the line for traceability.

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 3: Render and verify

Run `uv run ve init` to render the templates and verify:
- `.claude/commands/chunk-execute.md` is created
- `CLAUDE.md` lists `/chunk-execute`
- The rendered output matches expectations (no Jinja2 syntax errors)

### Step 4: Test template rendering

Since this is a template-only change, testing follows the project's convention:
"We verify templates render without error and files are created, but don't assert
on template prose" (per TESTING_PHILOSOPHY.md).

Run the existing test suite (`uv run pytest tests/`) to ensure no regressions in
template rendering. If there are existing tests for `ve init` or command template
rendering, verify the new template is included in their coverage.

## Dependencies

No external dependencies. This chunk composes three existing skills
(`/chunk-plan`, `/chunk-implement`, `/chunk-complete`) that are already
implemented and rendered.

## Risks and Open Questions

- **Plan detection heuristic:** Determining whether a PLAN.md is "already filled
  in" vs "still a bare template" relies on checking whether the `## Approach`
  section contains only HTML comments. This is fragile if the template structure
  changes. Mitigation: keep the heuristic simple and document it clearly. The
  agent executing the skill can use judgment.

- **Error propagation between phases:** The skill instructs the agent to "STOP if
  implementation has errors", but the definition of "error" is subjective when an
  agent is executing code. This is acceptable because the agent has judgment, and
  the instruction is a guideline, not a programmatic check.

- **Task context compatibility:** The skill needs to work both in single-project
  and multi-project (task) contexts. The existing sub-skills already handle task
  context via Jinja2 conditionals, so chunk-execute just needs to include the
  same conditional blocks for tips/context.

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