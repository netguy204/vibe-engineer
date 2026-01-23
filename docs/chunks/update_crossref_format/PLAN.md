<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk updates all cross-references from the legacy `NNNN-short_name` format to
the new `short_name` format. The work is primarily mechanical text substitution,
but must be done carefully to avoid breaking references.

The approach:
1. Create a migration script that handles all reference types
2. Run the migration script to update all references
3. Update templates to show the new format in examples
4. Verify no broken references remain
5. Run tests to confirm nothing broke

The migration script will live in the chunk directory as a one-time artifact
(per GOAL.md chunk artifacts guidance). This follows the pattern established
by `scripts/migrate_artifact_names.py` which handled directory renaming.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (REFACTORING): This chunk IMPLEMENTS the
  final part of the directory naming transition. The subsystem's "Directory Naming
  Transition" section documents that cross-reference updates may be deferred to a
  separate chunk—this is that chunk.

Since the subsystem is in REFACTORING status and this work directly addresses a
documented transition, we should bring all references into compliance.

## Sequence

### Step 1: Create the migration script

Create `docs/chunks/update_crossref_format/migrate_crossrefs.py` that:

1. **Updates code backreferences in source files**:
   - Pattern: `# Chunk: docs/chunks/NNNN-short_name` → `# Chunk: docs/chunks/short_name`
   - Pattern: `# Subsystem: docs/subsystems/NNNN-short_name` → `# Subsystem: docs/subsystems/short_name`
   - Locations: `src/**/*.py`, `tests/**/*.py`

2. **Updates remaining frontmatter references**:
   - `chunk_id: NNNN-short_name` → `chunk_id: short_name`
   - `parent_chunk: NNNN-short_name` → `parent_chunk: short_name`
   - Locations: `docs/**/*.md`

The script should:
- Support `--dry-run` mode to preview changes
- Report statistics on what was changed
- Use regex substitution with the pattern `\d{4}-(\w+)` → `\1`

Location: `docs/chunks/update_crossref_format/migrate_crossrefs.py`

### Step 2: Run the migration script

Execute the migration script on the codebase:

```bash
python docs/chunks/update_crossref_format/migrate_crossrefs.py --dry-run
python docs/chunks/update_crossref_format/migrate_crossrefs.py
```

Expected changes:
- ~259 code backreferences in `src/`
- ~28 subsystem backreferences in `src/`
- ~48 code backreferences in `tests/`
- ~3 frontmatter references in `docs/`

### Step 3: Update template examples

Update `src/templates/chunk/PLAN.md.jinja2` to show the new backreference format
in its documentation examples:

Before:
```
# Chunk: docs/chunks/NNNN-short_name - Brief description
# Chunk: docs/chunks/0012-symbolic_code_refs - Symbolic code reference format
# Subsystem: docs/subsystems/NNNN-short_name - Brief subsystem description
```

After:
```
# Chunk: docs/chunks/short_name - Brief description
# Chunk: docs/chunks/symbolic_code_refs - Symbolic code reference format
# Subsystem: docs/subsystems/short_name - Brief subsystem description
```

Location: `src/templates/chunk/PLAN.md.jinja2`

### Step 4: Update CLAUDE.md template

Check `src/templates/claude/CLAUDE.md.jinja2` for any legacy format references
and update them.

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 5: Verify no legacy references remain

Run verification grep commands to confirm all legacy references are gone:

```bash
# Should return 0 matches:
grep -r "# Chunk: docs/chunks/[0-9]\{4\}-" src/ tests/
grep -r "# Subsystem: docs/subsystems/[0-9]\{4\}-" src/ tests/
grep -r "chunk_id: [0-9]\{4\}-" docs/
grep -r "parent_chunk: [0-9]\{4\}-" docs/
```

### Step 6: Run tests

Run the full test suite to confirm nothing broke:

```bash
uv run pytest tests/
```

All tests should pass. The tests themselves will have updated backreferences,
but the test logic should remain unchanged.

### Step 7: Update GOAL.md with code_paths

Update the chunk's GOAL.md frontmatter to list the files that were modified.
Since this is a migration affecting many files, list the key categories:
- `src/**/*.py` (source files with backreferences)
- `tests/**/*.py` (test files with backreferences)
- `docs/**/*.md` (docs with frontmatter references)
- `src/templates/**/*.jinja2` (templates with example formats)

## Dependencies

- Chunk `ordering_remove_seqno` must be complete (directories already renamed)
  - Status: ACTIVE ✓

## Risks and Open Questions

1. **Regex edge cases**: The pattern `\d{4}-` could theoretically match non-artifact
   references. Mitigate by restricting matches to known contexts:
   - `# Chunk: docs/chunks/NNNN-`
   - `# Subsystem: docs/subsystems/NNNN-`
   - YAML keys: `chunk_id:`, `parent_chunk:`, `subsystem_id:`

2. **Partial matches in prose**: Some documentation may mention legacy formats
   as examples or history (like this chunk's own GOAL.md). The migration should
   only update actual references, not prose discussing the format.
   - Mitigate by using strict context patterns

3. **Test fixtures with legacy format**: Some tests may intentionally use legacy
   format in fixture data. These should be updated to match the new format.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
