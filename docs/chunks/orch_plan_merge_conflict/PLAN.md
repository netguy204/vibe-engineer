<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The problem is that when `ve chunk create` runs, it creates both `GOAL.md` and `PLAN.md` from templates. Agents typically only add modified files to commits, so when they commit after refining GOAL.md, the PLAN.md remains untracked. When the orchestrator later tries to merge the worktree (where PLAN.md was created during the PLAN phase), it fails because `PLAN.md` exists as an untracked file on main.

**Strategy:** Add explicit prompting guidance in two places:
1. **`chunk-create.md.jinja2`** — Add a new step instructing agents to commit the **entire chunk directory** after refinement and approval.
2. **`GOAL.md.jinja2` template comment** — Add a note in the FUTURE CHUNK APPROVAL REQUIREMENT section reminding agents to commit both files.

This is a "prompt engineering" fix per the goal's framing. We're not changing CLI behavior—we're making agent instructions explicit about what constitutes a complete commit for a newly created chunk.

**Reference:** Per DEC-005, commands should not prescribe git operations. However, this change doesn't prescribe—it documents what files belong together when an agent chooses to commit. The agent still decides when to commit; we're clarifying what should be included.

## Subsystem Considerations

No subsystems are directly relevant to this chunk. This is a template/prompting fix that doesn't touch architectural patterns.

## Sequence

### Step 1: Add commit guidance to chunk-create skill

Update `src/templates/commands/chunk-create.md.jinja2` to add a new step after step 8 (check for existing implementing chunk) that instructs agents on proper commit behavior for newly created chunks.

The new guidance should:
- Appear as a new numbered step (step 9)
- Explicitly state that when committing a newly created chunk, the **entire chunk directory** should be added (both GOAL.md and PLAN.md)
- Explain why: `ve chunk create` generates both files, and leaving PLAN.md untracked causes merge conflicts when the orchestrator creates the worktree for the PLAN phase
- Apply specifically to FUTURE chunks being prepared for injection

**Location:** `src/templates/commands/chunk-create.md.jinja2`, after step 8

### Step 2: Update GOAL.md template with commit reminder

Update `src/templates/chunk/GOAL.md.jinja2` to add a reminder in the FUTURE CHUNK APPROVAL REQUIREMENT section.

The addition should:
- Note that after approval, when committing a FUTURE chunk, the entire chunk directory (GOAL.md + PLAN.md) should be committed together
- Be positioned after the existing approval requirement text
- Be concise (1-2 sentences)

**Location:** `src/templates/chunk/GOAL.md.jinja2`, within the FUTURE CHUNK APPROVAL REQUIREMENT comment section

### Step 3: Re-render templates and verify

Run `uv run ve init` to re-render the templates and verify:
1. The rendered `.claude/commands/chunk-create.md` includes the new step
2. Existing GOAL.md templates in test fixtures or documentation don't need updates (they're rendered from the template for new chunks only)

### Step 4: Run tests to confirm no regressions

Run `uv run pytest tests/` to ensure:
1. All existing tests pass
2. No unintended side effects from the template changes

Note: No new tests are required because this is a prompting change, not behavioral code. Per TESTING_PHILOSOPHY.md, we don't test template prose content—we verify templates render without error, which is covered by existing tests.

## Dependencies

No dependencies. This is a standalone template fix.

## Risks and Open Questions

1. **DEC-005 tension:** DEC-005 states "commands do not prescribe git operations." The new guidance documents what files belong together when committing, but doesn't prescribe *when* to commit. This seems consistent with DEC-005's spirit—the operator still controls git timing. If reviewers disagree, the guidance can be framed more as "awareness" than instruction.

2. **Existing chunks:** Chunks already created with the old templates won't benefit from the GOAL.md template update. This is acceptable—the primary fix is in chunk-create.md.jinja2 which guides agent behavior at creation time.

3. **Template scope:** The `chunk-commit.md.jinja2` skill already has guidance about including chunk documentation. However, it's invoked separately from chunk creation, so agents may commit between creating and planning without invoking that skill. The new guidance in chunk-create is targeted at the specific "create → refine → commit → inject" flow.

## Deviations

*To be populated during implementation.*