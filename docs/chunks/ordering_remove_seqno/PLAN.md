<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk removes sequence prefixes from artifact directory names, transitioning from
`{NNNN}-{short_name}/` to `{short_name}/` format. The work is organized into three
phases:

1. **Update creation logic** - Modify all artifact creation functions to use short_name
   only, with collision detection
2. **Update parsing logic** - Modify code that parses directory names to handle both
   old and new formats
3. **Create migration script** - Rename existing directories and update cross-references

The strategy is to support both patterns during transition, allowing the migration to
happen independently of the code changes. This follows DEC-002 (git not assumed) since
the migration script operates on the filesystem without requiring git.

**Testing approach**: Following docs/trunk/TESTING_PHILOSOPHY.md, we write failing
tests first for behavioral changes:
- Test collision detection rejects duplicate short names
- Test new artifacts are created with short_name-only directories
- Test existing code gracefully handles both naming patterns

## Subsystem Considerations

- **docs/subsystems/0002-workflow_artifacts** (REFACTORING): This chunk IMPLEMENTS the
  directory naming transition documented in the subsystem's "Directory Naming Transition"
  section. Since the subsystem is REFACTORING, we should improve compliance in code we
  touch.

The subsystem's Hard Invariant #1 states: "Directory naming uses `{NNNN}-{short_name}/`
pattern where the sequence prefix is legacy (being retired)." This chunk completes that
retirement.

## Sequence

### Step 1: Add short_name extraction utility

Create a utility function to extract short names from directory names, handling both
old (`0001-foo`) and new (`foo`) patterns. This function will be used throughout the
codebase during the transition.

Location: `src/models.py`

```python
def extract_short_name(dir_name: str) -> str:
    """Extract short name from directory name, handling both patterns.

    Args:
        dir_name: Either "NNNN-short_name" or "short_name" format

    Returns:
        The short name portion
    """
    if re.match(r'^\d{4}-', dir_name):
        return dir_name.split('-', 1)[1]
    return dir_name
```

Tests:
- `test_extract_short_name_legacy_format` - extracts from "0001-feature"
- `test_extract_short_name_new_format` - returns "feature" unchanged
- `test_extract_short_name_with_hyphens` - handles "0001-multi-word-name"

### Step 2: Add collision detection to Chunks.find_duplicates

Update `find_duplicates` method to detect collisions by short_name, not full directory
name. This enables detecting when a new short_name would conflict with an existing
artifact.

Location: `src/chunks.py#Chunks::find_duplicates`

Current behavior: Looks for directories ending with `-{short_name}` or `-{short_name}-{ticket}`
New behavior: Also check if `short_name` equals the extracted short_name of any existing directory

Tests:
- `test_find_duplicates_detects_short_name_collision` - returns match when existing
  "0001-feature" and creating "feature"
- `test_find_duplicates_allows_different_short_names` - no collision for different names

### Step 3: Update Chunks.create_chunk to use short_name only

Modify `create_chunk` to use `{short_name}` (or `{short_name}-{ticket_id}`) as the
directory name, removing the sequence prefix.

Location: `src/chunks.py#Chunks::create_chunk` (lines 191-211)

Changes:
- Remove `next_chunk_id = self.num_chunks + 1` sequence calculation
- Remove `next_chunk_id_str = f"{next_chunk_id:04d}"` formatting
- Change directory path from `f"{next_chunk_id_str}-{short_name}"` to `f"{short_name}"`
- Add collision check before creating directory

Tests:
- `test_create_chunk_uses_short_name_only` - creates "feature/" not "0001-feature/"
- `test_create_chunk_rejects_collision` - raises error if short_name already exists
- `test_create_chunk_with_ticket_id` - creates "feature-VE-001/" format

### Step 4: Update resolve_chunk_id for both patterns

Modify `resolve_chunk_id` to find chunks by short_name when given just the short_name,
while still supporting exact matches for legacy directories.

Location: `src/chunks.py#Chunks::resolve_chunk_id` (lines 214-228)

Changes:
- Add short_name-based matching (if `chunk_id` equals extracted short_name of a directory)
- Maintain backward compatibility with "0001" prefix matching

Tests:
- `test_resolve_chunk_id_finds_by_short_name` - "feature" resolves to existing directory
- `test_resolve_chunk_id_finds_legacy_prefix` - "0001" still resolves to "0001-feature"
- `test_resolve_chunk_id_exact_match` - "0001-feature" exact match works

### Step 5: Update CHUNK_ID_PATTERN and validators

Update the `CHUNK_ID_PATTERN` regex and related validators in `models.py` to accept
both old and new patterns.

Location: `src/models.py`

Changes:
- Update `CHUNK_ID_PATTERN` to `re.compile(r"^(\d{4}-.+|[a-z0-9_-]+)$")` (or similar)
- Update `ChunkRelationship.validate_chunk_id` to accept short_name format
- Update `SubsystemRelationship.validate_subsystem_id` similarly

Tests:
- `test_chunk_relationship_accepts_short_name` - "feature" is valid
- `test_chunk_relationship_accepts_legacy` - "0001-feature" is valid
- `test_chunk_relationship_rejects_invalid` - "FEATURE" (uppercase) rejected

### Step 6: Update Narratives.create_narrative

Apply the same pattern to narrative creation.

Location: `src/narratives.py#Narratives::create_narrative` (lines 42-83)

Changes:
- Remove sequence prefix calculation
- Use `{short_name}` as directory name
- Add collision detection via short_name comparison

Tests:
- `test_create_narrative_uses_short_name_only`
- `test_create_narrative_rejects_collision`

### Step 7: Update Investigations.create_investigation

Apply the same pattern to investigation creation.

Location: `src/investigations.py#Investigations::create_investigation` (lines 53-94)

Changes:
- Remove sequence prefix calculation
- Use `{short_name}` as directory name
- Add collision detection

Tests:
- `test_create_investigation_uses_short_name_only`
- `test_create_investigation_rejects_collision`

### Step 8: Update Subsystems.create_subsystem

Apply the same pattern to subsystem creation.

Location: `src/subsystems.py#Subsystems::create_subsystem` (lines 142-183)

Changes:
- Remove sequence prefix calculation
- Use `{short_name}` as directory name
- Add collision detection
- Update `is_subsystem_dir` to accept both patterns

Tests:
- `test_create_subsystem_uses_short_name_only`
- `test_create_subsystem_rejects_collision`

### Step 9: Update find_by_shortname methods

Update `Subsystems.find_by_shortname` (and add equivalent for other types if needed)
to handle both patterns.

Location: `src/subsystems.py#Subsystems::find_by_shortname` (lines 116-131)

Tests:
- `test_find_by_shortname_finds_legacy_format`
- `test_find_by_shortname_finds_new_format`

### Step 10: Update task_utils.py

Update `get_next_chunk_id` and `create_external_yaml` for the new naming pattern.

Location: `src/task_utils.py`

Changes in `get_next_chunk_id` (lines 126-153):
- This function may no longer be needed, or needs to be repurposed
- If kept for backwards compatibility, document its legacy nature

Changes in `create_external_yaml` (lines 157-194):
- Update directory path construction to use short_name only

Tests:
- `test_create_external_yaml_uses_short_name_only`

### Step 11: Update artifact_ordering.py if needed

The `ArtifactIndex` should already work since it operates on directory names as opaque
strings. Verify this is the case and update if needed.

Location: `src/artifact_ordering.py`

Tests:
- `test_artifact_index_handles_mixed_naming` - index works with both patterns
- `test_artifact_index_tips_with_new_naming` - tips correctly identified

### Step 12: Create migration script

Create a migration script in the chunk directory that:
1. Renames all existing `{NNNN}-{short_name}/` directories to `{short_name}/`
2. Updates `created_after` references in all frontmatter to use short names
3. Updates cross-references in frontmatter (parent_chunk, narrative, subsystem refs)
4. Validates no short_name collisions exist before migrating

Location: `docs/chunks/ordering_remove_seqno/migrate.py`

The script should:
- Be idempotent (safe to run multiple times)
- Report what it will do before doing it (dry-run mode)
- Handle each artifact type (chunks, narratives, investigations, subsystems)

Tests:
- `test_migration_renames_directories`
- `test_migration_updates_created_after`
- `test_migration_detects_collisions`
- `test_migration_is_idempotent`

### Step 13: Update all tests to use new naming

Update test fixtures and assertions throughout the test suite to work with both
patterns and preferentially use the new pattern for new tests.

Location: `tests/` (multiple files)

Key files:
- `tests/conftest.py` - Update fixtures
- `tests/test_chunk_start.py` - Update assertions
- `tests/test_models.py` - Update pattern validation tests

### Step 14: Run migration on vibe-engineer itself

Run the migration script on this project's docs/ directory to rename all existing
artifacts to the new format.

This step should be done last and may require a separate commit.

## Dependencies

- Chunks 0037-0043 (causal ordering infrastructure) - Already complete
- All existing tests must pass before migration

## Risks and Open Questions

1. **Cross-reference updates scope**: The GOAL.md notes that cross-reference updates
   may be deferred to a separate chunk. Should we:
   - (A) Update created_after references only (minimal scope)
   - (B) Update all frontmatter cross-references (parent_chunk, narrative, subsystems)
   - (C) Also update code backreferences in source files

   **Recommendation**: Do (A) and (B) in the migration script, defer (C) to the next
   chunk per the investigation's proposed chunks.

2. **Collision handling**: What if two existing artifacts have the same short name
   after removing the prefix? (e.g., `0001-feature` and `0015-feature`)

   **Mitigation**: The migration script should detect this upfront and abort with a
   clear error listing the collisions. The operator can manually resolve before
   running the migration.

3. **External references**: External chunk references (`external.yaml`) use the full
   directory name. After migration, these references may point to non-existent
   directories until the external repo is also migrated.

   **Mitigation**: Document this in migration output. Consider adding the short_name
   format support to `ve sync` to auto-update external references.

4. **Test fixture pollution**: Many tests create directories with hardcoded names like
   "0001-feature". These need systematic updates.

   **Mitigation**: Step 13 handles this systematically.

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