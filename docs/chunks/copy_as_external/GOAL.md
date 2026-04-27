---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/task/exceptions.py
  - src/task/external.py
  - src/ve.py
  - tests/test_artifact_copy_external.py
code_references:
  - ref: src/task/exceptions.py#TaskCopyExternalError
    implements: "Error class for artifact copy failures"
  - ref: src/task/external.py#copy_artifact_as_external
    implements: "Core function to copy external artifact as reference in target project"
  - ref: src/ve.py#copy_external
    implements: "CLI command ve artifact copy-external"
  - ref: tests/test_artifact_copy_external.py
    implements: "Test suite for copy_artifact_as_external functionality"
  - ref: src/cli/artifact.py#copy_external
    implements: "CLI artifact copy-external command after CLI modularization"
  - ref: src/task_utils.py
    implements: "Artifact copy-external command implementation re-export module"
narrative: null
subsystems: []
created_after: ["ordering_audit_seqnums", "cluster_rename", "cluster_prefix_suggest", "task_list_proposed"]
---

# Chunk Goal

## Minor Goal

The `ve artifact copy-external` command creates an external reference to an
artifact in the external artifact repository within a specified project
repository.

**Use Case**: When an artifact is created in the wrong project and later
promoted to the external artifact repository, the other project(s)
participating in the task need a way to reference it. `ve artifact promote`
creates an external reference in the source project automatically; this
command extends the same capability to the remaining projects in the task,
so any participating project can pick up an external reference to a
promoted artifact.

## Success Criteria

- `ve artifact copy-external ARTIFACT_PATH PROJECT_DIR [--name NAME]` command exists and creates an external reference
- Command must be run from within a task directory (`.ve-task.yaml` must exist in cwd or `--cwd`)
- Command auto-detects artifact type (chunk, narrative, investigation, subsystem) from the source path
- Command creates `docs/{artifact_type}/{artifact_name}/external.yaml` in the target project
- External reference contains: `artifact_type`, `artifact_id`, `repo`, `track`, `pinned` (current SHA of external repo), `created_after`
- The `repo` field uses `org/repo` format from the task configuration
- The `created_after` field is automatically populated with the current tip artifacts of that type in the target project (following the established causal ordering pattern)
- Optional `--name` argument allows renaming the artifact in the destination project
- Command validates that:
  - Running from a task directory (`.ve-task.yaml` exists)
  - The source artifact exists in the external artifact repository
  - The target project is a participating project in the task (listed in `.ve-task.yaml`)
  - The target project is a valid VE-initialized project (has `docs/chunks/`)
  - The artifact doesn't already exist in the target project (error if duplicate)
- Command reuses the existing `create_external_yaml()` function from `external_refs.py`
- All tests pass

