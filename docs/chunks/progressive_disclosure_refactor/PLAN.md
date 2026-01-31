<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Refactor CLAUDE.md.jinja2 using the prototypes from the investigation as the starting point. The investigation (`docs/investigations/claudemd_progressive_disclosure`) validated that:

1. **77% token reduction is achievable** - from ~3573 to ~834 tokens
2. **Signpost pattern works** - agents correctly discover and follow links
3. **docs/trunk/ is the appropriate home** for extracted documentation

The approach is:

1. **Create docs/trunk/ORCHESTRATOR.md** - Extract full orchestrator reference from CLAUDE.md
2. **Create docs/trunk/ARTIFACTS.md** - Extract narratives, investigations, subsystems, and backreferences documentation
3. **Update CLAUDE.md.jinja2** - Replace situational sections with signposts using the "Read when:" pattern from the prototype

Note: These new files will be static markdown files in docs/trunk/, not template-rendered files. The `_init_trunk()` method uses `overwrite=False`, meaning existing files are preserved. Adding these files manually is safe and follows the existing pattern (GOAL.md, SPEC.md, DECISIONS.md, TESTING_PHILOSOPHY.md, FRICTION.md are all static except FRICTION.md which has a template).

Per docs/trunk/TESTING_PHILOSOPHY.md:
- **Template content**: We verify templates render without error and files are created, but don't assert on template prose
- Test the `ve init` command still works correctly after template changes
- Verify token reduction target is met (manual check during implementation)

## Subsystem Considerations

- **docs/subsystems/template_system** (status unknown): This chunk USES the template system for rendering CLAUDE.md.jinja2. No changes to the template system itself, just the template content.

## Sequence

### Step 1: Create docs/trunk/ORCHESTRATOR.md

Create the orchestrator reference document using the prototype at `docs/investigations/claudemd_progressive_disclosure/prototypes/ORCHESTRATOR.md` as the source.

Location: `docs/trunk/ORCHESTRATOR.md`

Contents: Full orchestrator reference including:
- Key Commands table
- Creating and Submitting FUTURE Chunks
- Batch Creating Multiple Chunks
- Re-injecting After Updates
- Handling Attention Items
- The "Background" Keyword (with both use cases)
- Proactive Orchestrator Support

### Step 2: Create docs/trunk/ARTIFACTS.md

Create the artifacts reference document using the prototype at `docs/investigations/claudemd_progressive_disclosure/prototypes/ARTIFACTS.md` as the source.

Location: `docs/trunk/ARTIFACTS.md`

Contents:
- Narratives (with frontmatter pattern and when to use)
- Investigations (with status values and frontmatter pattern)
- Subsystems (with status values and behavior effects)
- Proposed Chunks pattern
- Code Backreferences (valid types and lifespan table)

### Step 3: Update CLAUDE.md.jinja2 with signpost structure

Replace the monolithic CLAUDE.md.jinja2 with the slim version using the prototype at `docs/investigations/claudemd_progressive_disclosure/prototypes/CLAUDE-slim.md` as the source.

Preserve these core sections (from prototype):
- Header and intro
- Project Documentation (`docs/trunk/`)
- Chunks (`docs/chunks/`) - core content only
- Chunk Naming Conventions
- Available Commands
- Creating Artifacts
- Getting Started
- Learning Philosophy

Replace these sections with signposts:
- **Narratives** → signpost pointing to `docs/trunk/ARTIFACTS.md#narratives`
- **Subsystems** → signpost pointing to `docs/trunk/ARTIFACTS.md#subsystems`
- **Investigations** → signpost pointing to `docs/trunk/ARTIFACTS.md#investigations`
- **Friction Log** → signpost pointing to `docs/trunk/FRICTION.md`
- **External Artifacts** → signpost pointing to `docs/trunk/EXTERNAL.md` (note: file doesn't exist yet, handled by separate chunk)
- **Orchestrator** → signpost pointing to `docs/trunk/ORCHESTRATOR.md`
- **Code Backreferences** → brief section with signpost to `docs/trunk/ARTIFACTS.md`

Note on Chunk Frontmatter References: The current CLAUDE.md has a "Chunk Frontmatter References" section that explains narrative, investigation, and friction_entries references. This can be shortened to a brief mention since the detailed context will be in ARTIFACTS.md.

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 4: Verify template renders correctly

Run `uv run ve init` in a test directory to verify:
1. Templates render without Jinja2 errors
2. CLAUDE.md is created successfully
3. Existing tests pass

```bash
uv run pytest tests/test_init.py -v
```

### Step 5: Validate token reduction

Count tokens in the new rendered CLAUDE.md to verify:
- Target: at least 50% reduction (from ~3573 to ~1787 or less)
- Goal from investigation: ~834 tokens (77% reduction)

Use approximate word count × 1.3 as token estimate.

## Dependencies

None - this chunk builds on the investigation findings and prototypes which are already complete.

## Risks and Open Questions

1. **External artifacts signpost**: The signpost will point to `docs/trunk/EXTERNAL.md` which doesn't exist yet. This is handled by a separate proposed chunk (`progressive_disclosure_external`). For now, the signpost can still be useful even without the detailed doc, as it tells agents what external artifacts are for.

2. **Code backreferences section placement**: The investigation prototype puts backreferences in ARTIFACTS.md, but the current CLAUDE.md has them as a standalone section. Need to decide whether to move entirely or keep a brief section in CLAUDE.md with a link. Decision: Keep a brief section in CLAUDE.md since backreferences are encountered frequently during implementation work.

3. **Proposed Chunks section**: The current CLAUDE.md has a "Proposed Chunks" section explaining the frontmatter pattern. This should be included in ARTIFACTS.md as it relates to narratives/investigations.

4. **--latest flag**: The investigation discovered that `ve chunk list --latest` is a misnomer (should be `--current`). The prototype uses `--recent` and `--current`. Need to keep the current `--latest` terminology in this chunk since the rename is a separate proposed chunk (`chunk_list_flags`). Decision: Keep `--latest` in this chunk; the rename is out of scope.

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