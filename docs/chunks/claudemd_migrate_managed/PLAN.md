<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

<!--
How will you build this? Describe the strategy at a high level.
What patterns or techniques will you use?
What existing code will you build on?

Reference docs/trunk/DECISIONS.md entries where relevant.
If this approach represents a new significant decision, ask the user
if we should add it to DECISIONS.md and reference it here.

Always include tests in your implementation plan and adhere to
docs/trunk/TESTING_PHILOSOPHY.md in your planning.

Remember to update code_paths in the chunk's GOAL.md (e.g., docs/chunks/claudemd_migrate_managed/GOAL.md)
with references to the files that you expect to touch.
-->

This chunk creates a slash command that guides agents through migrating legacy CLAUDE.md files to use magic markers. The implementation follows established patterns:

1. **Slash command pattern**: Create a Jinja2 template in `src/templates/commands/` that provides step-by-step instructions for the agent. See `investigation-create.md.jinja2` for the multi-phase pattern.

2. **Migration directory pattern**: Create a migration template in `src/templates/migrations/managed_claude_md/` with a MIGRATION.md that tracks status, phases, and questions. See `chunks_to_subsystems/MIGRATION.md.jinja2` for the established pattern.

3. **Agent-driven detection**: Rather than programmatic heuristics, the slash command instructs the agent to analyze CLAUDE.md and propose line number boundaries. This is more robust for edge cases.

4. **Invariant**: Every successful migration results in magic markers present in CLAUDE.md (`<!-- VE:MANAGED:START -->` / `<!-- VE:MANAGED:END -->`).

The migration is simpler than chunks_to_subsystems because it:
- Operates on a single file (CLAUDE.md)
- Has fewer phases (detect → propose → wrap → validate)
- Doesn't involve code backreferences or archives

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system
  for rendering the slash command template and migration template. Follow the
  established patterns:
  - Templates use `.jinja2` suffix
  - Templates are rendered through `render_template` or `render_to_directory`
  - Partials go in `partials/` subdirectory if needed

## Sequence

### Step 1: Create the migration template directory

Create `src/templates/migrations/managed_claude_md/` with `MIGRATION.md.jinja2`.

The MIGRATION.md template should follow the established pattern but be simpler:
- **Status values**: DETECTING, PROPOSING, EXECUTING, COMPLETED, PAUSED, ABANDONED
- **Phases**: 1 (Detection), 2 (Proposal), 3 (Wrapping), 4 (Validation)
- **Frontmatter**: status, current_phase, phases_completed, timestamps, detected_boundaries

Key sections:
- Current State (what happened, what's next)
- Detection Results (proposed line boundaries, agent reasoning)
- Pending Questions (operator confirmation of boundaries)
- Progress Log (archaeology)
- Validation Results

Location: `src/templates/migrations/managed_claude_md/MIGRATION.md.jinja2`

### Step 2: Create the slash command template

Create `src/templates/commands/migrate-managed-claude-md.md.jinja2`.

Structure (following `investigation-create.md.jinja2` pattern):
1. **Tips section** with common tips partial
2. **Phase 1: Initialization** - Check prerequisites, create migration directory
3. **Phase 2: Detection** - Agent analyzes CLAUDE.md, proposes boundaries
4. **Phase 3: Proposal** - Present boundaries to operator for confirmation
5. **Phase 4: Wrapping** - Insert markers or append empty markers
6. **Phase 5: Validation** - Verify markers exist and are well-formed

Key behaviors to encode in the template:
- Check if CLAUDE.md exists; if not, create with empty markers
- Check if markers already exist; if so, complete immediately
- Instruct agent to read CLAUDE.md and propose "Lines N-M are VE content"
- List detection signals (headings, doc references, ve commands)
- Provide format for proposing boundaries with reasoning
- Allow operator to adjust line range before wrapping
- Handle both cases: wrap existing content OR append empty markers

Location: `src/templates/commands/migrate-managed-claude-md.md.jinja2`

### Step 3: Run `ve init` to render the slash command

After creating the template, run `ve init` to render it to `.claude/commands/migrate-managed-claude-md.md`.

Verify the rendered file exists and has the correct content.

### Step 4: Test the migration workflow manually

Test the slash command by invoking it in a test project:

1. **Test case: No CLAUDE.md** - Should create file with empty markers
2. **Test case: CLAUDE.md with VE content** - Should detect boundaries and wrap
3. **Test case: CLAUDE.md with mixed content** - Should detect VE portion only
4. **Test case: Already migrated** - Should detect markers and complete immediately

For each test case, verify:
- Migration directory created at `docs/migrations/managed_claude_md/`
- MIGRATION.md has correct frontmatter and structure
- Markers are correctly placed in CLAUDE.md
- Content outside markers is preserved

### Step 5: Add automated tests

Add tests for:
- Migration template renders correctly
- Slash command template renders correctly

Note: The migration logic itself is agent-driven (not programmatic), so testing
focuses on template correctness, not migration behavior.

Location: `tests/test_template_rendering.py` or similar

## Dependencies

- **claudemd_magic_markers chunk**: Must be complete. The magic markers
  (`<!-- VE:MANAGED:START -->` / `<!-- VE:MANAGED:END -->`) must exist in the
  CLAUDE.md template for the migration to have a target format.

  **Status**: Verified - markers exist in `src/templates/claude/CLAUDE.md.jinja2`
  at lines 10 and 402.

## Risks and Open Questions

1. **Agent boundary detection accuracy**: The migration relies on agent judgment
   to identify VE content boundaries. If the agent misjudges, operator must catch
   and correct during the proposal phase.

   **Mitigation**: Clear guidance in the slash command about detection signals,
   and explicit operator confirmation before wrapping.

2. **Edge case: VE content interleaved with user content**: If a user inserted
   custom content within the VE section (not before/after), the agent must
   decide what to do. This is inherently ambiguous.

   **Mitigation**: Agent should flag this scenario and ask operator for guidance.

3. **Preserving exact whitespace**: When wrapping content with markers, we must
   preserve exact whitespace to avoid diff noise.

   **Mitigation**: Agent should insert markers on their own lines without modifying
   surrounding content.

## Deviations

- **Status values**: Originally planned custom status values (DETECTING, PROPOSING, VALIDATING)
  for the migration template. Changed to use the standard MigrationStatus enum values
  (ANALYZING, REFINING, EXECUTING, COMPLETED) for consistency with existing migrations
  and to work with the existing Pydantic validation. The phases still map logically:
  ANALYZING covers detection, REFINING covers proposal/operator approval, EXECUTING covers
  wrapping and validation.

- **CLI output**: Updated `ve.py` to show migration-type-specific output messages. The
  managed_claude_md migration shows different guidance ("Run /migrate-managed-claude-md")
  than other migrations ("Run /migrate-to-subsystems").

- **Subdirectory creation**: Added logic to skip creating analysis/proposals/questions
  subdirectories for managed_claude_md since this migration is simpler and doesn't need them.