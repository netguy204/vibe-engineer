---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- docs/chunks/0042-causal_ordering_migration/migrate.py
- tests/test_migration_utilities.py
code_references:
- ref: docs/chunks/0042-causal_ordering_migration/migrate.py#extract_short_name
  implements: Extract short name from directory names with optional ticket suffixes
- ref: docs/chunks/0042-causal_ordering_migration/migrate.py#extract_sequence_number
  implements: Extract numeric prefix for sorting artifacts
- ref: docs/chunks/0042-causal_ordering_migration/migrate.py#parse_frontmatter
  implements: Parse YAML frontmatter from markdown files
- ref: docs/chunks/0042-causal_ordering_migration/migrate.py#update_frontmatter
  implements: Update created_after field while preserving other frontmatter
- ref: docs/chunks/0042-causal_ordering_migration/migrate.py#migrate_artifact_type
  implements: Migrate single artifact type creating linear created_after chain
- ref: docs/chunks/0042-causal_ordering_migration/migrate.py#migrate_all
  implements: Orchestrate migration of all artifact types (chunks, narratives, investigations,
    subsystems)
- ref: docs/chunks/0042-causal_ordering_migration/migrate.py#main
  implements: CLI entry point with dry-run preview and verification guidance
- ref: tests/test_migration_utilities.py
  implements: Unit tests for migration script utilities
narrative: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
created_after:
- artifact_list_ordering
---

# Chunk Goal

## Minor Goal

Run a one-time migration to populate `created_after` fields for all existing artifacts (chunks, narratives, investigations, subsystems).

This is a one-time operation for this repository only. Future users of Vibe Engineering will get causal ordering from the start, so no CLI command is needed. The migration script will be stored in this chunk's folder (`docs/chunks/0042-causal_ordering_migration/`) for historical reference.

This is Phase 3 of the investigation's phased approach - the foundation (chunks 1-2) and creation flow (chunks 3-4) are already implemented. This chunk bridges existing artifacts into the new system.

## Success Criteria

1. **All artifact types migrated**: Chunks, narratives, investigations, and subsystems have `created_after` populated
2. **Linear chain creation**: For each artifact type, sorted by sequence number with each artifact's `created_after` set to `[previous artifact's short name]`
3. **First artifacts handled correctly**: First artifact of each type gets empty `created_after: []`
4. **Existing frontmatter preserved**: Only `created_after` field added/updated; other frontmatter unchanged
5. **ArtifactIndex validates result**: After migration, `ve chunk list` (and other list commands) use causal ordering successfully
6. **Script retained**: Migration script stored in `docs/chunks/0042-causal_ordering_migration/` for future reference

## Context from Investigation

This chunk is proposed chunk 5 from `docs/investigations/0001-artifact_sequence_numbering/OVERVIEW.md`. The investigation proposed a CLI command, but since this is a one-time migration for this repo only, a standalone script stored in the chunk folder is more appropriate.

**Relevant prototypes**: The investigation created `prototypes/migration_strategy.py` that demonstrates the migration approach.

**Migration strategy from investigation findings**:
- Use sequence order to create linear chain
- Each artifact's `created_after` = `[previous artifact's short name]`
- First artifact of each type has `created_after: []`
- Result: single tip per artifact type (most recent artifact)

**Short name extraction**: The short name is the portion after the sequence prefix (e.g., `0037-created_after_field` → `created_after_field`).