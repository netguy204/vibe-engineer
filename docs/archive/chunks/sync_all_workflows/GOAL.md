---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/sync.py
- src/ve.py
- tests/test_sync.py
- tests/test_sync_cli.py
code_references:
  - ref: src/sync.py#SyncResult
    implements: "SyncResult dataclass with artifact_type field and formatted_id property"
  - ref: src/sync.py#find_external_refs
    implements: "Generalized external ref finder that searches all workflow artifact directories"
  - ref: src/sync.py#sync_task_directory
    implements: "Task directory sync with artifact type filtering support"
  - ref: src/sync.py#sync_single_repo
    implements: "Single repo sync with artifact type filtering support"
  - ref: src/ve.py#sync
    implements: "CLI sync command with --type and --artifact options"
  - ref: src/ve.py#_sync_task_directory
    implements: "Task directory sync helper with artifact type filtering"
  - ref: src/ve.py#_sync_single_repo
    implements: "Single repo sync helper with artifact type filtering"
  - ref: src/ve.py#_display_sync_results
    implements: "Display sync results with artifact type prefix"
narrative: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
created_after: ["consolidate_ext_ref_utils"]
---

# Chunk Goal

## Minor Goal

Extend `ve sync` to find and update `external.yaml` files across all workflow artifact directories (`docs/chunks/`, `docs/narratives/`, `docs/investigations/`, `docs/subsystems/`), not just chunks.

Currently, `sync.py` only searches `docs/chunks/` for external references (see `find_external_refs()` at line 39). This limits `ve sync` to chunk-only use, but the `ExternalArtifactRef` model and `external_refs.py` utilities now support all workflow types. This chunk completes the sync functionality to support the full workflow artifact system.

This enables teams using cross-repo workflows for narratives, investigations, or subsystems to keep their pinned SHAs up to date using the same `ve sync` command.

## Success Criteria

- `find_external_refs()` generalized to accept an artifact type parameter (or iterate all types) and search the corresponding directory (`docs/narratives/`, `docs/investigations/`, `docs/subsystems/`)
- `sync_task_directory()` and `sync_single_repo()` updated to process external references from all artifact type directories
- `SyncResult` updated to include artifact type information in its output (e.g., `narrative:my_narrative` vs `chunk:my_chunk`)
- Existing `--chunk` CLI filter option extended or complemented with a more general `--artifact` option
- Unit tests verify that external.yaml files in each artifact type directory are discovered and synced
- All existing tests continue to pass (backward compatibility)

