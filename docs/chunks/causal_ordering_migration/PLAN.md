<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Create a standalone Python migration script that populates `created_after` fields for all existing artifacts by using sequence number order. The script will:

1. Process each artifact type (chunks, narratives, investigations, subsystems) independently
2. Sort artifacts by their sequence number prefix (extracted from directory names like `0001-short_name`)
3. Create a linear chain where each artifact's `created_after` points to the previous artifact's short name
4. Preserve all existing frontmatter, only adding/updating the `created_after` field
5. Run idempotently (safe to re-run; won't corrupt already-migrated artifacts)

The script reuses patterns from `docs/investigations/0001-artifact_sequence_numbering/prototypes/migration_strategy.py` for short name extraction and chain generation.

Since this is a one-time migration for this repository only (future Vibe Engineering users get causal ordering from the start via chunk 0039), no CLI command is needed. The script is stored in this chunk's folder for historical reference.

**Testing approach**: Per TESTING_PHILOSOPHY.md, we test meaningful behavior at boundaries. The migration script will have unit tests for:
- Short name extraction from various directory name formats
- Chain generation logic (first artifact gets empty list, others get previous)
- Frontmatter preservation (only `created_after` changes)

Verification after migration: `ve chunk list`, `ve narrative list`, etc. should display artifacts in causal order with tip indicators.

## Subsystem Considerations

- **docs/subsystems/0002-workflow_artifacts** (REFACTORING): This chunk IMPLEMENTS part of the causal ordering system. The migration is Phase 3 of the investigation's phased approach - it bridges existing artifacts into the new `created_after`-based ordering.

Since the subsystem is in REFACTORING status, the script should follow the established patterns in `src/artifact_ordering.py` for parsing frontmatter and extracting short names.

## Sequence

### Step 1: Create migration script with core utilities

Create `docs/chunks/0042-causal_ordering_migration/migrate.py` with:

- `extract_short_name(dir_name: str) -> str` - Extract short name from directory names like `0001-short_name` or `0001-short_name-ticket`
- `extract_sequence_number(dir_name: str) -> int` - Extract the 4-digit sequence prefix
- `parse_frontmatter(file_path: Path) -> tuple[dict, str, str]` - Parse YAML frontmatter, return (frontmatter_dict, before_content, after_content)
- `update_frontmatter(file_path: Path, created_after: list[str]) -> None` - Update only the `created_after` field, preserving everything else

Location: `docs/chunks/0042-causal_ordering_migration/migrate.py`

Reference: `docs/investigations/0001-artifact_sequence_numbering/prototypes/migration_strategy.py` for pattern

### Step 2: Implement artifact type migration

Add function `migrate_artifact_type(artifact_dir: Path, main_file: str) -> int`:

- Enumerate directories in `artifact_dir` that contain `main_file`
- Sort by sequence number
- For each artifact:
  - If first: set `created_after: []`
  - Otherwise: set `created_after: [previous_short_name]`
  - Update the main file's frontmatter
- Return count of migrated artifacts

This function handles all four types uniformly since they differ only in directory location and main file name.

Location: `docs/chunks/0042-causal_ordering_migration/migrate.py`

### Step 3: Implement main migration driver

Add `migrate_all(project_root: Path) -> dict[str, int]`:

- Process chunks: `docs/chunks/`, main file `GOAL.md`
- Process narratives: `docs/narratives/`, main file `OVERVIEW.md`
- Process investigations: `docs/investigations/`, main file `OVERVIEW.md`
- Process subsystems: `docs/subsystems/`, main file `OVERVIEW.md`
- Return dict mapping artifact type to count migrated

Add `if __name__ == "__main__":` block that:
- Determines project root (traverse up from script location to find `docs/trunk/GOAL.md`)
- Calls `migrate_all()`
- Prints summary of what was migrated

Location: `docs/chunks/0042-causal_ordering_migration/migrate.py`

### Step 4: Write tests for migration utilities

Create `tests/test_migration_utilities.py` with tests for:

1. **Short name extraction**:
   - `0001-short_name` -> `short_name`
   - `0001-short_name-ve-001` -> `short_name` (ticket suffix stripped)
   - `0001-short_name-ticket123` -> `short_name` (ticket suffix stripped)
   - Edge case: already short name format returns as-is

2. **Sequence number extraction**:
   - `0001-foo` -> 1
   - `0042-bar` -> 42
   - Edge case: no prefix returns 0

3. **Frontmatter parsing and preservation**:
   - Parse existing frontmatter correctly
   - Preserve all fields except `created_after`
   - Handle files with existing `created_after` (overwrite)
   - Handle files without `created_after` (add)

Location: `tests/test_migration_utilities.py`

### Step 5: Run migration and verify

Execute the migration script:
```bash
uv run python docs/chunks/0042-causal_ordering_migration/migrate.py
```

Verify results:
1. Check sample artifacts have `created_after` populated
2. Run `ve chunk list` - should show causal ordering with tip indicator on most recent chunk
3. Run `ve narrative list`, `ve subsystem list`, `ve investigation list` - same verification
4. Verify `.artifact-order.json` is regenerated correctly

Expected counts:
- 42 chunks (including this one)
- 3 narratives
- 2 investigations
- 2 subsystems

### Step 6: Update GOAL.md with code_paths

Update the chunk's GOAL.md frontmatter to include:
- `docs/chunks/0042-causal_ordering_migration/migrate.py`
- `tests/test_migration_utilities.py`

## Dependencies

- **Chunk ordering_field**: Adds `created_after` field to all frontmatter models (COMPLETE)
- **Chunk 0038-artifact_ordering_index**: Creates `ArtifactIndex` for causal ordering (COMPLETE)
- **Chunk 0039-populate_created_after**: Auto-populates `created_after` on new artifact creation (COMPLETE)
- **Chunk 0041-artifact_list_ordering**: Uses `ArtifactIndex` in list commands (COMPLETE)

All dependencies are satisfied - the infrastructure exists; this chunk populates existing artifacts.

## Risks and Open Questions

1. **Directory name formats**: Some chunks have ticket suffixes (`-ve-001`, `-ticket123`). The `extract_short_name` regex must handle these. The prototype's regex `r'^(\d{4})-(.+?)(-[a-zA-Z]+-\d+|-[a-zA-Z]+\d+)?$'` should work but needs verification against all actual directory names.

2. **Frontmatter preservation**: The script must not corrupt existing frontmatter. Using YAML round-trip parsing (via `ruamel.yaml` or careful string manipulation) ensures comments and formatting are preserved. Since frontmatter in this project is generated from templates and doesn't contain manual formatting, simple `yaml.safe_load` + string replacement should suffice.

3. **Idempotency**: Running the script twice should be safe. The script should detect existing `created_after` and overwrite it with the sequence-based chain. This ensures the migration can be re-run if needed.

## Deviations

1. **Full directory names in created_after**: The investigation prototype (`migration_strategy.py`) proposed using short names (e.g., `artifact_list_ordering`) in `created_after` fields. However, the actual artifact creation code in chunks.py, narratives.py, etc. uses full directory names (e.g., `0041-artifact_list_ordering`). The ArtifactIndex tip detection compares directory names against `created_after` values, so using short names would cause all artifacts to appear as tips. Updated the migration to use full directory names to match the existing creation behavior.
