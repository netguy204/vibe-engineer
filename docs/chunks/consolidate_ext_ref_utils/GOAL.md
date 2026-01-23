---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/external_refs.py
- src/task_utils.py
- src/sync.py
- src/external_resolve.py
- src/artifact_ordering.py
- tests/test_external_refs.py
- tests/test_task_utils.py
code_references:
  - ref: src/external_refs.py
    implements: "Consolidated external artifact reference utilities module"
  - ref: src/external_refs.py#ARTIFACT_MAIN_FILE
    implements: "Mapping of artifact types to main document file names"
  - ref: src/external_refs.py#ARTIFACT_DIR_NAME
    implements: "Mapping of artifact types to directory names"
  - ref: src/external_refs.py#get_main_file_for_type
    implements: "Utility to get main file name for an artifact type"
  - ref: src/external_refs.py#is_external_artifact
    implements: "Generic detection of external artifact references"
  - ref: src/external_refs.py#detect_artifact_type_from_path
    implements: "Artifact type detection from directory path"
  - ref: src/external_refs.py#load_external_ref
    implements: "Load ExternalArtifactRef from external.yaml"
  - ref: src/external_refs.py#create_external_yaml
    implements: "Create external.yaml for any artifact type"
  - ref: src/task_utils.py#is_external_chunk
    implements: "Convenience wrapper using is_external_artifact for chunks"
  - ref: src/artifact_ordering.py#_enumerate_artifacts
    implements: "Updated to use is_external_artifact from external_refs"
  - ref: tests/test_external_refs.py
    implements: "Test coverage for external_refs module"
narrative: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
created_after: ["consolidate_ext_refs", "rename_chunk_start_to_create", "valid_transitions"]
---

# Chunk Goal

## Minor Goal

Create a dedicated `src/external_refs.py` module that consolidates external artifact
reference utilities. This supports the project's goal of maintaining consistent
tooling across all workflow artifact types (chunks, narratives, investigations,
subsystems) by providing generic utilities that work for any artifact type.

Currently, external reference utilities (`is_external_chunk`, `load_external_ref`,
`create_external_yaml`) are located in `src/task_utils.py` and are chunk-specific
in naming even though the underlying `ExternalArtifactRef` model (from chunk
`consolidate_ext_refs`) already supports all artifact types. This chunk extracts
and generalizes these utilities to enable future chunks that extend external
reference support to narratives, investigations, and subsystems.

## Success Criteria

1. **New module created**: `src/external_refs.py` exists with consolidated utilities
2. **Generic detection**: `is_external_artifact(path, artifact_type)` function detects
   external references for any artifact type by checking for `external.yaml` without
   the type-specific main document (GOAL.md for chunks, OVERVIEW.md for others)
3. **Type detection**: `detect_artifact_type_from_path(path)` infers artifact type from
   directory path (e.g., `docs/chunks/` → CHUNK, `docs/narratives/` → NARRATIVE)
4. **Unified loading**: `load_external_ref(path)` returns `ExternalArtifactRef` (already
   type-agnostic from `consolidate_ext_refs`)
5. **Unified creation**: `create_external_yaml(path, ref)` exists in the new module
   (migrated from `task_utils.py`)
6. **Callers updated**: All import sites (`sync.py`, `external_resolve.py`, `task_utils.py`)
   updated to import from `external_refs` directly
7. **Tests pass**: Existing tests continue to pass, new tests cover the generic utilities
8. **ArtifactIndex updated**: `src/artifact_ordering.py` uses the new
   `is_external_artifact()` for detecting external references