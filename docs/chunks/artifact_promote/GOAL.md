---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/task_utils.py
  - src/ve.py
  - tests/test_artifact_promote.py
code_references:
  - ref: src/task_utils.py#TaskPromoteError
    implements: "Exception class for user-friendly promotion error messages"
  - ref: src/task_utils.py#find_task_directory
    implements: "Walk up from artifact path to find task directory containing .ve-task.yaml"
  - ref: src/task_utils.py#identify_source_project
    implements: "Determine which project (org/repo) contains the artifact being promoted"
  - ref: src/task_utils.py#add_dependents_to_artifact
    implements: "Generic helper to add dependents to any artifact type's main file"
  - ref: src/task_utils.py#_get_artifact_created_after
    implements: "Parse created_after field from artifact's main file frontmatter"
  - ref: src/task_utils.py#promote_artifact
    implements: "Core promotion logic: copy to external repo, update frontmatter, create external.yaml"
  - ref: src/ve.py#artifact
    implements: "CLI command group for artifact management commands"
  - ref: src/ve.py#promote
    implements: "CLI command ve artifact promote <path> [--name]"
  - ref: tests/test_artifact_promote.py#TestPromoteArtifactCoreFunction
    implements: "Unit tests for promote_artifact() function"
  - ref: tests/test_artifact_promote.py#TestPromoteArtifactCLI
    implements: "CLI integration tests for ve artifact promote command"
narrative: null
subsystems:
  - subsystem_id: workflow_artifacts
    relationship: uses
created_after: ["task_aware_investigations", "task_aware_subsystem_cmds"]
---

# Chunk Goal

## Minor Goal

Add a `ve artifact promote` command that moves a local artifact (chunk, investigation, narrative, or subsystem) from a project's `docs/` directory to the task-level external artifact repository. This addresses a workflow gap discovered during the `xr_vibe_integration` investigation: when an artifact is created locally but later discovered to span multiple projects, there's no way to "promote" it to task-level.

This advances the trunk goal by maintaining document health over time—artifacts should live at the appropriate scope. The workflow should make it easy to correct artifact placement after the fact, supporting the principle that "following the workflow must maintain the health of documents over time."

### Command Signature

```
ve artifact promote <artifact-path> [--name <new-name>]
```

- `<artifact-path>`: Path to a local artifact (e.g., `docs/investigations/xr_vibe_integration`)
- `--name`: Optional new name for the artifact in the destination (enables renaming during promotion)

### Scope

This command is specifically for **task-level promotion**: moving an artifact from a project to the external artifact repository, leaving behind an external reference. For moving artifacts between projects without external references, users should use shell commands (`mv`).

### What the Command Does

1. **Detects context**: Walks up from artifact path to find task directory (`.ve-task.yaml`), identifies source project's org/repo by matching against task config's projects list
2. **Validates**: Errors if destination artifact already exists in external repo (unless `--name` provides alternate name)
3. **Copies**: Moves artifact directory to external repo's `docs/<type>/<dest-name>/`
4. **Updates promoted artifact**: Sets `created_after` to external repo tips (inserting it as newest in external repo's causal chain), adds source project to `dependents`
5. **Creates reference**: Clears source directory, creates `external.yaml` with `created_after` from the **original artifact** (preserving local causal position)
6. **Does NOT auto-commit**: Makes filesystem changes only; user commits manually

## Success Criteria

1. **CLI command exists**: `ve artifact promote <artifact-path> [--name <new-name>]` is available

2. **Task context detection**: Walks up from artifact path to find task directory; errors with clear message if not in task context

3. **Project identification**: Determines source project's org/repo by matching artifact path against task config's projects list

4. **Artifact type inference**: Detects artifact type from path structure (`docs/chunks/`, `docs/investigations/`, etc.)

5. **Collision detection**: Errors if destination name already exists in external repo; `--name` flag allows specifying alternate destination name

6. **Move operation**: Copies entire artifact directory to external repo's `docs/<type>/<dest-name>/`, preserving all files and subdirectories

7. **External reference creation**: Clears source directory and creates `external.yaml` with:
   - `artifact_type`: The detected type
   - `artifact_id`: The destination name (source name or `--name` value)
   - `repo`: The external artifact repo from task config
   - `pinned`: Current SHA of external repo
   - `created_after`: The **original artifact's** `created_after` value (preserves local causal position)

8. **Promoted artifact causal ordering**: Updates the promoted artifact's `created_after` in its frontmatter to reference the external repo's current tips (inserts it as the newest artifact in the external repo's causal chain)

9. **Dependent tracking**: Updates promoted artifact's frontmatter to add source project to `dependents` list

10. **Idempotency protection**: Refuses to promote artifacts that are already external references (have `external.yaml` without main document)

11. **No auto-commit**: Command makes filesystem changes only; does not run git commands

12. **Tests pass**: Unit tests cover the promote workflow including:
    - Happy path promotion
    - `--name` renaming
    - Collision detection and error
    - Already-external rejection
    - Task context detection from nested project directory
    - Correct `created_after` handling for both promoted artifact and external.yaml

