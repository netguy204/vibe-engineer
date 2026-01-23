# Implementation Plan

## Approach

This chunk is a documentation-only cleanup task. The previous chunks in the
`revert_scratchpad_chunks` narrative already migrated artifacts to `docs/` and
removed the scratchpad infrastructure code. This chunk updates all remaining
template documentation to reflect the new in-repo reality.

The approach is:
1. Update each template file to remove "user-global scratchpad" and
   `~/.vibe/scratchpad/` references
2. Replace with accurate descriptions of in-repo storage (`docs/chunks/`,
   `docs/narratives/`)
3. Re-render all templates using `uv run ve init`
4. Verify no "scratchpad" references remain

No tests required - this is pure documentation cleanup. Verification is via grep.

## Sequence

### Step 1: Update CLAUDE.md.jinja2 backreference section

Location: `src/templates/claude/CLAUDE.md.jinja2`

The "Code Backreferences" section (lines 353-356) incorrectly states that chunks
and narratives are "ephemeral work notes in user-global scratchpad." Since chunks
and narratives now live in the repository, these comments should simply be removed
when encountered (they're legacy from before the revert).

**Change:**
- Remove the explanation that chunks/narratives are in "user-global scratchpad"
- Keep the instruction to remove `# Chunk:` and `# Narrative:` backreferences
  (these are still legacy artifacts that may exist in older code)
- Update the reason: these are removed because subsystems are the only valid
  backreference type, not because they're "in scratchpad"

### Step 2: Update narrative-compact.md.jinja2

Location: `src/templates/commands/narrative-compact.md.jinja2`

The "Background" section (lines 26-34) and Phase 4 (lines 107-112) reference the
old scratchpad workflow.

**Changes:**
- Remove the Background note about "user-global scratchpad" storage
- Update to explain that `# Chunk:` and `# Narrative:` backreferences are legacy
  artifacts to be removed in favor of `# Subsystem:` references
- Update Phase 4 language to explain why legacy backreferences should be removed
  (subsystems are authoritative, not scratchpad location)

### Step 3: Update PLAN.md.jinja2 template

Location: `src/templates/chunk/PLAN.md.jinja2`

The "BACKREFERENCE COMMENTS" section (lines 120-124) says chunks and narratives
are "ephemeral work notes stored in user-global scratchpad."

**Change:**
- Update to say chunks and narratives should not have code backreferences because
  only subsystems represent enduring architectural patterns
- Remove the "user-global scratchpad" language

### Step 4: Update task/CLAUDE.md.jinja2

Location: `src/templates/task/CLAUDE.md.jinja2`

The "Backreferences" section (lines 43-51) contains the same incorrect language
about "user-global scratchpad."

**Change:**
- Update to match the corrected CLAUDE.md.jinja2 language

### Step 5: Update subsystem/OVERVIEW.md.jinja2

Location: `src/templates/subsystem/OVERVIEW.md.jinja2`

The "BACKREFERENCE COMMENTS" section (lines 179-181) contains the same incorrect
language about "user-global scratchpad."

**Change:**
- Update to match the corrected language (subsystems are valid; chunks/narratives
  are not valid backreference types)

### Step 6: Re-render templates

Run `uv run ve init` to regenerate all rendered files from templates.

### Step 7: Verify no scratchpad references remain

Run case-insensitive grep for "scratchpad" in:
- `src/templates/` - should return no hits
- `.claude/commands/` - should return no hits (rendered from templates)
- `CLAUDE.md` - should return no hits (rendered from template)

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->