---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/ve.py
- src/chunks.py
- tests/test_chunk_start.py
- tests/test_chunk_list.py
code_references:
  - ref: src/ve.py#validate_combined_chunk_name
    implements: "Combined chunk name length validation at creation time"
  - ref: src/ve.py#list_chunks
    implements: "Frontmatter parse error surfacing in chunk list command"
  - ref: src/chunks.py#Chunks::activate_chunk
    implements: "Frontmatter parse error surfacing in chunk activation"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
created_after:
- backref_restore_postmigration
---

# Chunk Goal

## Minor Goal

Enforce the 31-character chunk name limit at creation time and provide clear error messages when frontmatter parsing fails due to validation errors.

Currently, `ve chunk create` allows chunk names exceeding the 31-character limit imposed by `ExternalArtifactRef.artifact_id` validation. This creates chunks that work locally but fail silently or with cryptic errors when used in cross-repo workflows (e.g., as dependents in task directories). The failure manifests as `[UNKNOWN]` status in `ve chunk list` with no explanation of why parsing failed.

## Success Criteria

**Bug fix verification:**
- `ve chunk create` rejects names longer than 31 characters with a clear error message
- All commands that parse chunk frontmatter display Pydantic validation errors instead of failing silently

**Implementation requirements:**
1. **Validate chunk name length at creation time**
   - `ve chunk create my_very_long_chunk_name_that_exceeds_limit` exits with error
   - Error message explains the 31-character limit and shows actual length
   - Location: `src/ve.py` in the `chunk_create` command

2. **Surface frontmatter parsing errors across all commands**
   - When `ChunkFrontmatter` validation fails, emit the Pydantic validation error details
   - Affected commands include at minimum:
     - `ve chunk list` - show `[PARSE ERROR: <reason>]` instead of `[UNKNOWN]`
     - `ve chunk activate` - show why activation failed
     - Any other command that loads/parses chunk GOAL.md frontmatter
   - Error should include the field name and validation message (e.g., "dependents.0.artifact_id: must be less than 32 characters (got 35)")
   - Consider a shared utility for frontmatter parsing that handles errors consistently

3. **Tests verify both behaviors**
   - Test that chunk creation fails for names > 31 chars
   - Test that parse errors are surfaced with Pydantic details in relevant commands

## Notes

- The 31-character limit is enforced in `src/validation.py:validate_identifier()` with `max_length=31`
- `ExternalArtifactRef` in `src/models.py:291-295` uses `_require_valid_dir_name()` which calls this validator
- The limit exists because chunk names become directory names and are used as `artifact_id` in cross-repo references
- Discovered when `savings_preview_tax_exclude-cc-2683` (35 chars) was created and later failed to parse as a dependent