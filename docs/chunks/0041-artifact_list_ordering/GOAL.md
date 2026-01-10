---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/chunks.py
  - src/ve.py
  - tests/test_chunk_list.py
  - tests/test_subsystem_list.py
  - tests/test_investigation_list.py
  - tests/test_narrative_list.py
  - tests/test_artifact_ordering.py
code_references:
  - ref: src/chunks.py#Chunks::list_chunks
    implements: "Updated to use ArtifactIndex for causal ordering instead of sequence number parsing"
  - ref: src/chunks.py#Chunks::get_latest_chunk
    implements: "Updated for new list_chunks return type (list[str] instead of list[tuple[int,str]])"
  - ref: src/chunks.py#Chunks::get_current_chunk
    implements: "Updated for new list_chunks return type"
  - ref: src/ve.py#list_chunks
    implements: "CLI command with tip indicator display using ArtifactIndex"
  - ref: src/ve.py#list_narratives
    implements: "New CLI command for listing narratives in causal order with tip indicators"
  - ref: src/ve.py#list_subsystems
    implements: "Updated to use ArtifactIndex for causal ordering with tip indicators"
  - ref: src/ve.py#list_investigations
    implements: "Updated to use ArtifactIndex for causal ordering with tip indicators"
  - ref: src/task_utils.py#get_next_chunk_id
    implements: "Updated to use enumerate_chunks for directory-based ID calculation"
  - ref: src/task_utils.py#list_task_chunks
    implements: "Updated for new list_chunks return type"
  - ref: tests/test_chunks.py#TestListChunks
    implements: "Updated tests for new list_chunks return type"
  - ref: tests/test_artifact_ordering.py#TestBackwardCompatibility
    implements: "Backward compatibility tests for mixed created_after scenarios"
  - ref: tests/test_narrative_list.py
    implements: "Tests for new ve narrative list command"
narrative: null
subsystems:
  - subsystem_id: "0002-workflow_artifacts"
    relationship: implements
created_after: ["0001-implement_chunk_start-ve-001", "0002-chunk_list_command-ve-002", "0003-project_init_command", "0004-chunk_overlap_command", "0005-chunk_validate", "0006-narrative_cli_commands", "0007-cross_repo_schemas", "0008-git_local_utilities", "0009-task_init", "0010-chunk_create_task_aware", "0011-chunk_template_expansion", "0012-symbolic_code_refs", "0013-future_chunk_creation", "0014-subsystem_schemas_and_model", "0015-fix_ticket_frontmatter_null", "0016-subsystem_cli_scaffolding", "0017-subsystem_template", "0018-bidirectional_refs", "0019-subsystem_status_transitions", "0020-agent_discovery_command", "0021-spec_docs_update", "0022-subsystem_impact_resolution", "0023-canonical_template_module", "0024-remove_trivial_tests", "0025-migrate_chunks_template", "0026-template_system_consolidation", "0027-investigation_template", "0028-chunk_sequence_fix", "0029-investigation_commands", "0030-document_investigations", "0031-code_to_docs_backrefs", "0032-proposed_chunks_frontmatter", "0033-list_task_aware", "0034-ve_sync_command", "0035-external_resolve", "0036-chunk_frontmatter_model", "0037-created_after_field", "0038-artifact_ordering_index", "0039-populate_created_after", "0040-artifact_index_no_git"]
---

# Chunk Goal

## Minor Goal

Update `ve chunk list`, `ve narrative list`, `ve investigation list`, and `ve subsystem list` to use `ArtifactIndex` for causal ordering instead of parsing sequence numbers from directory names. This advances the project's goal of supporting parallel work (teams, worktrees) without sequence number conflicts.

Currently, all listing commands derive ordering from directory name prefixes (0001-, 0002-, etc.). This chunk transitions them to use the `created_after` frontmatter field via `ArtifactIndex`, enabling correct ordering even when artifacts are created in parallel branches and merged.

## Success Criteria

1. **`ve chunk list` uses ArtifactIndex**: Returns chunks in topological order based on `created_after` dependencies
2. **`ve narrative list` uses ArtifactIndex**: Returns narratives in causal order
3. **`ve investigation list` uses ArtifactIndex**: Returns investigations in causal order
4. **`ve subsystem list` uses ArtifactIndex**: Returns subsystems in causal order
5. **Fallback to sequence order**: When `created_after` is empty or results in ambiguous ordering, fall back to sequence number parsing from directory names
6. **Tip indicators displayed**: Artifacts with no dependents (graph tips) are visually marked in list output
7. **Performance acceptable**: List commands remain human-interaction fast (<1 second for typical usage)
8. **Existing tests pass**: All tests in `tests/` continue to pass