---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/task_utils.py
- src/ve.py
- tests/test_task_chunk_list.py
- tests/test_task_narrative_list.py
- tests/test_task_investigation_list.py
- tests/test_task_subsystem_list.py
- docs/subsystems/workflow_artifacts/OVERVIEW.md
code_references:
- ref: src/task_utils.py#TaskArtifactListError
  implements: Error class for task artifact listing failures
- ref: src/task_utils.py#_list_local_artifacts
  implements: List local artifacts for a project, excluding external references
- ref: src/task_utils.py#list_task_artifacts_grouped
  implements: Grouped task artifact listing with external and local sections
- ref: src/ve.py#_format_grouped_artifact_list
  implements: Output formatter for grouped artifact listing display
- ref: src/ve.py#_list_task_chunks
  implements: Updated CLI handler for task-aware chunk listing with grouped output
- ref: src/ve.py#_list_task_narratives_cmd
  implements: Updated CLI handler for task-aware narrative listing with grouped output
- ref: src/ve.py#_list_task_investigations
  implements: Updated CLI handler for task-aware investigation listing with grouped output
- ref: src/ve.py#_list_task_subsystems
  implements: Updated CLI handler for task-aware subsystem listing with grouped output
- ref: tests/test_task_chunk_list.py
  implements: Tests for grouped chunk listing in task context
- ref: tests/test_task_narrative_list.py
  implements: Tests for grouped narrative listing in task context
- ref: tests/test_task_investigation_list.py
  implements: Tests for grouped investigation listing in task context
- ref: tests/test_task_subsystem_list.py
  implements: Tests for grouped subsystem listing in task context
- ref: docs/subsystems/workflow_artifacts/OVERVIEW.md
  implements: Subsystem documentation update for grouped listing behavior
narrative: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
created_after: ["task_aware_investigations", "task_aware_subsystem_cmds"]
---

# Chunk Goal

## Minor Goal

Enhance artifact list commands (`ve chunk list`, `ve narrative list`, `ve subsystem list`, `ve investigation list`) to show grouped-by-location output when running from a task context. Currently, these commands only show artifacts from the external repo when at task root. The new behavior shows the complete cross-project picture: external repo artifacts first, then each participating project's local artifacts, with each group preserving its own causal ordering.

This is an extension to the workflow_artifacts subsystem—the grouped listing concept should be documented there and the implementation should comply with subsystem patterns.

## Success Criteria

1. **Default task context behavior**: Running `ve {artifact} list` from a task root directory shows artifacts grouped by location:
   - External repo artifacts first (labeled with the external repo org/repo)
   - Each participating project's local artifacts (labeled with org/repo)
   - Each group preserves its own causal ordering (topological sort by `created_after`)

2. **Output format**:
   ```
   # External Artifacts (org/external-repo)
   cross_cutting_feature [IMPLEMENTING] (tip)
     → referenced by: org/project-a, org/project-b

   # org/project-a (local)
   local_fix_a [ACTIVE] (tip)

   # org/project-b (local)
   local_fix_b [IMPLEMENTING] (tip)
   ```

   External artifacts show which projects reference them (from the `dependents` field in frontmatter). Local artifacts in each project section do not show references.

3. **All artifact types supported**: The grouped listing works for chunks, narratives, subsystems, and investigations. Non-task context behavior remains unchanged.

4. **Subsystem documentation**: Add a new section to `docs/subsystems/workflow_artifacts/OVERVIEW.md` documenting the grouped listing behavior for task contexts.

5. **Tests verify**:
   - Grouped output format for each artifact type
   - Per-group causal ordering is preserved
   - Non-task context behavior unchanged

