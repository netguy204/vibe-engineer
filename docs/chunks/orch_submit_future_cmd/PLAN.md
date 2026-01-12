<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a **slash command only** implementation—no CLI subcommand. The command
provides agent instructions that orchestrate existing `ve` CLI capabilities.

**Strategy:**
1. Create a new Jinja2 template at `src/templates/commands/orchestrator-submit-future.md.jinja2`
2. The template provides numbered instructions for the agent to:
   - Query all chunks with `status: FUTURE`
   - For each, check git commit status and orchestrator presence
   - Submit eligible chunks via `ve orch inject`
   - Report results to the user

**Key patterns to follow:**
- Use the same template structure as `chunk-create.md.jinja2` (frontmatter, auto-generated header, tips, instructions)
- Agent-driven logic—the template instructs the agent what to check and do
- Use existing CLI commands: `ve chunk list`, `ve orch ps`, `ve orch inject`, `ve orch start`
- Use bash for git status checks (`git status --porcelain docs/chunks/<name>`)

**Relevant decisions:**
- DEC-002 (git not assumed): This command WILL require git since it checks commit
  status. This is acceptable because the orchestrator workflow inherently assumes
  parallelization via git worktrees.
- DEC-005 (commands don't prescribe git operations): This command doesn't prescribe
  commits—it checks existing commit status as a guard.

**Testing approach:**
Per TESTING_PHILOSOPHY.md, this is a slash command template with no testable code.
We verify:
- Template renders without error (covered by existing template test infrastructure)
- Template file is created at the expected location

## Sequence

### Step 1: Create the slash command template

Create `src/templates/commands/orchestrator-submit-future.md.jinja2` with:

**Frontmatter:**
```yaml
---
description: Batch-submit all FUTURE chunks to the orchestrator.
---
```

**Structure:**
- Include auto-generated header partial
- Include common-tips partial
- Numbered instructions section

**Instructions content:**

1. **Ensure orchestrator is running**: Check with `ve orch status`. If not running,
   start it with `ve orch start`.

2. **List all chunks**: Run `ve chunk list --json` to get all chunks with their
   statuses.

3. **Filter FUTURE chunks**: From the output, identify chunks where `status: FUTURE`.

4. **Get current orchestrator work units**: Run `ve orch ps --json` to get all
   chunks already in the orchestrator.

5. **For each FUTURE chunk, evaluate eligibility:**
   - **Check git status**: Run `git status --porcelain docs/chunks/<chunk_name>/`
     - If output is non-empty → chunk has uncommitted changes → skip with message
   - **Check orchestrator presence**: Compare against work units from step 4
     - If chunk is already in orchestrator → skip with status message
   - **If committed AND not in orchestrator**: Submit via `ve orch inject <chunk_name>`

6. **Report summary**: Output a structured summary showing:
   - Submitted: chunks that were injected
   - Skipped (uncommitted): chunks with uncommitted changes
   - Skipped (already running): chunks already in orchestrator with their status

Location: `src/templates/commands/orchestrator-submit-future.md.jinja2`

### Step 2: Regenerate rendered commands

Run `uv run ve init` to render the template to `.claude/commands/orchestrator-submit-future.md`.

### Step 3: Verify template renders correctly

Confirm that:
- `.claude/commands/orchestrator-submit-future.md` exists
- Contains expected sections (Tips, Instructions)
- Auto-generated header is present (since this is the ve source repo)

### Step 4: Manual validation

Test the command manually by:
1. Creating a FUTURE chunk (or using an existing one)
2. Running `/orchestrator-submit-future`
3. Verifying the agent correctly identifies and processes FUTURE chunks

## Risks and Open Questions

1. **JSON output availability**: The plan assumes `ve chunk list --json` and
   `ve orch ps --json` provide structured output. Need to verify these flags exist.
   If not, the agent will need to parse human-readable output.

2. **Git status in non-git repos**: Per DEC-002, ve doesn't assume git. However,
   the orchestrator workflow with worktrees DOES require git. The command should
   fail gracefully with a clear error if run outside a git repository.

3. **Race conditions**: Between checking orchestrator status and submitting, another
   process could inject the same chunk. The `ve orch inject` command should handle
   this idempotently (reject duplicate injection).

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->