---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models.py
- src/task_utils.py
- src/ve.py
- src/friction.py
- docs/subsystems/workflow_artifacts/OVERVIEW.md
- tests/test_task_friction_log.py
code_references:
- ref: src/models.py#ExternalFrictionSource
  implements: External friction source reference schema for task contexts
- ref: src/models.py#FrictionFrontmatter
  implements: Friction log frontmatter schema with external_friction_sources field
- ref: src/task_utils.py#TaskFrictionError
  implements: Error class for task-aware friction operations
- ref: src/task_utils.py#create_task_friction_entry
  implements: Task-aware friction entry creation with external references
- ref: src/task_utils.py#add_external_friction_source
  implements: Add external friction source reference to project FRICTION.md
- ref: src/ve.py#log_entry
  implements: CLI handler for task-aware friction logging with --projects flag
- ref: src/ve.py#_log_entry_task_context
  implements: Task context handler for friction logging
- ref: src/friction.py#Friction::get_external_friction_sources
  implements: Retrieve external friction sources from friction log
- ref: tests/test_task_friction_log.py
  implements: Integration tests for task-aware friction logging
narrative: null
investigation: selective_artifact_linking
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
friction_entries: []
created_after:
- cluster_list_command
- cluster_naming_guidance
- friction_chunk_workflow
- narrative_consolidation
---

# Chunk Goal

## Minor Goal

Enable friction logging to participate in task context and implement selective project linking across all artifact creation workflows.

### Part 1: Friction Logging in Task Context

Currently, friction log entries are only recorded in the local project's `docs/trunk/FRICTION.md`. When working in a task context (multi-project work with an external artifact repo), friction should be surfaced as an artifact that links back to the relevant projects—just like chunks, investigations, narratives, and subsystems do.

**Key design constraint**: Unlike other artifacts which get their own directories, `FRICTION.md` is a singleton file in each project. We cannot use the standard `external.yaml` pattern. Instead, we need a mechanism for embedding external references *within* the singleton friction log—likely via frontmatter that lists external friction sources.

### Part 2: Selective Project Linking (`--projects` flag)

Implement the `--projects` flag for all artifact creation workflows so operators can selectively specify which projects an artifact should link to. This implements Option D from the selective artifact linking investigation: flag-based selection with all-projects as the default.

### Part 3: Artifact Subsystem Update

Update the `docs/subsystems/workflow_artifacts/OVERVIEW.md` to add `--projects` as a **hard invariant** for all artifact creation commands in task context. This ensures the capability is consistently available and enforced.

This is the right next step because:
1. Friction logging is currently the only artifact type that doesn't support task context, creating an inconsistency
2. The `--projects` flag is a foundational capability that makes selective linking available across all artifact types
3. Without selective linking, task-context artifacts create noise in project chunk histories by linking to irrelevant projects

## Success Criteria

1. **Friction logging in task context works**: When `ve friction log` is run in a task context:
   - A friction entry is created in the external artifact repo's `docs/trunk/FRICTION.md`
   - The friction entry includes metadata indicating which projects it relates to
   - Projects specified via `--projects` (or all projects if omitted) receive a reference to the external friction entry in their local `FRICTION.md` (via frontmatter or inline reference)

2. **--projects flag available on all artifact commands**: The following commands accept `--projects`:
   - `ve chunk create`
   - `ve investigation create`
   - `ve narrative create`
   - `ve subsystem discover`
   - `ve friction log`

3. **Default behavior preserved**: When `--projects` is omitted, all projects in the task context receive external.yaml references (or equivalent for friction) (backward compatible)

4. **Flexible project specification**: The `--projects` flag accepts:
   - Comma-separated project names (e.g., `--projects service-a,service-b`)
   - Short project names (e.g., `--projects service-a`)
   - Full org/repo refs (e.g., `--projects acme/service-a`)

5. **Task utils integration**: The `create_task_*` functions in `src/task_utils.py` accept an optional `projects` parameter that filters the project iteration loop

6. **Subsystem invariant documented**: `docs/subsystems/workflow_artifacts/OVERVIEW.md` includes a new hard invariant requiring all task-aware artifact creation commands to support `--projects`

7. **All tests pass**: Existing tests continue to pass; new tests cover selective project linking