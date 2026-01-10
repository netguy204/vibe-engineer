---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models.py
- src/artifact_ordering.py
- src/task_utils.py
- tests/test_task_models.py
- tests/test_task_utils.py
- tests/test_chunks.py
code_references:
  - ref: src/models.py#ArtifactType
    implements: "Moved ArtifactType enum from artifact_ordering.py to models.py"
  - ref: src/models.py#ExternalArtifactRef
    implements: "Generic external artifact reference model with artifact_type and artifact_id fields"
  - ref: src/models.py#ChunkDependent
    implements: "Updated to use ExternalArtifactRef for cross-repo references"
  - ref: src/models.py#ChunkFrontmatter
    implements: "Updated dependents field to use ExternalArtifactRef"
  - ref: src/artifact_ordering.py
    implements: "Import ArtifactType from models.py instead of defining locally"
  - ref: src/task_utils.py#load_external_ref
    implements: "Updated to return ExternalArtifactRef"
  - ref: src/task_utils.py#create_external_yaml
    implements: "Updated to use artifact_type and artifact_id fields"
  - ref: src/task_utils.py#create_task_chunk
    implements: "Updated to use ExternalArtifactRef format for dependents"
  - ref: src/task_utils.py#list_task_chunks
    implements: "Updated to handle ExternalArtifactRef objects"
narrative: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
created_after: ["external_chunk_causal"]
---

# Chunk Goal

## Minor Goal

Replace the chunk-specific `ExternalChunkRef` model with a generic `ExternalArtifactRef` model
that can represent external references to any workflow artifact type (chunks, narratives,
investigations, subsystems). This addresses the "External References Only for Chunks" deviation
in the workflow_artifacts subsystem by establishing a foundation for cross-repo support
across all workflow types.

The current `ExternalChunkRef` model has a `chunk` field that only makes sense for chunks.
The new `ExternalArtifactRef` model will have:
- `artifact_type` field (enum: CHUNK, NARRATIVE, INVESTIGATION, SUBSYSTEM)
- `artifact_id` field (replaces `chunk` field - the short name of the referenced artifact)

This is the first step in the External Reference Consolidation sequence outlined in the
workflow_artifacts subsystem. Subsequent chunks will build on this foundation to add
generic utilities and extend commands to all workflow types.

## Success Criteria

1. **ArtifactType enum moved to models.py** - Relocate the `ArtifactType` enum from
   `artifact_ordering.py` to `models.py` to avoid circular imports. Update
   `artifact_ordering.py` to import from models.

2. **ExternalArtifactRef model exists in models.py** with:
   - `artifact_type: ArtifactType` field
   - `artifact_id: str` field (replaces the old `chunk` field)
   - `repo: str` field (unchanged from ExternalChunkRef)
   - `track: str | None` field (unchanged)
   - `pinned: str | None` field (unchanged)
   - `created_after: list[str]` field (unchanged)
   - Same validators as ExternalChunkRef (repo format, pinned SHA format, artifact_id format)

3. **ExternalChunkRef is removed** - Clean replacement, no backward compatibility needed
   (no external.yaml files exist in any Vibe Engineering projects yet)

4. **All existing code using ExternalChunkRef is updated** to use ExternalArtifactRef:
   - `src/task_utils.py` (create_external_yaml, load_external_ref, etc.)
   - `src/artifact_ordering.py` (import ArtifactType from models, update any ExternalChunkRef refs)
   - Any CLI commands that create/read external.yaml files

5. **All tests pass** including any new tests for ExternalArtifactRef validation

