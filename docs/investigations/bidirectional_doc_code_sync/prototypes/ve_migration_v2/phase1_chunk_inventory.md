# Phase 1: Chunk Inventory & Clustering

## Chunk Inventory

| Chunk | Status | Files Referenced | Summary |
|-------|--------|------------------|---------|
| accept_full_artifact_paths | ACTIVE | 15 refs | Flexible artifact path normalization accepting any reasonable format |
| agent_discovery_command | ACTIVE | 0 refs | Agent discovery CLI command |
| artifact_copy_backref | ACTIVE | 3 refs | Back-reference update for copy-external operations |
| artifact_index_no_git | ACTIVE | 0 refs | Directory-based staleness detection (no git required) |
| artifact_list_ordering | ACTIVE | 0 refs | Use ArtifactIndex for causal ordering in list commands |
| artifact_ordering_index | ACTIVE | 0 refs | ArtifactIndex class for cached topological sorting |
| artifact_promote | ACTIVE | 10 refs | Promote artifact from project to external repo |
| background_keyword_semantic | ACTIVE | 0 refs | "In the background" keyword triggers FUTURE chunk workflow |
| bidirectional_refs | ACTIVE | 0 refs | Subsystem validation and bidirectional refs |
| bug_type_field | ACTIVE | 6 refs | Bug type field in frontmatter |
| causal_ordering_migration | ACTIVE | 0 refs | One-time migration to populate created_after fields |
| chunk_create_guard | ACTIVE | 2 refs | Prevent multiple IMPLEMENTING chunks |
| chunk_create_task_aware | ACTIVE | 0 refs | Task-aware chunk creation |
| chunk_frontmatter_model | ACTIVE | 0 refs | ChunkStatus StrEnum and ChunkFrontmatter Pydantic model |
| chunk_list_command-ve-002 | ACTIVE | 0 refs | List chunks command |
| chunk_list_repo_source | ACTIVE | 3 refs | Include repo ref in --latest output |
| chunk_overlap_command | ACTIVE | 0 refs | Chunk overlap detection command |
| chunk_template_expansion | ACTIVE | 0 refs | Template context for chunk creation |
| chunk_validate | ACTIVE | 0 refs | Chunk validation framework |
| cluster_list_command | ACTIVE | 8 refs | Cluster analysis list command |
| cluster_naming_guidance | ACTIVE | 0 refs | Documentation for cluster naming conventions |
| cluster_prefix_suggest | ACTIVE | 7 refs | TF-IDF prefix suggestion feature |
| cluster_rename | ACTIVE | 16 refs | Cluster rename command |
| cluster_seed_naming | ACTIVE | 1 ref | Seed naming for clusters |
| cluster_subsystem_prompt | ACTIVE | 9 refs | Cluster size warnings and subsystem prompting |
| code_to_docs_backrefs | ACTIVE | 0 refs | Code to docs backref documentation |
| coderef_format_prompting | HISTORICAL | 5 refs | Code reference format prompting (superseded) |
| consolidate_ext_ref_utils | ACTIVE | 11 refs | External reference utilities consolidation |
| consolidate_ext_refs | ACTIVE | 9 refs | ExternalArtifactRef model consolidation |
| copy_as_external | ACTIVE | 4 refs | Copy artifact as external reference |
| cross_repo_schemas | ACTIVE | 0 refs | Cross-repo task configuration schemas |
| deferred_worktree_creation | ACTIVE | 4 refs | Deferred worktree creation |
| document_investigations | ACTIVE | 0 refs | Investigation documentation |
| external_chunk_causal | ACTIVE | 10 refs | External chunk causal ordering |
| external_resolve | ACTIVE | 0 refs | External resolve command |
| external_resolve_all_types | ACTIVE | 11 refs | Extended external resolve to all artifact types |
| fix_ticket_frontmatter_null | ACTIVE | 0 refs | Fix null ticket frontmatter |
| friction_chunk_linking | ACTIVE | 10 refs | Friction entry to chunk linking |
| friction_chunk_workflow | ACTIVE | 6 refs | Friction chunk workflow |
| friction_claude_docs | ACTIVE | 1 ref | Friction log documentation in CLAUDE.md |
| friction_noninteractive | ACTIVE | 0 refs | Non-interactive friction logging |
| friction_template_and_cli | ACTIVE | 14 refs | Friction log template and CLI commands |
| future_chunk_creation | ACTIVE | 0 refs | FUTURE chunk status and activate command |
| git_local_utilities | ACTIVE | 0 refs | Git local utility functions |
| implement_chunk_start-ve-001 | ACTIVE | 9 refs | Original chunk management implementation |
| init_creates_chunks_dir | ACTIVE | 6 refs | Project init creates chunks directory |
| investigation_chunk_refs | ACTIVE | 7 refs | Investigation field for chunk traceability |
| investigation_commands | ACTIVE | 0 refs | Investigation CLI commands |
| investigation_template | ACTIVE | 0 refs | Investigation template |
| jinja_backrefs | ACTIVE | 6 refs | Jinja template backreferences |
| learning_philosophy_docs | ACTIVE | 1 ref | Learning philosophy documentation |
| list_task_aware | ACTIVE | 0 refs | Task-aware chunk listing |
| migrate_chunks_template | ACTIVE | 0 refs | Migrate chunks to template system |
| narrative_backreference_support | ACTIVE | 4 refs | Narrative backreference validation |
| narrative_cli_commands | ACTIVE | 0 refs | Narrative CLI commands |
| narrative_consolidation | ACTIVE | 13 refs | Chunk consolidation into narratives |
| orch_activate_on_inject | ACTIVE | 12 refs | Activate on inject for orchestrator |
| orch_agent_question_tool | ACTIVE | 5 refs | Agent question tool for orchestrator |
| orch_agent_skills | ACTIVE | 5 refs | Agent skills for orchestrator |
| orch_attention_queue | ACTIVE | 15 refs | Attention queue CLI commands |
| orch_attention_reason | ACTIVE | 14 refs | Attention reason tracking |
| orch_blocked_lifecycle | ACTIVE | 8 refs | Blocked lifecycle management |
| orch_broadcast_invariant | ACTIVE | 4 refs | Broadcast invariant for orchestrator |
| orch_conflict_oracle | ACTIVE | 28 refs | Conflict detection and resolution |
| orch_conflict_template_fix | ACTIVE | 4 refs | Conflict template fix |
| orch_dashboard | ACTIVE | 18 refs | Real-time dashboard with WebSocket |
| orch_foundation | ACTIVE | 24 refs | Orchestrator daemon foundation |
| orch_inject_path_compat | ACTIVE | 2 refs | Inject path compatibility |
| orch_inject_validate | ACTIVE | 5 refs | Injection-time validation |
| orch_mechanical_commit | ACTIVE | 4 refs | Mechanical commit operations |
| orch_question_forward | ACTIVE | 8 refs | Question forwarding |
| orch_sandbox_enforcement | ACTIVE | 11 refs | Sandbox enforcement |
| orch_scheduling | ACTIVE | 30 refs | Work unit scheduling |
| orch_submit_future_cmd | ACTIVE | 1 ref | Submit future command |
| orch_tcp_port | ACTIVE | 6 refs | TCP port configuration |
| orch_unblock_transition | FUTURE | 3 refs | Unblock transition (not yet implemented) |
| orch_verify_active | ACTIVE | 10 refs | Verify active chunk status |
| ordering_active_only | ACTIVE | 0 refs | Status-aware tip filtering |
| ordering_audit_seqnums | ACTIVE | 4 refs | Audit sequence numbers |
| ordering_field | ACTIVE | 0 refs | created_after field for ordering |
| ordering_field_clarity | ACTIVE | 1 ref | Ordering field documentation clarity |
| ordering_remove_seqno | ACTIVE | 20 refs | Remove sequence number prefixes |
| populate_created_after | ACTIVE | 0 refs | Auto-populate created_after from tips |
| project_init_command | ACTIVE | 0 refs | Project initialization command |
| proposed_chunks_frontmatter | ACTIVE | 0 refs | Proposed chunks frontmatter field |
| remove_external_ref | ACTIVE | 0 refs | Remove external reference command |
| remove_trivial_tests | ACTIVE | 0 refs | Remove trivial tests |
| rename_chunk_start_to_create | ACTIVE | 0 refs | Rename start to create CLI command |
| respect_future_intent | ACTIVE | 1 ref | Respect FUTURE chunk intent |
| restore_template_content | ACTIVE | 5 refs | Restore template content |
| selective_artifact_friction | ACTIVE | 0 refs | Selective artifact friction linking |
| selective_project_linking | ACTIVE | 20 refs | --projects flag for selective linking |
| spec_docs_update | ACTIVE | 0 refs | Specification documentation update |
| subsystem_cli_scaffolding | ACTIVE | 0 refs | Subsystem CLI scaffolding |
| subsystem_docs_update | ACTIVE | 0 refs | Subsystem documentation update |
| subsystem_impact_resolution | ACTIVE | 0 refs | Subsystem impact/overlap detection |
| subsystem_schemas_and_model | ACTIVE | 0 refs | Subsystem schemas and Pydantic models |
| subsystem_status_transitions | ACTIVE | 3 refs | Subsystem status transitions |
| subsystem_template | ACTIVE | 0 refs | Subsystem template |
| symbolic_code_refs | ACTIVE | 1 ref | Symbolic code reference format |
| sync_all_workflows | ACTIVE | 8 refs | Extend sync to all workflow types |
| task_aware_investigations | ACTIVE | 11 refs | Task-aware investigation commands |
| task_aware_narrative_cmds | ACTIVE | 12 refs | Task-aware narrative commands |
| task_aware_subsystem_cmds | ACTIVE | 11 refs | Task-aware subsystem commands |
| task_chunk_validation | ACTIVE | 6 refs | Task-aware chunk validation |
| task_config_local_paths | ACTIVE | 4 refs | Task config local path resolution |
| task_init | ACTIVE | 0 refs | Task directory initialization |
| task_init_scaffolding | ACTIVE | 18 refs | Task CLAUDE.md and commands scaffolding |
| task_list_proposed | ACTIVE | 7 refs | Task-aware proposed chunk listing |
| task_qualified_refs | ACTIVE | 12 refs | Project-qualified code references |
| task_status_command | ACTIVE | 0 refs | Task status command |
| taskdir_context_cmds | ACTIVE | 0 refs | Task context operational commands |
| template_drift_prevention | ACTIVE | 9 refs | Prevent template drift |
| template_system_consolidation | ACTIVE | 0 refs | Template system consolidation |
| template_unified_module | ACTIVE | 0 refs | Unified template_system.py module |
| update_crossref_format | ACTIVE | 0 refs | Update cross-reference format |
| valid_transitions | ACTIVE | 0 refs | State transition validation dicts |
| ve_sync_command | ACTIVE | 0 refs | Sync external references command |

**Total**: 118 chunks (117 ACTIVE, 1 HISTORICAL, 1 FUTURE)

---

## File Overlap Analysis

### High-Touch Files (10+ chunk references)

| File | Chunk Ref Count | Key Chunks Referencing |
|------|----------------|------------------------|
| src/ve.py | 145 | implement_chunk_start, chunk_list_command, project_init_command, future_chunk_creation, selective_project_linking, orch_* (many) |
| src/task_utils.py | 88 | chunk_create_task_aware, consolidate_ext_refs, task_aware_*, selective_project_linking, artifact_promote |
| src/models.py | 62 | chunk_frontmatter_model, valid_transitions, consolidate_ext_refs, orch_* |
| src/chunks.py | 77 | implement_chunk_start, chunk_overlap_command, symbolic_code_refs, narrative_consolidation, cluster_prefix_suggest |
| src/subsystems.py | 28 | subsystem_schemas_and_model, subsystem_cli_scaffolding, bidirectional_refs, ordering_remove_seqno |
| src/template_system.py | 19 | template_unified_module, template_system_consolidation, template_drift_prevention |
| src/orchestrator/*.py | ~60 total | orch_foundation, orch_scheduling, orch_conflict_oracle, orch_attention_* |

### Most-Referenced Chunks (by backreference count in code)

| Chunk | Backreference Count | Primary Files |
|-------|---------------------|---------------|
| ordering_remove_seqno | 22 | chunks.py, subsystems.py, investigations.py, narratives.py, external_refs.py |
| orch_conflict_oracle | 19 | orchestrator/state.py, orchestrator/scheduler.py, orchestrator/api.py |
| selective_project_linking | 17 | ve.py, task_utils.py |
| chunk_create_task_aware | 17 | task_utils.py, ve.py, external_refs.py |
| valid_transitions | 16 | chunks.py, narratives.py, investigations.py, ve.py |
| symbolic_code_refs | 16 | chunks.py, symbols.py |
| orch_foundation | 16 | ve.py, orchestrator/*.py |
| accept_full_artifact_paths | 16 | ve.py, external_refs.py, task_utils.py |

---

## Prefix Clusters

| Prefix | Chunk Count | Primary Files |
|--------|-------------|---------------|
| orch_* | 21 | src/orchestrator/*.py, src/ve.py |
| task_* | 11 | src/task_utils.py, src/task_init.py, src/ve.py |
| chunk_* | 9 | src/chunks.py, src/ve.py |
| ordering_* | 5 | src/artifact_ordering.py, src/chunks.py |
| subsystem_* | 6 | src/subsystems.py, src/ve.py |
| friction_* | 5 | src/friction.py, src/ve.py |
| cluster_* | 5 | src/cluster_analysis.py, src/ve.py |
| template_* | 4 | src/template_system.py, src/project.py |
| narrative_* | 3 | src/narratives.py, src/chunks.py |
| external_* | 4 | src/external_refs.py, src/external_resolve.py |
| artifact_* | 4 | src/artifact_ordering.py, src/task_utils.py |
| investigation_* | 3 | src/investigations.py, src/ve.py |
| consolidate_* | 2 | src/external_refs.py, src/task_utils.py |
| valid_* | 1 | src/models.py, multiple manager classes |
| sync_* | 1 | src/sync.py |

---

## Prefix vs File Cluster Alignment

| Prefix Cluster | Aligns With File Cluster? | Notes |
|----------------|---------------------------|-------|
| orch_* | **YES** | All 21 chunks share orchestrator files (src/orchestrator/*.py) |
| task_* | **YES** | All share task_utils.py, task_init.py |
| chunk_* | **PARTIAL** | Some share chunks.py, but chunk_create_task_aware heavily in task_utils.py |
| ordering_* | **YES** | All share artifact_ordering.py |
| subsystem_* | **YES** | All share subsystems.py |
| friction_* | **YES** | All share friction.py |
| cluster_* | **YES** | All share cluster_analysis.py |
| template_* | **YES** | All share template_system.py |
| narrative_* | **PARTIAL** | narrative_consolidation heavily in chunks.py, not just narratives.py |
| external_* | **YES** | All share external_refs.py, external_resolve.py |
| consolidate_* | **PARTIAL** | Named for the ACTION, not the DOMAIN. Actually belong to external_* capability |

---

## Capability Clusters

### Cluster: Orchestrator (Parallel Execution)
- **Chunks**: orch_foundation, orch_scheduling, orch_conflict_oracle, orch_dashboard, orch_attention_queue, orch_attention_reason, orch_blocked_lifecycle, orch_activate_on_inject, orch_sandbox_enforcement, orch_verify_active, orch_inject_validate, orch_inject_path_compat, orch_mechanical_commit, orch_agent_question_tool, orch_agent_skills, orch_question_forward, orch_submit_future_cmd, orch_tcp_port, orch_broadcast_invariant, orch_conflict_template_fix, orch_unblock_transition (FUTURE)
- **Shared files**: src/orchestrator/*.py (state.py, scheduler.py, daemon.py, api.py, agent.py, models.py, websocket.py), src/ve.py
- **Prefix alignment**: Perfect - all orch_* chunks
- **Rationale**: Self-contained parallel execution system managing work units, scheduling, conflicts, and agent communication

### Cluster: Workflow Artifacts (Chunk/Narrative/Investigation/Subsystem Lifecycle)
- **Chunks**: implement_chunk_start, chunk_list_command, chunk_overlap_command, chunk_validate, chunk_frontmatter_model, chunk_template_expansion, chunk_create_guard, future_chunk_creation, narrative_cli_commands, narrative_consolidation, narrative_backreference_support, investigation_commands, investigation_template, investigation_chunk_refs, subsystem_cli_scaffolding, subsystem_schemas_and_model, subsystem_template, subsystem_status_transitions, subsystem_impact_resolution, proposed_chunks_frontmatter, valid_transitions, bidirectional_refs, symbolic_code_refs
- **Shared files**: src/chunks.py, src/narratives.py, src/investigations.py, src/subsystems.py, src/models.py
- **Prefix alignment**: Mixed - chunk_*, narrative_*, investigation_*, subsystem_* all belong here
- **Rationale**: Core workflow artifact management - all share the same structural pattern (status, frontmatter, lifecycle)

### Cluster: Artifact Ordering (Causal DAG)
- **Chunks**: ordering_field, ordering_field_clarity, ordering_remove_seqno, ordering_active_only, ordering_audit_seqnums, artifact_ordering_index, artifact_index_no_git, artifact_list_ordering, populate_created_after, causal_ordering_migration
- **Shared files**: src/artifact_ordering.py, touched by all manager classes
- **Prefix alignment**: ordering_* + artifact_* (overlap)
- **Rationale**: Causal ordering infrastructure - created_after field and topological sorting

### Cluster: Cross-Repo Operations (Task Directory Mode)
- **Chunks**: task_init, task_init_scaffolding, task_config_local_paths, task_status_command, task_list_proposed, task_qualified_refs, task_chunk_validation, chunk_create_task_aware, list_task_aware, task_aware_narrative_cmds, task_aware_investigations, task_aware_subsystem_cmds, selective_project_linking, taskdir_context_cmds
- **Shared files**: src/task_utils.py, src/task_init.py
- **Prefix alignment**: Mostly task_*, but chunk_create_task_aware named by artifact not domain
- **Rationale**: Multi-repository workflow support

### Cluster: External References
- **Chunks**: external_resolve, external_resolve_all_types, external_chunk_causal, consolidate_ext_refs, consolidate_ext_ref_utils, copy_as_external, artifact_copy_backref, remove_external_ref, sync_all_workflows, ve_sync_command
- **Shared files**: src/external_refs.py, src/external_resolve.py, src/sync.py
- **Prefix alignment**: external_*, consolidate_*, sync_*
- **Rationale**: External artifact reference handling across repositories

### Cluster: Template System
- **Chunks**: template_unified_module, template_system_consolidation, template_drift_prevention, migrate_chunks_template, jinja_backrefs, restore_template_content
- **Shared files**: src/template_system.py, src/project.py, src/templates/*
- **Prefix alignment**: template_*
- **Rationale**: Unified Jinja2 template rendering for artifact creation

### Cluster: Cluster Analysis (Chunk Naming)
- **Chunks**: cluster_list_command, cluster_rename, cluster_prefix_suggest, cluster_seed_naming, cluster_naming_guidance, cluster_subsystem_prompt
- **Shared files**: src/cluster_analysis.py, src/cluster_rename.py
- **Prefix alignment**: cluster_*
- **Rationale**: Chunk naming conventions and cluster management

### Cluster: Friction Log
- **Chunks**: friction_template_and_cli, friction_chunk_workflow, friction_chunk_linking, friction_claude_docs, friction_noninteractive, selective_artifact_friction
- **Shared files**: src/friction.py
- **Prefix alignment**: friction_* (mostly)
- **Rationale**: Friction log artifact management

### Cluster: Project Initialization
- **Chunks**: project_init_command, init_creates_chunks_dir, accept_full_artifact_paths
- **Shared files**: src/project.py
- **Prefix alignment**: Mixed (project_*, init_*, accept_*)
- **Rationale**: Project setup and configuration

### Cluster: Code Reference Management
- **Chunks**: symbolic_code_refs, code_to_docs_backrefs, coderef_format_prompting (HISTORICAL)
- **Shared files**: src/symbols.py, src/chunks.py
- **Prefix alignment**: Mixed
- **Rationale**: Code-to-documentation reference handling

---

## Orphans & Anomalies

### Documentation-Only Chunks (no code_references in frontmatter)
- agent_discovery_command
- background_keyword_semantic
- code_to_docs_backrefs
- cluster_naming_guidance
- document_investigations
- learning_philosophy_docs
- spec_docs_update
- subsystem_docs_update

### Stale References
- None detected (all code_references appear to point to existing symbols)

### Undocumented Code Areas
| File | Backreference Count | Notes |
|------|---------------------|-------|
| src/cluster_rename.py | 0 | Has cluster_rename chunk, but no backreferences in code |
| src/repo_cache.py | 1 | Only external_resolve chunk reference |

### HISTORICAL Chunks with Context Value
- **coderef_format_prompting** (HISTORICAL) - Still has 5 active backreferences. May need cleanup or the backreferences updated.

### FUTURE Chunks (Excluded from Synthesis)
- **orch_unblock_transition** (FUTURE) - Not yet implemented, 3 code_references declared

---

## File Clusters by Shared Chunks

Based on >50% shared chunk references:

| File Group | Shared Chunks | Capability |
|------------|---------------|------------|
| src/orchestrator/*.py | orch_* (21 chunks) | Orchestrator |
| src/chunks.py + src/narratives.py + src/investigations.py + src/subsystems.py | implement_chunk_start, valid_transitions, ordering_remove_seqno, populate_created_after | Workflow Artifacts |
| src/task_utils.py + src/task_init.py | task_*, chunk_create_task_aware, selective_project_linking | Cross-Repo Operations |
| src/external_refs.py + src/external_resolve.py + src/sync.py | external_*, consolidate_* | External References |
| src/template_system.py + src/project.py | template_* | Template System |
