---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/task_utils.py
- src/ve.py
- tests/test_artifact_remove_external.py
code_references:
- ref: src/task_utils.py#TaskRemoveExternalError
  implements: "Error class for remove-external failures with user-friendly messages"
- ref: src/task_utils.py#remove_dependent_from_artifact
  implements: "Helper to remove dependent entry from artifact frontmatter"
- ref: src/task_utils.py#remove_artifact_from_external
  implements: "Core function removing external.yaml and updating dependents"
- ref: src/ve.py#remove_external
  implements: "CLI command ve artifact remove-external"
- ref: tests/test_artifact_remove_external.py#TestRemoveArtifactFromExternalCoreFunction
  implements: "Core function tests for removal, idempotency, cleanup, orphan warning"
- ref: tests/test_artifact_remove_external.py#TestRemoveArtifactFromExternalCLI
  implements: "CLI command integration tests"
narrative: null
investigation: selective_artifact_linking
subsystems: []
created_after:
- friction_template_and_cli
- orch_conflict_template_fix
- orch_sandbox_enforcement
- orch_blocked_lifecycle
---

# Chunk Goal

## Minor Goal

Add `ve artifact remove-external` command to remove an artifact's link from a project. This is the inverse of `copy-external` and completes the artifact-to-project lifecycle by enabling scope reduction after creation.

The removal must be comprehensive to maintain consistency:
1. Delete the `external.yaml` from the project's artifact directory
2. Remove the dependent entry from the artifact's frontmatter in the external repo
3. Clean up empty directories if the artifact directory becomes empty

See investigation `docs/investigations/selective_artifact_linking/OVERVIEW.md` for full context.

## Success Criteria

- `ve artifact remove-external my_chunk svc-a` removes external.yaml from project
- Command updates artifact's `dependents` list in external repo to remove the project entry
- Empty artifact directories are cleaned up after removal
- Command is idempotent (no error if external.yaml doesn't exist)
- Command warns when removing the last project link (artifact becomes orphaned)
- Accepts flexible input: full `org/repo` or just `repo` name, flexible artifact path
- Tests cover removal, dependent update, cleanup, idempotency, and orphan warning

