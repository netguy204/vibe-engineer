# Phase 5: Domain Boundary Refinement

## Proposed Subsystems

### 1. workflow_artifacts (EXISTING - STABLE)

- **Business intent**: Provide a unified structural pattern for documentation-driven workflow artifacts (chunks, narratives, investigations, subsystems) that ensures consistent lifecycle management, cross-repository capability, and mechanical discoverability of work.

- **Core entities**: Chunk, Narrative, Investigation, Subsystem

- **Key invariants**:
  1. Every artifact must have `status` and `created_after` fields
  2. Status transitions follow defined state machines
  3. Only one IMPLEMENTING chunk per repository
  4. Causal ordering via `created_after` DAG
  5. Code references must be symbolic

- **Contributing chunks**:
  | Chunk | Status | Disposition | Notes |
  |-------|--------|-------------|-------|
  | implement_chunk_start | ACTIVE | fully absorbed | Core chunk manager |
  | chunk_frontmatter_model | ACTIVE | fully absorbed | ChunkStatus, ChunkFrontmatter |
  | chunk_validate | ACTIVE | fully absorbed | Validation framework |
  | chunk_create_guard | ACTIVE | fully absorbed | IMPLEMENTING guard |
  | future_chunk_creation | ACTIVE | fully absorbed | FUTURE status |
  | chunk_list_command | ACTIVE | fully absorbed | List operations |
  | chunk_overlap_command | ACTIVE | fully absorbed | Overlap detection |
  | chunk_template_expansion | ACTIVE | fully absorbed | Template context |
  | narrative_cli_commands | ACTIVE | fully absorbed | Narrative manager |
  | narrative_backreference_support | ACTIVE | fully absorbed | Narrative validation |
  | narrative_consolidation | ACTIVE | fully absorbed | Consolidation feature |
  | investigation_commands | ACTIVE | fully absorbed | Investigation manager |
  | investigation_template | ACTIVE | fully absorbed | Investigation template |
  | investigation_chunk_refs | ACTIVE | fully absorbed | Investigation traceability |
  | subsystem_schemas_and_model | ACTIVE | fully absorbed | Subsystem schemas |
  | subsystem_cli_scaffolding | ACTIVE | fully absorbed | Subsystem manager |
  | subsystem_template | ACTIVE | fully absorbed | Subsystem template |
  | subsystem_status_transitions | ACTIVE | fully absorbed | Status transitions |
  | subsystem_impact_resolution | ACTIVE | fully absorbed | Overlap detection |
  | proposed_chunks_frontmatter | ACTIVE | fully absorbed | ProposedChunk model |
  | valid_transitions | ACTIVE | fully absorbed | State machines |
  | bidirectional_refs | ACTIVE | fully absorbed | Bidirectional validation |
  | symbolic_code_refs | ACTIVE | fully absorbed | Reference format |
  | rename_chunk_start_to_create | ACTIVE | fully absorbed | CLI rename |
  | ordering_field | ACTIVE | fully absorbed | created_after field |
  | ordering_field_clarity | ACTIVE | fully absorbed | Documentation |
  | ordering_remove_seqno | ACTIVE | fully absorbed | Short-name directories |
  | ordering_active_only | ACTIVE | fully absorbed | Status-aware tips |
  | artifact_ordering_index | ACTIVE | fully absorbed | ArtifactIndex class |
  | artifact_index_no_git | ACTIVE | fully absorbed | Directory-based staleness |
  | artifact_list_ordering | ACTIVE | fully absorbed | List command ordering |
  | populate_created_after | ACTIVE | fully absorbed | Auto-population |
  | causal_ordering_migration | ACTIVE | fully absorbed | Migration script |
  | update_crossref_format | ACTIVE | fully absorbed | Reference format migration |
  | coderef_format_prompting | HISTORICAL | provenance only | Superseded by symbolic_code_refs |

- **Code locations**: `src/chunks.py`, `src/narratives.py`, `src/investigations.py`, `src/subsystems.py`, `src/models.py`, `src/artifact_ordering.py`

- **Existing subsystem**: docs/subsystems/workflow_artifacts (STABLE) - **AGREEMENT**

---

### 2. template_system (EXISTING - STABLE)

- **Business intent**: Provide a unified template rendering system that ensures all templates receive a consistent set of base parameters and can compose shared content via includes.

- **Core entities**: None (infrastructure)

- **Key invariants**:
  1. All templates must be rendered through template_system
  2. Template files must use .jinja2 suffix
  3. Include paths resolve relative to template collection

- **Contributing chunks**:
  | Chunk | Status | Disposition | Notes |
  |-------|--------|-------------|-------|
  | template_unified_module | ACTIVE | fully absorbed | Core module |
  | template_system_consolidation | ACTIVE | fully absorbed | Consolidation |
  | template_drift_prevention | ACTIVE | fully absorbed | Drift prevention |
  | migrate_chunks_template | ACTIVE | fully absorbed | Migration |
  | jinja_backrefs | ACTIVE | fully absorbed | Jinja comments |
  | restore_template_content | ACTIVE | fully absorbed | Content restoration |

- **Code locations**: `src/template_system.py`, `src/templates/*`

- **Existing subsystem**: docs/subsystems/template_system (STABLE) - **AGREEMENT**

---

### 3. orchestrator (NEW)

- **Business intent**: Enable operators to run multiple AI agents in parallel on different chunks of work, with automatic conflict detection, scheduling, and attention routing when agents need human input.

- **Core entities**: WorkUnit, Conflict, Daemon

- **Key invariants**:
  1. Work units progress through defined state machine
  2. Conflicts must be resolved before parallel execution
  3. Agents operate within sandbox boundaries
  4. Chunks must be committed and have PLAN.md before injection
  5. NEEDS_ATTENTION state requires attention_reason

- **Contributing chunks**:
  | Chunk | Status | Disposition | Notes |
  |-------|--------|-------------|-------|
  | orch_foundation | ACTIVE | fully absorbed | Core daemon and work unit |
  | orch_scheduling | ACTIVE | fully absorbed | Scheduling algorithm |
  | orch_conflict_oracle | ACTIVE | fully absorbed | Conflict detection |
  | orch_dashboard | ACTIVE | fully absorbed | Real-time UI |
  | orch_attention_queue | ACTIVE | fully absorbed | Attention CLI |
  | orch_attention_reason | ACTIVE | fully absorbed | Reason tracking |
  | orch_blocked_lifecycle | ACTIVE | fully absorbed | Blocked handling |
  | orch_activate_on_inject | ACTIVE | fully absorbed | Inject activation |
  | orch_sandbox_enforcement | ACTIVE | fully absorbed | Sandbox security |
  | orch_verify_active | ACTIVE | fully absorbed | Active verification |
  | orch_inject_validate | ACTIVE | fully absorbed | Injection validation |
  | orch_inject_path_compat | ACTIVE | fully absorbed | Path compatibility |
  | orch_mechanical_commit | ACTIVE | fully absorbed | Auto-commit |
  | orch_agent_question_tool | ACTIVE | fully absorbed | Agent questions |
  | orch_agent_skills | ACTIVE | fully absorbed | Agent skills |
  | orch_question_forward | ACTIVE | fully absorbed | Question forwarding |
  | orch_submit_future_cmd | ACTIVE | fully absorbed | Future submission |
  | orch_tcp_port | ACTIVE | fully absorbed | Port configuration |
  | orch_broadcast_invariant | ACTIVE | fully absorbed | Broadcast handling |
  | orch_conflict_template_fix | ACTIVE | fully absorbed | Template fix |
  | orch_unblock_transition | FUTURE | excluded | Not implemented |

- **Code locations**: `src/orchestrator/*.py` (state.py, scheduler.py, daemon.py, api.py, agent.py, models.py, websocket.py)

- **Existing subsystem**: None - **NEW SUBSYSTEM REQUIRED**

---

### 4. cross_repo_operations (NEW)

- **Business intent**: Enable work that spans multiple repositories via a task directory pattern, where a shared external repo holds artifacts and multiple project repos link to them.

- **Core entities**: TaskConfig, ExternalArtifactRef

- **Key invariants**:
  1. Task directory identified by .ve-task.yaml
  2. Repository references use org/repo format
  3. External references track artifact_type and artifact_id
  4. External artifacts participate in local causal ordering
  5. All task-aware commands support --projects flag

- **Contributing chunks**:
  | Chunk | Status | Disposition | Notes |
  |-------|--------|-------------|-------|
  | task_init | ACTIVE | fully absorbed | Task init command |
  | task_init_scaffolding | ACTIVE | fully absorbed | Task scaffolding |
  | task_config_local_paths | ACTIVE | fully absorbed | Path resolution |
  | task_status_command | ACTIVE | fully absorbed | Status command |
  | task_list_proposed | ACTIVE | fully absorbed | Proposed listing |
  | task_qualified_refs | ACTIVE | fully absorbed | Qualified refs |
  | task_chunk_validation | ACTIVE | fully absorbed | Validation |
  | chunk_create_task_aware | ACTIVE | fully absorbed | Task chunk creation |
  | list_task_aware | ACTIVE | fully absorbed | Task-aware listing |
  | task_aware_narrative_cmds | ACTIVE | fully absorbed | Narrative commands |
  | task_aware_investigations | ACTIVE | fully absorbed | Investigation commands |
  | task_aware_subsystem_cmds | ACTIVE | fully absorbed | Subsystem commands |
  | selective_project_linking | ACTIVE | fully absorbed | --projects flag |
  | taskdir_context_cmds | ACTIVE | fully absorbed | Context commands |
  | external_resolve | ACTIVE | fully absorbed | Resolve command |
  | external_resolve_all_types | ACTIVE | fully absorbed | All types |
  | external_chunk_causal | ACTIVE | fully absorbed | Causal ordering |
  | consolidate_ext_refs | ACTIVE | fully absorbed | ExternalArtifactRef |
  | consolidate_ext_ref_utils | ACTIVE | fully absorbed | Utilities |
  | copy_as_external | ACTIVE | fully absorbed | Copy external |
  | artifact_copy_backref | ACTIVE | fully absorbed | Backref update |
  | remove_external_ref | ACTIVE | fully absorbed | Remove external |
  | sync_all_workflows | ACTIVE | fully absorbed | Sync command |
  | ve_sync_command | ACTIVE | fully absorbed | Sync foundation |
  | cross_repo_schemas | ACTIVE | fully absorbed | TaskConfig schema |
  | accept_full_artifact_paths | ACTIVE | partial | Path normalization (shared with workflow_artifacts) |

- **Code locations**: `src/task_utils.py`, `src/task_init.py`, `src/external_refs.py`, `src/external_resolve.py`, `src/sync.py`

- **Existing subsystem**: None - **NEW SUBSYSTEM REQUIRED**

---

### 5. cluster_analysis (NEW)

- **Business intent**: Help users understand and manage chunk naming patterns, suggesting prefixes for cohesion and warning when clusters become too large.

- **Core entities**: None (analysis tool)

- **Key invariants**:
  1. Clusters identified by naming prefix
  2. Large clusters (>threshold) trigger subsystem prompts
  3. Prefix suggestions use TF-IDF similarity

- **Contributing chunks**:
  | Chunk | Status | Disposition | Notes |
  |-------|--------|-------------|-------|
  | cluster_list_command | ACTIVE | fully absorbed | List command |
  | cluster_rename | ACTIVE | fully absorbed | Rename command |
  | cluster_prefix_suggest | ACTIVE | fully absorbed | TF-IDF suggestion |
  | cluster_seed_naming | ACTIVE | fully absorbed | Seed naming |
  | cluster_naming_guidance | ACTIVE | fully absorbed | Documentation |
  | cluster_subsystem_prompt | ACTIVE | fully absorbed | Size warnings |

- **Code locations**: `src/cluster_analysis.py`, `src/cluster_rename.py`

- **Existing subsystem**: None - **NEW SUBSYSTEM REQUIRED**

---

### 6. friction_log (NEW)

- **Business intent**: Capture and track pain points encountered during project use, enabling pattern recognition and improvement prioritization.

- **Core entities**: FrictionEntry, FrictionTheme

- **Key invariants**:
  1. Entry IDs are F{digits} format, sequential
  2. Status is derived (OPEN/ADDRESSED/RESOLVED), not stored
  3. Themes emerge organically from entries
  4. Proposed chunks can address multiple entries

- **Contributing chunks**:
  | Chunk | Status | Disposition | Notes |
  |-------|--------|-------------|-------|
  | friction_template_and_cli | ACTIVE | fully absorbed | Core CLI and template |
  | friction_chunk_workflow | ACTIVE | fully absorbed | Workflow |
  | friction_chunk_linking | ACTIVE | fully absorbed | friction_entries field |
  | friction_claude_docs | ACTIVE | fully absorbed | Documentation |
  | friction_noninteractive | ACTIVE | fully absorbed | Non-interactive mode |
  | selective_artifact_friction | ACTIVE | partial | Task-aware friction (shared with cross_repo) |

- **Code locations**: `src/friction.py`

- **Existing subsystem**: None - **NEW SUBSYSTEM REQUIRED**

---

## Granularity Decisions Log

| Decision | Rationale |
|----------|-----------|
| **Absorbed** causal ordering (ordering_*) into workflow_artifacts | Same entity lifecycle, ArtifactIndex serves all artifact types |
| **Absorbed** external references (consolidate_ext_*) into cross_repo_operations | Mechanism enabling task mode, not standalone capability |
| **Absorbed** project initialization (project_init_*) into template_system/infrastructure | Uses template_system, no domain-specific invariants |
| **Kept** orchestrator separate from workflow_artifacts | Different entities (WorkUnit vs Chunk), different change cadence, different users |
| **Kept** cross_repo_operations separate from workflow_artifacts | Different mode of operation (task directory), additional schemas (TaskConfig) |
| **Kept** cluster_analysis separate from workflow_artifacts | Analysis tooling, not artifact lifecycle; different user need |
| **Kept** friction_log separate from workflow_artifacts | Unique pattern (ledger not lifecycle), derived status |

---

## Chunk Disposition Summary

| Chunk | Status | Disposition | Target Subsystem(s) |
|-------|--------|-------------|---------------------|
| accept_full_artifact_paths | ACTIVE | split | workflow_artifacts (validation), cross_repo_operations (paths) |
| agent_discovery_command | ACTIVE | infrastructure | n/a (documentation only) |
| artifact_copy_backref | ACTIVE | absorbed | cross_repo_operations |
| artifact_index_no_git | ACTIVE | absorbed | workflow_artifacts |
| artifact_list_ordering | ACTIVE | absorbed | workflow_artifacts |
| artifact_ordering_index | ACTIVE | absorbed | workflow_artifacts |
| artifact_promote | ACTIVE | absorbed | cross_repo_operations |
| background_keyword_semantic | ACTIVE | absorbed | orchestrator (documentation) |
| bidirectional_refs | ACTIVE | absorbed | workflow_artifacts |
| bug_type_field | ACTIVE | absorbed | workflow_artifacts |
| causal_ordering_migration | ACTIVE | absorbed | workflow_artifacts |
| chunk_create_guard | ACTIVE | absorbed | workflow_artifacts |
| chunk_create_task_aware | ACTIVE | absorbed | cross_repo_operations |
| chunk_frontmatter_model | ACTIVE | absorbed | workflow_artifacts |
| chunk_list_command-ve-002 | ACTIVE | absorbed | workflow_artifacts |
| chunk_list_repo_source | ACTIVE | absorbed | cross_repo_operations |
| chunk_overlap_command | ACTIVE | absorbed | workflow_artifacts |
| chunk_template_expansion | ACTIVE | absorbed | workflow_artifacts |
| chunk_validate | ACTIVE | absorbed | workflow_artifacts |
| cluster_list_command | ACTIVE | absorbed | cluster_analysis |
| cluster_naming_guidance | ACTIVE | absorbed | cluster_analysis |
| cluster_prefix_suggest | ACTIVE | absorbed | cluster_analysis |
| cluster_rename | ACTIVE | absorbed | cluster_analysis |
| cluster_seed_naming | ACTIVE | absorbed | cluster_analysis |
| cluster_subsystem_prompt | ACTIVE | absorbed | cluster_analysis |
| code_to_docs_backrefs | ACTIVE | absorbed | workflow_artifacts (documentation) |
| coderef_format_prompting | HISTORICAL | provenance only | workflow_artifacts |
| consolidate_ext_ref_utils | ACTIVE | absorbed | cross_repo_operations |
| consolidate_ext_refs | ACTIVE | absorbed | cross_repo_operations |
| copy_as_external | ACTIVE | absorbed | cross_repo_operations |
| cross_repo_schemas | ACTIVE | absorbed | cross_repo_operations |
| deferred_worktree_creation | ACTIVE | absorbed | orchestrator |
| document_investigations | ACTIVE | absorbed | workflow_artifacts (documentation) |
| external_chunk_causal | ACTIVE | absorbed | cross_repo_operations |
| external_resolve | ACTIVE | absorbed | cross_repo_operations |
| external_resolve_all_types | ACTIVE | absorbed | cross_repo_operations |
| fix_ticket_frontmatter_null | ACTIVE | absorbed | workflow_artifacts |
| friction_chunk_linking | ACTIVE | absorbed | friction_log |
| friction_chunk_workflow | ACTIVE | absorbed | friction_log |
| friction_claude_docs | ACTIVE | absorbed | friction_log |
| friction_noninteractive | ACTIVE | absorbed | friction_log |
| friction_template_and_cli | ACTIVE | absorbed | friction_log |
| future_chunk_creation | ACTIVE | absorbed | workflow_artifacts |
| git_local_utilities | ACTIVE | infrastructure | n/a |
| implement_chunk_start-ve-001 | ACTIVE | absorbed | workflow_artifacts |
| init_creates_chunks_dir | ACTIVE | absorbed | template_system |
| investigation_chunk_refs | ACTIVE | absorbed | workflow_artifacts |
| investigation_commands | ACTIVE | absorbed | workflow_artifacts |
| investigation_template | ACTIVE | absorbed | workflow_artifacts |
| jinja_backrefs | ACTIVE | absorbed | template_system |
| learning_philosophy_docs | ACTIVE | absorbed | workflow_artifacts (documentation) |
| list_task_aware | ACTIVE | absorbed | cross_repo_operations |
| migrate_chunks_template | ACTIVE | absorbed | template_system |
| narrative_backreference_support | ACTIVE | absorbed | workflow_artifacts |
| narrative_cli_commands | ACTIVE | absorbed | workflow_artifacts |
| narrative_consolidation | ACTIVE | absorbed | workflow_artifacts |
| orch_* (20 chunks) | ACTIVE | absorbed | orchestrator |
| orch_unblock_transition | FUTURE | excluded | n/a (not implemented) |
| ordering_* (5 chunks) | ACTIVE | absorbed | workflow_artifacts |
| populate_created_after | ACTIVE | absorbed | workflow_artifacts |
| project_init_command | ACTIVE | absorbed | template_system |
| proposed_chunks_frontmatter | ACTIVE | absorbed | workflow_artifacts |
| remove_external_ref | ACTIVE | absorbed | cross_repo_operations |
| remove_trivial_tests | ACTIVE | infrastructure | n/a |
| rename_chunk_start_to_create | ACTIVE | absorbed | workflow_artifacts |
| respect_future_intent | ACTIVE | absorbed | orchestrator |
| restore_template_content | ACTIVE | absorbed | template_system |
| selective_artifact_friction | ACTIVE | split | friction_log, cross_repo_operations |
| selective_project_linking | ACTIVE | absorbed | cross_repo_operations |
| spec_docs_update | ACTIVE | infrastructure | n/a (documentation only) |
| subsystem_* (6 chunks) | ACTIVE | absorbed | workflow_artifacts |
| symbolic_code_refs | ACTIVE | absorbed | workflow_artifacts |
| sync_all_workflows | ACTIVE | absorbed | cross_repo_operations |
| task_* (14 chunks) | ACTIVE | absorbed | cross_repo_operations |
| template_* (4 chunks) | ACTIVE | absorbed | template_system |
| update_crossref_format | ACTIVE | absorbed | workflow_artifacts |
| valid_transitions | ACTIVE | absorbed | workflow_artifacts |
| ve_sync_command | ACTIVE | absorbed | cross_repo_operations |

---

## Summary

| Subsystem | Status | Chunk Count | Primary Code Locations |
|-----------|--------|-------------|------------------------|
| workflow_artifacts | EXISTS (STABLE) | 35 | chunks.py, narratives.py, investigations.py, subsystems.py, models.py, artifact_ordering.py |
| template_system | EXISTS (STABLE) | 6 | template_system.py, templates/ |
| orchestrator | NEW | 21 | orchestrator/*.py |
| cross_repo_operations | NEW | 25 | task_utils.py, task_init.py, external_refs.py, external_resolve.py, sync.py |
| cluster_analysis | NEW | 6 | cluster_analysis.py, cluster_rename.py |
| friction_log | NEW | 6 | friction.py |
| Infrastructure (not subsystem) | - | 7 | validation.py, git_utils.py, repo_cache.py, ve.py (CLI framework) |
