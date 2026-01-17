# Phase 1: Chunk Inventory & Clustering

## Executive Summary

- **Total chunks analyzed**: 118
- **Status breakdown**: 116 ACTIVE, 1 HISTORICAL, 1 FUTURE
- **Unique files referenced**: 131+
- **High-touch files (10+ chunk refs)**: 8 files
- **Existing subsystems to reconcile**: 2 (template_system, workflow_artifacts)
- **Existing narratives**: 3 (cross_repo_chunks, investigations, subsystem_documentation)

## Chunk Inventory

### Status Distribution

| Status | Count | Notes |
|--------|-------|-------|
| ACTIVE | 116 | Include fully in synthesis |
| HISTORICAL | 1 | coderef_format_prompting (provenance only) |
| FUTURE | 1 | orch_unblock_transition (exclude from synthesis) |

### Full Chunk List by Status

#### ACTIVE Chunks (116)

| Chunk | Narrative | Primary Files |
|-------|-----------|---------------|
| accept_full_artifact_paths | null | src/external_refs.py, src/task_utils.py, src/ve.py |
| agent_discovery_command | subsystem_documentation | src/templates/commands/subsystem-discover.md |
| artifact_copy_backref | null | src/task_utils.py |
| artifact_index_no_git | null | src/artifact_ordering.py |
| artifact_list_ordering | null | src/chunks.py, src/task_utils.py, src/ve.py |
| artifact_ordering_index | null | src/artifact_ordering.py, src/models.py |
| artifact_promote | null | src/task_utils.py, src/ve.py |
| background_keyword_semantic | null | src/templates/claude/CLAUDE.md.jinja2 |
| bidirectional_refs | subsystem_documentation | src/chunks.py, src/models.py, src/subsystems.py |
| bug_type_field | null | src/models.py, src/templates/chunk/GOAL.md.jinja2 |
| causal_ordering_migration | null | migration scripts |
| chunk_create_guard | null | src/chunks.py |
| chunk_create_task_aware | cross_repo_chunks | src/external_refs.py, src/models.py, src/task_utils.py, src/ve.py |
| chunk_frontmatter_model | null | src/chunks.py, src/models.py |
| chunk_list_command-ve-002 | null | src/chunks.py, src/ve.py |
| chunk_list_repo_source | null | src/task_utils.py, src/ve.py |
| chunk_overlap_command | null | src/chunks.py, src/ve.py |
| chunk_template_expansion | null | src/chunks.py, src/templates/chunk/PLAN.md.jinja2 |
| chunk_validate | null | src/chunks.py, src/models.py, src/ve.py |
| cluster_list_command | null | src/cluster_analysis.py, src/ve.py |
| cluster_naming_guidance | null | src/templates/claude/CLAUDE.md.jinja2 |
| cluster_prefix_suggest | null | src/chunks.py, src/ve.py |
| cluster_rename | null | src/cluster_rename.py, src/ve.py |
| cluster_seed_naming | null | src/templates/commands/chunk-create.md.jinja2 |
| cluster_subsystem_prompt | null | src/cluster_analysis.py, src/project.py |
| code_to_docs_backrefs | null | templates, CLAUDE.md |
| consolidate_ext_ref_utils | null | src/external_refs.py, src/external_resolve.py |
| consolidate_ext_refs | null | src/external_refs.py, src/models.py |
| copy_as_external | null | src/task_utils.py, src/ve.py |
| cross_repo_schemas | cross_repo_chunks | src/models.py |
| deferred_worktree_creation | null | src/orchestrator/ |
| document_investigations | investigations | CLAUDE.md, docs/trunk/SPEC.md |
| external_chunk_causal | null | src/artifact_ordering.py, src/external_refs.py |
| external_resolve | null | src/external_resolve.py, src/sync.py |
| external_resolve_all_types | null | src/external_resolve.py, src/ve.py |
| fix_ticket_frontmatter_null | null | src/templates/chunk/GOAL.md |
| friction_chunk_linking | null | src/chunks.py, src/models.py |
| friction_chunk_workflow | null | src/templates/commands/ |
| friction_claude_docs | null | src/templates/claude/CLAUDE.md.jinja2 |
| friction_noninteractive | null | src/ve.py |
| friction_template_and_cli | null | src/friction.py, src/models.py |
| future_chunk_creation | null | src/chunks.py, src/task_utils.py |
| git_local_utilities | null | src/git_utils.py |
| implement_chunk_start-ve-001 | null | src/chunks.py, src/ve.py |
| init_creates_chunks_dir | null | src/project.py |
| investigation_chunk_refs | null | src/chunks.py, src/models.py |
| investigation_commands | null | src/investigations.py, src/ve.py |
| investigation_template | null | src/templates/investigation/OVERVIEW.md.jinja2 |
| jinja_backrefs | null | src/templates/ |
| learning_philosophy_docs | null | src/templates/claude/CLAUDE.md.jinja2 |
| list_task_aware | null | src/task_utils.py, src/ve.py |
| migrate_chunks_template | null | src/chunks.py, src/templates/chunk/ |
| narrative_backreference_support | null | src/chunks.py |
| narrative_cli_commands | null | src/narratives.py, src/ve.py |
| narrative_consolidation | null | src/chunks.py, src/ve.py |
| orch_activate_on_inject | null | src/orchestrator/ |
| orch_agent_question_tool | null | src/orchestrator/agent.py |
| orch_agent_skills | null | src/orchestrator/agent.py |
| orch_attention_queue | null | src/orchestrator/ |
| orch_attention_reason | null | src/orchestrator/ |
| orch_blocked_lifecycle | null | src/orchestrator/ |
| orch_broadcast_invariant | null | src/orchestrator/scheduler.py |
| orch_conflict_oracle | null | src/orchestrator/ |
| orch_conflict_template_fix | null | src/orchestrator/oracle.py |
| orch_dashboard | null | src/orchestrator/ |
| orch_foundation | null | src/orchestrator/ |
| orch_inject_path_compat | null | src/ve.py |
| orch_inject_validate | null | src/chunks.py, src/orchestrator/ |
| orch_mechanical_commit | null | src/orchestrator/ |
| orch_question_forward | null | src/orchestrator/ |
| orch_sandbox_enforcement | null | src/orchestrator/agent.py |
| orch_scheduling | null | src/orchestrator/ |
| orch_submit_future_cmd | null | templates |
| orch_tcp_port | null | src/orchestrator/daemon.py |
| orch_verify_active | null | src/orchestrator/ |
| ordering_active_only | null | src/artifact_ordering.py |
| ordering_audit_seqnums | null | templates |
| ordering_field | null | src/models.py |
| ordering_field_clarity | null | src/templates/chunk/GOAL.md.jinja2 |
| ordering_remove_seqno | null | multiple files |
| populate_created_after | null | multiple files |
| project_init_command | null | src/project.py, src/ve.py |
| proposed_chunks_frontmatter | null | src/chunks.py, src/models.py |
| remove_external_ref | null | src/task_utils.py, src/ve.py |
| remove_trivial_tests | null | docs, tests |
| rename_chunk_start_to_create | null | src/ve.py |
| respect_future_intent | null | templates |
| restore_template_content | null | templates |
| selective_artifact_friction | null | src/friction.py, src/task_utils.py |
| selective_project_linking | null | src/task_utils.py, src/ve.py |
| spec_docs_update | null | docs/trunk/SPEC.md |
| subsystem_cli_scaffolding | null | src/subsystems.py, src/ve.py |
| subsystem_docs_update | null | docs/subsystems/ |
| subsystem_impact_resolution | null | src/subsystems.py, src/ve.py |
| subsystem_schemas_and_model | null | src/models.py, src/subsystems.py |
| subsystem_status_transitions | null | src/models.py, src/subsystems.py |
| subsystem_template | null | templates |
| symbolic_code_refs | null | src/chunks.py, src/models.py, src/symbols.py |
| sync_all_workflows | null | src/sync.py, src/ve.py |
| task_aware_investigations | null | src/task_utils.py, src/ve.py |
| task_aware_narrative_cmds | null | src/task_utils.py, src/ve.py |
| task_aware_subsystem_cmds | null | src/task_utils.py, src/ve.py |
| task_chunk_validation | null | src/chunks.py, src/ve.py |
| task_config_local_paths | null | src/git_utils.py, src/task_init.py |
| task_init | null | src/task_init.py, src/ve.py |
| task_init_scaffolding | null | src/project.py, src/task_init.py |
| task_list_proposed | null | src/task_utils.py, src/ve.py |
| task_qualified_refs | null | src/chunks.py, src/models.py, src/symbols.py |
| task_status_command | null | src/task_utils.py, src/ve.py |
| taskdir_context_cmds | null | src/chunks.py, src/task_utils.py |
| template_drift_prevention | null | src/project.py, src/template_system.py |
| template_system_consolidation | null | src/template_system.py, templates |
| template_unified_module | null | src/template_system.py |
| update_crossref_format | null | docs/, src/ |
| valid_transitions | null | src/chunks.py, src/models.py, src/ve.py |
| ve_sync_command | null | src/sync.py, src/ve.py |

#### HISTORICAL Chunks (1)

| Chunk | Status | Notes |
|-------|--------|-------|
| coderef_format_prompting | HISTORICAL | Superseded by symbolic_code_refs |

#### FUTURE Chunks (1)

| Chunk | Status | Notes |
|-------|--------|-------|
| orch_unblock_transition | FUTURE | Not yet implemented - exclude from synthesis |

## File Overlap Analysis

### High-Touch Files (10+ chunk references)

| File | Chunk Count | Subsystem Candidate |
|------|-------------|---------------------|
| src/ve.py | 54 | Multiple (CLI entry point) |
| src/models.py | 27 | workflow_artifacts (schemas) |
| src/chunks.py | 26 | workflow_artifacts (chunk manager) |
| src/task_utils.py | 24 | cross_repo_operations |
| src/templates/claude/CLAUDE.md.jinja2 | 14 | template_system |
| tests/test_chunks.py | 13 | workflow_artifacts (tests) |
| src/orchestrator/scheduler.py | 11 | orchestrator |
| src/templates/chunk/GOAL.md.jinja2 | 11 | template_system |
| src/subsystems.py | 11 | workflow_artifacts |
| src/orchestrator/api.py | 9 | orchestrator |

### Orchestrator Module Files

| File | Chunk Count |
|------|-------------|
| src/orchestrator/scheduler.py | 11 |
| src/orchestrator/api.py | 9 |
| src/orchestrator/models.py | 8 |
| src/orchestrator/state.py | 8 |
| src/orchestrator/agent.py | 7 |
| src/orchestrator/daemon.py | 3 |
| src/orchestrator/client.py | 3 |
| src/orchestrator/worktree.py | 3 |
| src/orchestrator/oracle.py | 2 |
| src/orchestrator/websocket.py | 1 |
| src/orchestrator/__init__.py | 2 |

## Prefix Clusters

### Major Prefix Clusters (5+ chunks)

| Prefix | Chunks | Primary Business Capability |
|--------|--------|----------------------------|
| orch_* | 21 | Parallel agent orchestration |
| task_* | 10 | Cross-repo/task directory operations |
| chunk_* | 8 | Chunk lifecycle management |
| cluster_* | 6 | Chunk naming/clustering utilities |
| subsystem_* | 6 | Subsystem lifecycle management |
| friction_* | 5 | Friction log tracking |
| ordering_* | 5 | Artifact causal ordering |
| artifact_* | 5 | Artifact utilities (ordering, index) |

### Medium Prefix Clusters (3-4 chunks)

| Prefix | Chunks | Primary Business Capability |
|--------|--------|----------------------------|
| template_* | 3 | Template rendering system |
| narrative_* | 3 | Narrative lifecycle management |
| investigation_* | 3 | Investigation lifecycle management |
| external_* | 3 | External reference resolution |

### Small/Singleton Prefixes (1-2 chunks)

| Prefix | Chunks | Notes |
|--------|--------|-------|
| consolidate_* | 2 | External ref consolidation |
| selective_* | 2 | Selective project linking |
| remove_* | 2 | Removal utilities |
| (others) | 1 each | Various specific features |

## Prefix vs File Cluster Alignment

| Prefix Cluster | Aligns With File Cluster? | Notes |
|----------------|---------------------------|-------|
| orch_* | **YES** | All chunks touch src/orchestrator/ exclusively |
| task_* | **YES** | All touch src/task_utils.py, src/ve.py |
| chunk_* | **PARTIAL** | Most touch src/chunks.py, but some touch models.py |
| cluster_* | **YES** | All touch src/cluster_analysis.py or src/cluster_rename.py |
| subsystem_* | **YES** | All touch src/subsystems.py |
| friction_* | **YES** | All touch src/friction.py or friction templates |
| ordering_* | **YES** | All touch src/artifact_ordering.py |
| template_* | **YES** | All touch src/template_system.py |
| narrative_* | **YES** | All touch src/narratives.py |
| investigation_* | **YES** | All touch src/investigations.py |

## Capability Clusters

### Cluster: Parallel Agent Orchestration
- **Chunks**: orch_* (21 chunks)
- **Shared files**: src/orchestrator/* (all files)
- **Prefix alignment**: Perfect (orch_*)
- **Rationale**: All chunks work together to implement parallel agent execution with
  scheduling, conflict detection, dashboard, and work unit lifecycle management

### Cluster: Cross-Repository Operations
- **Chunks**: task_* (10), consolidate_ext_* (2), external_* (3), copy_as_external,
  cross_repo_schemas, selective_* (2), accept_full_artifact_paths
- **Shared files**: src/task_utils.py, src/external_refs.py, src/external_resolve.py
- **Prefix alignment**: Partial (task_*, external_*, consolidate_* are different prefixes)
- **Rationale**: All chunks enable work spanning multiple repositories via external
  references, task directories, and sync operations

### Cluster: Workflow Artifact Lifecycle
- **Chunks**: chunk_* (8), narrative_* (3), investigation_* (3), subsystem_* (6),
  valid_transitions, ordering_* (5), artifact_* (5), populate_created_after,
  proposed_chunks_frontmatter, symbolic_code_refs, bidirectional_refs
- **Shared files**: src/chunks.py, src/narratives.py, src/investigations.py,
  src/subsystems.py, src/models.py, src/artifact_ordering.py
- **Prefix alignment**: Mixed (multiple prefixes map to same capability)
- **Rationale**: All chunks implement the documentation-driven workflow pattern
  with status lifecycles, frontmatter schemas, and causal ordering

### Cluster: Template Rendering
- **Chunks**: template_* (3), migrate_chunks_template, jinja_backrefs,
  code_to_docs_backrefs, project_init_command, init_creates_chunks_dir
- **Shared files**: src/template_system.py, src/project.py, src/templates/*
- **Prefix alignment**: Partial (template_* is main, others scattered)
- **Rationale**: All chunks support Jinja2-based template rendering for
  artifact creation and project initialization

### Cluster: Chunk Naming & Clustering
- **Chunks**: cluster_* (6)
- **Shared files**: src/cluster_analysis.py, src/cluster_rename.py
- **Prefix alignment**: Perfect (cluster_*)
- **Rationale**: Tools for analyzing, suggesting, and renaming chunk prefixes

### Cluster: Friction Tracking
- **Chunks**: friction_* (5)
- **Shared files**: src/friction.py, friction templates
- **Prefix alignment**: Perfect (friction_*)
- **Rationale**: Friction log capture and management

### Cluster: Git & Sync Operations
- **Chunks**: git_local_utilities, ve_sync_command, sync_all_workflows
- **Shared files**: src/git_utils.py, src/sync.py
- **Prefix alignment**: Poor (no common prefix)
- **Rationale**: Git operations and repository synchronization

### Cluster: Documentation Updates
- **Chunks**: background_keyword_semantic, learning_philosophy_docs, spec_docs_update,
  restore_template_content, ordering_audit_seqnums
- **Shared files**: CLAUDE.md templates, docs/trunk/
- **Prefix alignment**: None (various prefixes)
- **Rationale**: CLAUDE.md and documentation improvements

## Orphans & Anomalies

### Documentation-Only Chunks (no code references)
- None identified - all chunks have code_paths or code_references

### Stale References
- Need to verify: Some chunks reference older path patterns

### Undocumented Code Areas
Based on high-touch files, these may have undocumented patterns:
- src/ve.py - CLI routing (touched by 54 chunks, but routing patterns undocumented)
- src/models.py - schema definitions (27 chunks, but schema evolution patterns undocumented)

### HISTORICAL Chunks with Context Value
- **coderef_format_prompting**: Superseded by symbolic_code_refs. Contains historical
  context about the evolution from line-number references to symbolic references.

## Existing Subsystem Reconciliation

### template_system (STABLE)
- **Status**: STABLE (well-documented, no active deviations)
- **Chunks already attributed**: 9 chunks via `relationship: implements`
- **Chunk agreement**: AGREEMENT - existing subsystem aligns with template_* capability cluster
- **Scope**: Template rendering, includes, base context, file writing with suffix stripping

### workflow_artifacts (STABLE)
- **Status**: STABLE (comprehensive documentation)
- **Chunks already attributed**: 36 chunks via `relationship: implements`
- **Chunk agreement**: AGREEMENT - existing subsystem captures the unified artifact pattern
- **Scope**: Artifact lifecycle, frontmatter schemas, status transitions, external refs

### Gaps (capabilities without subsystems)
1. **orchestrator** - 21 orch_* chunks have no subsystem documentation
2. **cross_repo_operations** - 15+ chunks for task/external operations have no subsystem
3. **cluster_analysis** - 6 cluster_* chunks have no subsystem
4. **friction_tracking** - 5 friction_* chunks have no subsystem
5. **git_sync** - 3 chunks for git/sync operations have no subsystem

## Narrative Relationships

### cross_repo_chunks Narrative
- **Chunks attributed**: chunk_create_task_aware, cross_repo_schemas (2 chunks)
- **Related capability cluster**: Cross-Repository Operations (~15+ chunks)
- **Gap**: Most cross-repo chunks not linked to this narrative

### investigations Narrative
- **Chunks attributed**: document_investigations (1 chunk)
- **Related capability cluster**: Workflow Artifact Lifecycle (investigation_* subset)
- **Gap**: investigation_commands, investigation_template not linked

### subsystem_documentation Narrative
- **Chunks attributed**: agent_discovery_command, bidirectional_refs (2 chunks)
- **Related capability cluster**: Workflow Artifact Lifecycle (subsystem_* subset)
- **Gap**: subsystem_cli_scaffolding, subsystem_schemas_and_model not linked

## Recommendations for Phase 2

### Strong Subsystem Candidates (high alignment)
1. **orchestrator** - 21 chunks, perfect file alignment, clear business capability
2. **cluster_analysis** - 6 chunks, perfect file alignment
3. **friction_tracking** - 5 chunks, perfect file alignment

### Needs Boundary Refinement
1. **cross_repo_operations** - Multiple prefixes (task_*, external_*, consolidate_*),
   need to determine if this is one subsystem or splits into task_context + external_refs
2. **workflow_artifacts** - Already exists but may need to absorb ordering_* chunks
3. **git_sync** - Small cluster (3 chunks), may fold into infrastructure

### Questions for Operator
1. Should ordering_* chunks be absorbed into existing workflow_artifacts subsystem?
2. Should cross-repo operations be one subsystem or split (task_context vs external_refs)?
3. Are cluster_* chunks a separate subsystem or part of workflow_artifacts?
4. Should documentation-update chunks (CLAUDE.md improvements) map to template_system?
