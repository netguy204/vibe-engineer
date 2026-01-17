# Phase 1: Chunk Inventory & Clustering

## Executive Summary

- **Total chunks analyzed**: 118
- **Status distribution**: 116 ACTIVE, 1 FUTURE, 1 HISTORICAL
- **Total unique files referenced**: 164
- **Files with 2+ chunk references**: 97
- **Concept clusters identified**: 12 major clusters

---

## Chunk Inventory

| Chunk | Status | Files Referenced | Summary |
|-------|--------|------------------|---------|
| accept_full_artifact_paths | ACTIVE | 6 | Introduce shared parsing infrastructure at the CLI level for flexible path and identifier formats |
| agent_discovery_command | ACTIVE | 1 | Create /subsystem-discover agent command that guides collaborative discovery of emergent subsystems |
| artifact_copy_backref | ACTIVE | 2 | Add backreference when using ve artifact copy-external to copy an artifact |
| artifact_index_no_git | ACTIVE | 2 | Simplify ArtifactIndex staleness detection using directory enumeration |
| artifact_list_ordering | ACTIVE | 9 | Update list commands to use ArtifactIndex for causal ordering |
| artifact_ordering_index | ACTIVE | 3 | Implement ArtifactIndex - cached ordering system using git-hash staleness detection |
| artifact_promote | ACTIVE | 3 | Add ve artifact promote command to move local artifacts to tasks |
| background_keyword_semantic | ACTIVE | 2 | Document "background" keyword semantic for agent-orchestrator interaction |
| bidirectional_refs | ACTIVE | 13 | Enable bidirectional navigation between chunks and subsystems |
| bug_type_field | ACTIVE | 5 | Add bug_type field to chunk schema for agent behavior guidance |
| causal_ordering_migration | ACTIVE | 2 | Run one-time migration to populate created_after fields |
| chunk_create_guard | ACTIVE | 2 | Fail ve chunk start if IMPLEMENTING chunk exists |
| chunk_create_task_aware | ACTIVE | 7 | Extend ve chunk create for cross-repository work in task directories |
| chunk_frontmatter_model | ACTIVE | 10 | Add ChunkStatus StrEnum and ChunkFrontmatter Pydantic model |
| chunk_list_command-ve-002 | ACTIVE | 5 | Implement ve chunk list command to enumerate existing chunks |
| chunk_list_repo_source | ACTIVE | 3 | Show repository source in ve chunk list --latest in task context |
| chunk_overlap_command | ACTIVE | 3 | Implement ve chunk overlap to identify affected ACTIVE chunks |
| chunk_template_expansion | ACTIVE | 3 | Expand chunk templates with full chunk directory name for cross-references |
| chunk_validate | ACTIVE | 4 | Implement ve chunk complete [chunk_id] to validate chunk metadata |
| cluster_list_command | ACTIVE | 3 | Implement ve cluster list to show prefix clusters |
| cluster_naming_guidance | ACTIVE | 1 | Add naming convention section to CLAUDE.md for chunks |
| cluster_prefix_suggest | ACTIVE | 5 | Implement similarity-based prefix suggestion during chunk planning |
| cluster_rename | ACTIVE | 5 | Implement ve cluster rename command for batch renaming |
| cluster_seed_naming | ACTIVE | 1 | Add naming prompt to /chunk-create skill for cluster seeding |
| cluster_subsystem_prompt | ACTIVE | 6 | Prompt for subsystem when cluster expands beyond threshold |
| code_to_docs_backrefs | ACTIVE | 5 | Add bidirectional references from source code to chunks and subsystems |
| coderef_format_prompting | HISTORICAL | 6 | Fix mismatch between chunk template code reference examples (superseded) |
| consolidate_ext_ref_utils | ACTIVE | 7 | Create src/external_refs.py module for external artifact utilities |
| consolidate_ext_refs | ACTIVE | 7 | Replace ExternalChunkRef with generic ExternalArtifactRef model |
| copy_as_external | ACTIVE | 3 | Add ve artifact copy-external command for external references |
| cross_repo_schemas | ACTIVE | 3 | Introduce Pydantic models for cross-repository chunk management |
| deferred_worktree_creation | ACTIVE | 4 | Defer git worktree creation until execution begins |
| document_investigations | ACTIVE | 3 | Document investigations as first-class workflow artifact |
| external_chunk_causal | ACTIVE | 6 | Extend causal ordering to include external chunk references |
| external_resolve | ACTIVE | 8 | Implement ve external resolve command with local repo cache |
| external_resolve_all_types | ACTIVE | 4 | Extend ve external resolve to all workflow artifact types |
| fix_ticket_frontmatter_null | ACTIVE | 2 | Fix chunk template to output valid YAML null |
| friction_chunk_linking | ACTIVE | 4 | Add friction_entries to chunk GOAL.md template |
| friction_chunk_workflow | ACTIVE | 3 | Integrate friction tracking into chunk create/complete workflows |
| friction_claude_docs | ACTIVE | 1 | Document friction log artifact type in CLAUDE.md |
| friction_noninteractive | ACTIVE | 3 | Make ve friction log CLI command fully non-interactive |
| friction_template_and_cli | ACTIVE | 8 | Implement friction log artifact type with template and CLI |
| future_chunk_creation | ACTIVE | 11 | Add ability to create FUTURE chunks while in progress |
| git_local_utilities | ACTIVE | 2 | Create utility functions for local git repositories and worktrees |
| implement_chunk_start-ve-001 | ACTIVE | 4 | Implement ve chunk start short_name [ticket_id] command |
| init_creates_chunks_dir | ACTIVE | 3 | Make ve init create docs/chunks/ directory |
| investigation_chunk_refs | ACTIVE | 6 | Add investigation reference to chunk frontmatter |
| investigation_commands | ACTIVE | 6 | Add CLI commands and slash command for investigations |
| investigation_template | ACTIVE | 2 | Create investigation OVERVIEW.md template |
| jinja_backrefs | ACTIVE | 3 | Add Jinja backreference comments to source templates |
| learning_philosophy_docs | ACTIVE | 1 | Add Learning Philosophy section to CLAUDE.md template |
| list_task_aware | ACTIVE | 3 | Extend ve chunk list for task directory context |
| migrate_chunks_template | ACTIVE | 4 | Migrate src/chunks.py to use template_system module |
| narrative_backreference_support | ACTIVE | 3 | Add narrative backreference support to source code files |
| narrative_cli_commands | ACTIVE | 3 | Add narrative command group with create subcommand |
| narrative_consolidation | ACTIVE | 4 | Implement chunk-to-narrative consolidation workflow |
| orch_activate_on_inject | ACTIVE | 5 | Transition chunk from FUTURE to IMPLEMENTING on inject |
| orch_agent_question_tool | ACTIVE | 3 | Replace text-parsing heuristics with tool-based mechanism for agent questions |
| orch_agent_skills | ACTIVE | 3 | Configure background agents with same skills as interactive users |
| orch_attention_queue | ACTIVE | 10 | Build attention queue system for operator input prioritization |
| orch_attention_reason | ACTIVE | 7 | Store and display reason for work unit needing attention |
| orch_blocked_lifecycle | ACTIVE | 6 | Fix conflict resolution system deficiencies |
| orch_broadcast_invariant | ACTIVE | 2 | Fix missing WebSocket broadcasts in scheduler |
| orch_conflict_oracle | ACTIVE | 11 | Implement Conflict Oracle for chunk parallelization analysis |
| orch_conflict_template_fix | ACTIVE | 2 | Fix false positive conflicts in oracle |
| orch_dashboard | ACTIVE | 4 | Add web dashboard for orchestrator visualization |
| orch_foundation | ACTIVE | 11 | Establish orchestrator foundation with daemon and SQLite state |
| orch_inject_path_compat | ACTIVE | 2 | Accept full chunk paths in inject command |
| orch_inject_validate | ACTIVE | 5 | Validate chunks before accepting into orchestrator |
| orch_mechanical_commit | ACTIVE | 4 | Replace agent-driven commit with mechanical commit |
| orch_question_forward | ACTIVE | 5 | Forward agent AskUserQuestion to attention queue |
| orch_sandbox_enforcement | ACTIVE | 2 | Prevent agents from escaping worktree sandbox |
| orch_scheduling | ACTIVE | 14 | Implement scheduling layer with worktree management and agent spawning |
| orch_submit_future_cmd | ACTIVE | 2 | Create /orchestrator-submit-future slash command |
| orch_tcp_port | ACTIVE | 3 | Add TCP port support for web dashboard access |
| orch_unblock_transition | FUTURE | 0 | Fix stuck work units in NEEDS_ATTENTION |
| orch_verify_active | ACTIVE | 5 | Validate chunk ACTIVE status before completion commit |
| ordering_active_only | ACTIVE | 2 | Update find_tips to only consider artifacts with appropriate status |
| ordering_audit_seqnums | ACTIVE | 4 | Remove deprecated sequential numbering from slash commands |
| ordering_field | ACTIVE | 2 | Add created_after field to workflow artifact frontmatter |
| ordering_field_clarity | ACTIVE | 1 | Clarify created_after field semantics |
| ordering_remove_seqno | ACTIVE | 16 | Remove sequence prefix from workflow artifact directory naming |
| populate_created_after | ACTIVE | 12 | Populate created_after field automatically on artifact creation |
| project_init_command | ACTIVE | 5 | Implement ve init command for project bootstrapping |
| proposed_chunks_frontmatter | ACTIVE | 13 | Standardize proposed_chunks tracking across artifact types |
| remove_external_ref | ACTIVE | 3 | Add ve artifact remove-external command |
| remove_trivial_tests | ACTIVE | 2 | Audit and remove trivial tests |
| rename_chunk_start_to_create | ACTIVE | 5 | Rename ve chunk start to ve chunk create |
| respect_future_intent | ACTIVE | 1 | Make /chunk-create respect operator intent for FUTURE status |
| restore_template_content | ACTIVE | 2 | Restore content lost from source templates |
| selective_artifact_friction | ACTIVE | 6 | Enable friction logging in task context |
| selective_project_linking | ACTIVE | 6 | Add --projects flag to task artifact creation commands |
| spec_docs_update | ACTIVE | 2 | Document subsystems in SPEC.md and CLAUDE.md |
| subsystem_cli_scaffolding | ACTIVE | 6 | Establish CLI scaffolding for subsystem documentation |
| subsystem_docs_update | ACTIVE | 1 | Update workflow_artifacts subsystem documentation |
| subsystem_impact_resolution | ACTIVE | 5 | Integrate subsystem code references into chunk completion |
| subsystem_schemas_and_model | ACTIVE | 3 | Define data model for subsystem documentation |
| subsystem_status_transitions | ACTIVE | 4 | Implement ve subsystem status command |
| subsystem_template | ACTIVE | 3 | Create subsystem OVERVIEW.md template |
| symbolic_code_refs | ACTIVE | 12 | Replace line-number-based code references with symbolic references |
| sync_all_workflows | ACTIVE | 4 | Extend ve sync for all workflow artifact directories |
| task_aware_investigations | ACTIVE | 5 | Extend investigation commands for task directory context |
| task_aware_narrative_cmds | ACTIVE | 9 | Extend narrative commands for task directory context |
| task_aware_subsystem_cmds | ACTIVE | 6 | Extend subsystem commands for task directory context |
| task_chunk_validation | ACTIVE | 3 | Enable chunk commands to resolve external chunks |
| task_config_local_paths | ACTIVE | 5 | Make ve task init resolve local names to GitHub format |
| task_init | ACTIVE | 6 | Implement ve task init command for task directories |
| task_init_scaffolding | ACTIVE | 14 | Enhance ve task init with Claude Code scaffolding files |
| task_list_proposed | ACTIVE | 3 | Make ve chunk list-proposed work in task context |
| task_qualified_refs | ACTIVE | 6 | Extend SymbolicReference for project-qualified paths |
| task_status_command | ACTIVE | 7 | Enhance artifact list commands with grouped-by-location output |
| taskdir_context_cmds | ACTIVE | 6 | Extend task-context awareness to overlap, validate, and other commands |
| template_drift_prevention | ACTIVE | 7 | Prevent template drift with obvious markers and workflow docs |
| template_system_consolidation | ACTIVE | 23 | Complete template_system consolidation |
| template_unified_module | ACTIVE | 2 | Create canonical src/template_system.py module |
| update_crossref_format | ACTIVE | 7 | Update cross-references from legacy NNNN-short_name format |
| valid_transitions | ACTIVE | 9 | Add explicit state transition validation for artifacts |
| ve_sync_command | ACTIVE | 7 | Implement ve sync command for external reference updates |

---

## File Overlap Analysis

Files referenced by 5 or more chunks (high-touch areas):

| File | # Chunks | Sample Chunks |
|------|----------|---------------|
| src/ve.py | 54 | accept_full_artifact_paths, artifact_list_ordering, artifact_promote, ... |
| src/models.py | 27 | artifact_ordering_index, bidirectional_refs, bug_type_field, ... |
| src/chunks.py | 26 | artifact_list_ordering, bidirectional_refs, chunk_create_guard, ... |
| src/task_utils.py | 24 | accept_full_artifact_paths, artifact_copy_backref, artifact_list_ordering, ... |
| src/templates/claude/CLAUDE.md.jinja2 | 14 | background_keyword_semantic, cluster_naming_guidance, code_to_docs_backrefs, ... |
| tests/test_chunks.py | 13 | artifact_list_ordering, bidirectional_refs, chunk_frontmatter_model, ... |
| src/orchestrator/scheduler.py | 11 | deferred_worktree_creation, orch_activate_on_inject, orch_attention_queue, ... |
| src/subsystems.py | 11 | bidirectional_refs, chunk_frontmatter_model, ordering_remove_seqno, ... |
| src/templates/chunk/GOAL.md.jinja2 | 11 | background_keyword_semantic, bidirectional_refs, bug_type_field, ... |
| tests/test_orchestrator_scheduler.py | 11 | deferred_worktree_creation, orch_activate_on_inject, orch_agent_question_tool, ... |
| src/orchestrator/api.py | 9 | deferred_worktree_creation, orch_activate_on_inject, orch_attention_queue, ... |
| tests/test_models.py | 9 | bidirectional_refs, bug_type_field, chunk_frontmatter_model, ... |
| src/orchestrator/models.py | 8 | orch_activate_on_inject, orch_attention_queue, orch_attention_reason, ... |
| src/orchestrator/state.py | 8 | orch_activate_on_inject, orch_attention_queue, orch_attention_reason, ... |
| src/templates/commands/chunk-create.md.jinja2 | 8 | bug_type_field, cluster_seed_naming, friction_chunk_workflow, ... |
| tests/test_chunk_validate.py | 8 | bidirectional_refs, chunk_frontmatter_model, chunk_validate, ... |
| src/artifact_ordering.py | 7 | artifact_index_no_git, artifact_ordering_index, consolidate_ext_ref_utils, ... |
| src/narratives.py | 7 | narrative_cli_commands, ordering_remove_seqno, populate_created_after, ... |
| src/orchestrator/agent.py | 7 | orch_agent_question_tool, orch_agent_skills, orch_attention_queue, ... |
| src/project.py | 7 | cluster_subsystem_prompt, init_creates_chunks_dir, narrative_cli_commands, ... |
| src/templates/commands/chunk-complete.md.jinja2 | 7 | bug_type_field, friction_chunk_workflow, ordering_audit_seqnums, ... |

---

## Concept Clusters

### Cluster: Orchestrator (Parallel Agent Management)
- **Chunks (21)**: orch_activate_on_inject, orch_agent_question_tool, orch_agent_skills, orch_attention_queue, orch_attention_reason, orch_blocked_lifecycle, orch_broadcast_invariant, orch_conflict_oracle, orch_conflict_template_fix, orch_dashboard, orch_foundation, orch_inject_path_compat, orch_inject_validate, orch_mechanical_commit, orch_question_forward, orch_sandbox_enforcement, orch_scheduling, orch_submit_future_cmd, orch_tcp_port, orch_unblock_transition, orch_verify_active
- **Shared files**: src/orchestrator/*, src/ve.py (orch commands)
- **Rationale**: All chunks related to the parallel agent orchestration system - daemon lifecycle, work unit scheduling, attention queue, conflict detection, worktree isolation

### Cluster: Task Directory (Cross-Repository Work)
- **Chunks (10)**: task_aware_investigations, task_aware_narrative_cmds, task_aware_subsystem_cmds, task_chunk_validation, task_config_local_paths, task_init, task_init_scaffolding, task_list_proposed, task_qualified_refs, task_status_command
- **Shared files**: src/task_utils.py, src/ve.py (task commands)
- **Rationale**: All chunks enabling cross-repository task management, including task initialization, artifact resolution across repos, and context-aware commands

### Cluster: Workflow Artifacts (Core Domain Model)
- **Chunks (27 via subsystem relationship)**: artifact_copy_backref, artifact_index_no_git, artifact_list_ordering, artifact_ordering_index, artifact_promote, causal_ordering_migration, chunk_frontmatter_model, consolidate_ext_ref_utils, consolidate_ext_refs, external_chunk_causal, external_resolve_all_types, ordering_active_only, ordering_audit_seqnums, ordering_field, ordering_remove_seqno, populate_created_after, rename_chunk_start_to_create, selective_artifact_friction, subsystem_docs_update, sync_all_workflows, task_aware_investigations, task_aware_narrative_cmds, task_aware_subsystem_cmds, task_status_command, taskdir_context_cmds, update_crossref_format, valid_transitions
- **Shared files**: src/models.py, src/chunks.py, src/narratives.py, src/subsystems.py, src/investigations.py
- **Rationale**: Core workflow artifact models, validation, and lifecycle management across all artifact types (chunks, narratives, investigations, subsystems)

### Cluster: Template System
- **Chunks (8 via subsystem + 3 naming prefix)**: background_keyword_semantic, code_to_docs_backrefs, migrate_chunks_template, proposed_chunks_frontmatter, task_init_scaffolding, template_drift_prevention, template_system_consolidation, template_unified_module + jinja_backrefs, restore_template_content
- **Shared files**: src/template_system.py, src/templates/**/*.jinja2
- **Rationale**: Jinja2 template rendering infrastructure, template-to-output mapping, drift prevention

### Cluster: Chunk Lifecycle Management
- **Chunks (8)**: chunk_create_guard, chunk_create_task_aware, chunk_frontmatter_model, chunk_list_command-ve-002, chunk_list_repo_source, chunk_overlap_command, chunk_template_expansion, chunk_validate
- **Shared files**: src/chunks.py, src/ve.py, tests/test_chunks.py
- **Rationale**: Chunk-specific CLI commands and lifecycle validation

### Cluster: Cluster Naming & Organization
- **Chunks (6)**: cluster_list_command, cluster_naming_guidance, cluster_prefix_suggest, cluster_rename, cluster_seed_naming, cluster_subsystem_prompt
- **Shared files**: src/chunks.py, src/ve.py, CLAUDE.md template
- **Rationale**: Tools for organizing chunks by naming prefix clusters

### Cluster: Subsystem Documentation
- **Chunks (6 + 8 via narrative)**: subsystem_cli_scaffolding, subsystem_docs_update, subsystem_impact_resolution, subsystem_schemas_and_model, subsystem_status_transitions, subsystem_template + agent_discovery_command, bidirectional_refs, spec_docs_update
- **Shared files**: src/subsystems.py, docs/subsystems/
- **Rationale**: Subsystem artifact type discovery, documentation, and lifecycle

### Cluster: Friction Log
- **Chunks (5)**: friction_chunk_linking, friction_chunk_workflow, friction_claude_docs, friction_noninteractive, friction_template_and_cli
- **Shared files**: src/friction.py (implied), CLAUDE.md template
- **Rationale**: Friction log artifact type for capturing pain points

### Cluster: Causal Ordering
- **Chunks (5 naming prefix + overlap)**: ordering_active_only, ordering_audit_seqnums, ordering_field, ordering_field_clarity, ordering_remove_seqno + artifact_ordering_index, populate_created_after
- **Shared files**: src/artifact_ordering.py, src/models.py
- **Rationale**: created_after field and topological artifact ordering

### Cluster: Investigation Artifacts
- **Chunks (3 + 3 related)**: investigation_chunk_refs, investigation_commands, investigation_template + document_investigations
- **Shared files**: src/investigations.py, docs/investigations/
- **Rationale**: Investigation artifact type for exploratory work

### Cluster: External References
- **Chunks (5)**: external_chunk_causal, external_resolve, external_resolve_all_types, consolidate_ext_ref_utils, consolidate_ext_refs
- **Shared files**: src/external_refs.py, src/sync.py
- **Rationale**: Cross-repository artifact reference resolution

### Cluster: Narrative Artifacts
- **Chunks (3 + consolidation)**: narrative_backreference_support, narrative_cli_commands, narrative_consolidation
- **Shared files**: src/narratives.py
- **Rationale**: Narrative artifact type for multi-chunk initiatives

---

## Orphans & Anomalies

### Documentation-Only Chunks (no code_references)
- **orch_unblock_transition**: FUTURE status, no implementation yet

### Stale References (files no longer exist)
| Chunk | Stale Reference |
|-------|-----------------|
| agent_discovery_command | src/templates/commands/subsystem-discover.md (renamed to .jinja2) |
| bidirectional_refs | src/templates/commands/chunk-complete.md (renamed to .jinja2) |
| causal_ordering_migration | docs/chunks/0042-causal_ordering_migration/migrate.py (one-time migration script removed) |
| chunk_list_command-ve-002 | tests/test_ve.py (test file reorganized) |
| fix_ticket_frontmatter_null | src/templates/chunk/GOAL.md (renamed to .jinja2) |
| proposed_chunks_frontmatter | docs/narratives/0001-cross_repo_chunks/OVERVIEW.md (seq numbers removed) |
| proposed_chunks_frontmatter | docs/narratives/0002-subsystem_documentation/OVERVIEW.md |
| proposed_chunks_frontmatter | docs/narratives/0003-investigations/OVERVIEW.md |
| proposed_chunks_frontmatter | docs/subsystems/0001-template_system/OVERVIEW.md |
| subsystem_docs_update | docs/subsystems/0002-workflow_artifacts/OVERVIEW.md |
| template_drift_prevention | src/templates/commands/*.jinja2 (glob pattern) |
| template_system_consolidation | docs/subsystems/0001-template_system/OVERVIEW.md |
| update_crossref_format | docs/**/*.md, src/**/*.py, etc. (glob patterns) |

### Undocumented Code Areas (no chunk references)
- **src/constants.py** - Project-wide constants
- **src/validation.py** - Validation utilities

### Status Anomalies
- **coderef_format_prompting**: HISTORICAL (superseded by symbolic_code_refs)
- **orch_unblock_transition**: FUTURE (not yet implemented)
