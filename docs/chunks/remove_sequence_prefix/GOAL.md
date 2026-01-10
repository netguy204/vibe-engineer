---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models.py
- src/chunks.py
- src/narratives.py
- src/investigations.py
- src/subsystems.py
- src/task_utils.py
- src/artifact_ordering.py
- tests/test_chunks.py
- tests/test_narratives.py
- tests/test_investigations.py
- tests/test_subsystems.py
- tests/test_models.py
- tests/test_chunk_start.py
- tests/conftest.py
code_references:
  - ref: src/models.py#extract_short_name
    implements: "Utility to extract short_name from directory names (handles both legacy and new formats)"
  - ref: src/models.py#ARTIFACT_ID_PATTERN
    implements: "Regex pattern accepting both legacy NNNN-name and new name-only formats"
  - ref: src/models.py#ChunkRelationship::validate_chunk_id
    implements: "Validator updated to accept both legacy and new chunk ID formats"
  - ref: src/models.py#SubsystemRelationship::validate_subsystem_id
    implements: "Validator updated to accept both legacy and new subsystem ID formats"
  - ref: src/chunks.py#Chunks::find_duplicates
    implements: "Collision detection using extract_short_name for both naming patterns"
  - ref: src/chunks.py#Chunks::create_chunk
    implements: "Create chunk with short_name only directory format, collision checking"
  - ref: src/chunks.py#Chunks::resolve_chunk_id
    implements: "Resolve chunk ID supporting legacy prefix, exact match, and short_name matching"
  - ref: src/chunks.py#Chunks::find_overlapping_chunks
    implements: "Find overlapping chunks using causal ordering via get_ancestors"
  - ref: src/narratives.py#Narratives::create_narrative
    implements: "Create narrative with short_name only directory format"
  - ref: src/narratives.py#Narratives::find_duplicates
    implements: "Collision detection for narratives"
  - ref: src/investigations.py#Investigations::create_investigation
    implements: "Create investigation with short_name only directory format"
  - ref: src/investigations.py#Investigations::find_duplicates
    implements: "Collision detection for investigations"
  - ref: src/subsystems.py#Subsystems::create_subsystem
    implements: "Create subsystem with short_name only directory format"
  - ref: src/subsystems.py#Subsystems::find_duplicates
    implements: "Collision detection for subsystems"
  - ref: src/subsystems.py#Subsystems::find_by_shortname
    implements: "Find subsystem by short_name supporting both naming patterns"
  - ref: src/subsystems.py#Subsystems::is_subsystem_dir
    implements: "Validate directory name pattern for both formats"
  - ref: src/task_utils.py#create_external_yaml
    implements: "Create external.yaml using short_name only directory format"
  - ref: src/task_utils.py#create_task_chunk
    implements: "Multi-repo chunk creation updated for short_name format"
  - ref: src/artifact_ordering.py#ArtifactIndex::get_ancestors
    implements: "Compute transitive ancestors for causal ordering (used by find_overlapping_chunks)"
  - ref: scripts/migrate_artifact_names.py
    implements: "Migration script to rename directories and update frontmatter references"
narrative: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
created_after:
- subsystem_docs_update
---

# Chunk Goal

## Minor Goal

Remove the sequence prefix from workflow artifact directory naming, transitioning from
`{NNNN}-{short_name}/` to `{short_name}/` format for all artifact types (chunks,
narratives, investigations, subsystems).

This is the right next step because:

1. **Causal ordering no longer needs sequence numbers** - The `created_after` field now
   provides causal ordering via `ArtifactIndex`. Sequence numbers were the original
   mechanism for ordering artifacts, but they're now semantically meaningless.

2. **Parallel work conflicts are eliminated** - Without sequence numbers, teams in
   separate clones or developers using multiple worktrees can create artifacts without
   collision risk. Each artifact type only needs short name uniqueness within its type.

3. **Simpler naming reduces cognitive overhead** - Shorter paths, easier to type and
   remember. `docs/chunks/add_auth_middleware/` is cleaner than
   `docs/chunks/0044-add_auth_middleware/`.

4. **Investigation 0001 identified this as Phase 4 work** - This chunk implements the
   design from investigation 0001-artifact_sequence_numbering, following the completed
   Phase 1-3 work (created_after field, ArtifactIndex, migration).

## Success Criteria

1. **New artifact creation uses short_name only** - `ve chunk start foo` creates
   `docs/chunks/foo/` not `docs/chunks/NNNN-foo/`. Same for narratives, investigations,
   and subsystems.

2. **Collision detection prevents duplicate short names** - Creating an artifact with a
   short name that already exists (within that artifact type) produces a clear error.

3. **Existing artifacts are renamed** - All existing `{NNNN}-{short_name}/` directories
   are renamed to `{short_name}/` as part of this chunk (or a separate migration script
   within the chunk directory).

4. **Code that parses directory names is updated** - Remove regex patterns for `^\d{4}-`
   and any logic that assumes sequence-prefixed naming.

5. **Both patterns supported during transition** - Existing code paths should gracefully
   handle both old and new naming formats until migration is complete (then old pattern
   support can be removed).

6. **Tests pass** - All existing tests pass, updated as needed for new naming format.

7. **Cross-references in frontmatter remain valid** - References like
   `narrative: 0003-investigations` are updated to `narrative: investigations`. (Note:
   cross-reference updates may be deferred to a separate chunk per the investigation.)