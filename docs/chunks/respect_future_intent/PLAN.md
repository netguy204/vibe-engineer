<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk modifies only the `/chunk-create` slash command template (`src/templates/commands/chunk-create.md.jinja2`). The change is purely instructional - telling the AI agent how to analyze user intent and make decisions about FUTURE vs IMPLEMENTING status.

The approach:
1. Restructure step 3 of the instructions to establish a clear priority order
2. Add explicit detection patterns for FUTURE intent signals
3. Add explicit detection patterns for IMPLEMENTING intent signals
4. Add a new step for conflict resolution when user says "now" but an implementing chunk exists
5. Document the safe pause protocol inline in the conflict handling step

This is a documentation change only - no Python code changes are needed. The behavior change happens because agents following these instructions will now prioritize user intent signals over the default heuristic.

Note: Since this is a template file modification that produces agent instructions, not executable code, there are no unit tests to write. The "test" is verifying that the generated `.claude/commands/chunk-create.md` contains the expected instructions after running `ve init`.

## Subsystem Considerations

No subsystems are relevant to this change - this is a template modification only.

## Sequence

### Step 1: Update code_paths in GOAL.md

Update the chunk's GOAL.md frontmatter to list the files that will be modified:
- `src/templates/commands/chunk-create.md.jinja2`

Location: `docs/chunks/respect_future_intent/GOAL.md`

### Step 2: Rewrite step 3 with user intent detection

In `src/templates/commands/chunk-create.md.jinja2`, completely rewrite step 3 to:

1. **First** scan the user's input for explicit intent signals:
   - FUTURE signals: "future", "later", "queue", "backlog", "upcoming", "not now", "after current work", "next up after", "when we're ready"
   - IMPLEMENTING signals: "now", "immediately", "start working on", "work on this next", "let's do this", "begin", "start"

2. **Then** check for existing implementing chunk (via `ve chunk list --latest`)

3. **Apply priority order**:
   - If explicit FUTURE signal → use `--future`
   - If explicit IMPLEMENTING signal → don't use `--future` (but see conflict handling)
   - If no explicit signal AND implementing chunk exists → use `--future`
   - If no explicit signal AND no implementing chunk → don't use `--future`

### Step 3: Add conflict handling step

Add a new step (between current step 3 and step 4) that handles the conflict case:

**When user explicitly signals "now" but an implementing chunk exists:**

1. Inform the user of the conflict
2. Offer to pause the current implementing chunk
3. If user agrees, execute the safe pause protocol:
   - Run tests via `pytest tests/` and confirm they pass
   - Add a "Paused State" section to the current chunk's PLAN.md documenting:
     - What steps have been completed
     - What remains to be done
     - Any work-in-progress context
   - Change the current chunk's status from IMPLEMENTING to FUTURE via `ve chunk status <chunk_id> FUTURE`
4. Then proceed with creating the new chunk as IMPLEMENTING

### Step 4: Run ve init and verify

After modifying the template:
1. Run `ve init` to regenerate `.claude/commands/chunk-create.md`
2. Review the generated file to confirm the new instructions appear correctly
3. Verify the priority order is clear and the conflict handling is well-documented

## Dependencies

None. The `/chunk-create` template and `ve init` command already exist.

## Risks and Open Questions

- **Signal word ambiguity**: Some words like "start" could be ambiguous (e.g., "start a future task to..."). The instructions tell the agent to consider context, but edge cases may exist.
- **Safe pause protocol may be heavy**: Running the full test suite before pausing could be slow. However, this is a safety feature to ensure we don't pause a chunk in a broken state.

## Deviations

<!-- Populated during implementation -->