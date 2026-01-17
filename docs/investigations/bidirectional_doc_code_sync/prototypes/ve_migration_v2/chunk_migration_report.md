# Chunk Migration Report

## Executive Summary

- **Chunks analyzed**: 118 (116 ACTIVE, 1 HISTORICAL, 1 FUTURE)
- **Subsystems created**: 6 (2 existing updated, 4 new)
- **Code files to migrate**: ~25
- **Backreferences to update**: ~500

---

## Migration Map

### Chunk -> Subsystem Mapping

| Chunk | Status | Target Subsystem | Disposition |
|-------|--------|------------------|-------------|
| accept_full_artifact_paths | ACTIVE | workflow_artifacts, cross_repo_operations | split |
| agent_discovery_command | ACTIVE | (infrastructure) | documentation only |
| artifact_copy_backref | ACTIVE | cross_repo_operations | absorbed |
| artifact_index_no_git | ACTIVE | workflow_artifacts | absorbed |
| artifact_list_ordering | ACTIVE | workflow_artifacts | absorbed |
| artifact_ordering_index | ACTIVE | workflow_artifacts | absorbed |
| artifact_promote | ACTIVE | cross_repo_operations | absorbed |
| background_keyword_semantic | ACTIVE | orchestrator | absorbed |
| bidirectional_refs | ACTIVE | workflow_artifacts | absorbed |
| bug_type_field | ACTIVE | workflow_artifacts | absorbed |
| causal_ordering_migration | ACTIVE | workflow_artifacts | absorbed |
| chunk_create_guard | ACTIVE | workflow_artifacts | absorbed |
| chunk_create_task_aware | ACTIVE | cross_repo_operations | absorbed |
| chunk_frontmatter_model | ACTIVE | workflow_artifacts | absorbed |
| chunk_list_command-ve-002 | ACTIVE | workflow_artifacts | absorbed |
| chunk_list_repo_source | ACTIVE | cross_repo_operations | absorbed |
| chunk_overlap_command | ACTIVE | workflow_artifacts | absorbed |
| chunk_template_expansion | ACTIVE | workflow_artifacts | absorbed |
| chunk_validate | ACTIVE | workflow_artifacts | absorbed |
| cluster_list_command | ACTIVE | cluster_analysis | absorbed |
| cluster_naming_guidance | ACTIVE | cluster_analysis | absorbed |
| cluster_prefix_suggest | ACTIVE | cluster_analysis | absorbed |
| cluster_rename | ACTIVE | cluster_analysis | absorbed |
| cluster_seed_naming | ACTIVE | cluster_analysis | absorbed |
| cluster_subsystem_prompt | ACTIVE | cluster_analysis | absorbed |
| code_to_docs_backrefs | ACTIVE | workflow_artifacts | absorbed |
| coderef_format_prompting | HISTORICAL | workflow_artifacts | provenance only |
| consolidate_ext_ref_utils | ACTIVE | cross_repo_operations | absorbed |
| consolidate_ext_refs | ACTIVE | cross_repo_operations | absorbed |
| copy_as_external | ACTIVE | cross_repo_operations | absorbed |
| cross_repo_schemas | ACTIVE | cross_repo_operations | absorbed |
| deferred_worktree_creation | ACTIVE | orchestrator | absorbed |
| document_investigations | ACTIVE | workflow_artifacts | absorbed |
| external_chunk_causal | ACTIVE | cross_repo_operations | absorbed |
| external_resolve | ACTIVE | cross_repo_operations | absorbed |
| external_resolve_all_types | ACTIVE | cross_repo_operations | absorbed |
| fix_ticket_frontmatter_null | ACTIVE | workflow_artifacts | absorbed |
| friction_chunk_linking | ACTIVE | friction_log | absorbed |
| friction_chunk_workflow | ACTIVE | friction_log | absorbed |
| friction_claude_docs | ACTIVE | friction_log | absorbed |
| friction_noninteractive | ACTIVE | friction_log | absorbed |
| friction_template_and_cli | ACTIVE | friction_log | absorbed |
| future_chunk_creation | ACTIVE | workflow_artifacts | absorbed |
| git_local_utilities | ACTIVE | (infrastructure) | supporting pattern |
| implement_chunk_start-ve-001 | ACTIVE | workflow_artifacts | absorbed |
| init_creates_chunks_dir | ACTIVE | template_system | absorbed |
| investigation_chunk_refs | ACTIVE | workflow_artifacts | absorbed |
| investigation_commands | ACTIVE | workflow_artifacts | absorbed |
| investigation_template | ACTIVE | workflow_artifacts | absorbed |
| jinja_backrefs | ACTIVE | template_system | absorbed |
| learning_philosophy_docs | ACTIVE | workflow_artifacts | absorbed |
| list_task_aware | ACTIVE | cross_repo_operations | absorbed |
| migrate_chunks_template | ACTIVE | template_system | absorbed |
| narrative_backreference_support | ACTIVE | workflow_artifacts | absorbed |
| narrative_cli_commands | ACTIVE | workflow_artifacts | absorbed |
| narrative_consolidation | ACTIVE | workflow_artifacts | absorbed |
| orch_activate_on_inject | ACTIVE | orchestrator | absorbed |
| orch_agent_question_tool | ACTIVE | orchestrator | absorbed |
| orch_agent_skills | ACTIVE | orchestrator | absorbed |
| orch_attention_queue | ACTIVE | orchestrator | absorbed |
| orch_attention_reason | ACTIVE | orchestrator | absorbed |
| orch_blocked_lifecycle | ACTIVE | orchestrator | absorbed |
| orch_broadcast_invariant | ACTIVE | orchestrator | absorbed |
| orch_conflict_oracle | ACTIVE | orchestrator | absorbed |
| orch_conflict_template_fix | ACTIVE | orchestrator | absorbed |
| orch_dashboard | ACTIVE | orchestrator | absorbed |
| orch_foundation | ACTIVE | orchestrator | absorbed |
| orch_inject_path_compat | ACTIVE | orchestrator | absorbed |
| orch_inject_validate | ACTIVE | orchestrator | absorbed |
| orch_mechanical_commit | ACTIVE | orchestrator | absorbed |
| orch_question_forward | ACTIVE | orchestrator | absorbed |
| orch_sandbox_enforcement | ACTIVE | orchestrator | absorbed |
| orch_scheduling | ACTIVE | orchestrator | absorbed |
| orch_submit_future_cmd | ACTIVE | orchestrator | absorbed |
| orch_tcp_port | ACTIVE | orchestrator | absorbed |
| orch_unblock_transition | FUTURE | orchestrator | excluded (FUTURE) |
| orch_verify_active | ACTIVE | orchestrator | absorbed |
| ordering_active_only | ACTIVE | workflow_artifacts | absorbed |
| ordering_audit_seqnums | ACTIVE | workflow_artifacts | absorbed |
| ordering_field | ACTIVE | workflow_artifacts | absorbed |
| ordering_field_clarity | ACTIVE | workflow_artifacts | absorbed |
| ordering_remove_seqno | ACTIVE | workflow_artifacts | absorbed |
| populate_created_after | ACTIVE | workflow_artifacts | absorbed |
| project_init_command | ACTIVE | template_system | absorbed |
| proposed_chunks_frontmatter | ACTIVE | workflow_artifacts | absorbed |
| remove_external_ref | ACTIVE | cross_repo_operations | absorbed |
| remove_trivial_tests | ACTIVE | (infrastructure) | supporting pattern |
| rename_chunk_start_to_create | ACTIVE | workflow_artifacts | absorbed |
| respect_future_intent | ACTIVE | orchestrator | absorbed |
| restore_template_content | ACTIVE | template_system | absorbed |
| selective_artifact_friction | ACTIVE | friction_log, cross_repo_operations | split |
| selective_project_linking | ACTIVE | cross_repo_operations | absorbed |
| spec_docs_update | ACTIVE | (infrastructure) | documentation only |
| subsystem_cli_scaffolding | ACTIVE | workflow_artifacts | absorbed |
| subsystem_docs_update | ACTIVE | workflow_artifacts | absorbed |
| subsystem_impact_resolution | ACTIVE | workflow_artifacts | absorbed |
| subsystem_schemas_and_model | ACTIVE | workflow_artifacts | absorbed |
| subsystem_status_transitions | ACTIVE | workflow_artifacts | absorbed |
| subsystem_template | ACTIVE | workflow_artifacts | absorbed |
| symbolic_code_refs | ACTIVE | workflow_artifacts | absorbed |
| sync_all_workflows | ACTIVE | cross_repo_operations | absorbed |
| task_aware_investigations | ACTIVE | cross_repo_operations | absorbed |
| task_aware_narrative_cmds | ACTIVE | cross_repo_operations | absorbed |
| task_aware_subsystem_cmds | ACTIVE | cross_repo_operations | absorbed |
| task_chunk_validation | ACTIVE | cross_repo_operations | absorbed |
| task_config_local_paths | ACTIVE | cross_repo_operations | absorbed |
| task_init | ACTIVE | cross_repo_operations | absorbed |
| task_init_scaffolding | ACTIVE | cross_repo_operations | absorbed |
| task_list_proposed | ACTIVE | cross_repo_operations | absorbed |
| task_qualified_refs | ACTIVE | cross_repo_operations | absorbed |
| task_status_command | ACTIVE | cross_repo_operations | absorbed |
| taskdir_context_cmds | ACTIVE | cross_repo_operations | absorbed |
| template_drift_prevention | ACTIVE | template_system | absorbed |
| template_system_consolidation | ACTIVE | template_system | absorbed |
| template_unified_module | ACTIVE | template_system | absorbed |
| update_crossref_format | ACTIVE | workflow_artifacts | absorbed |
| valid_transitions | ACTIVE | workflow_artifacts | absorbed |
| ve_sync_command | ACTIVE | cross_repo_operations | absorbed |

---

### Subsystem Summary

| Subsystem | Status | Intent | Chunks Absorbed | Code Locations |
|-----------|--------|--------|-----------------|----------------|
| workflow_artifacts | EXISTS (STABLE) | Unified workflow artifact lifecycle | 35 | chunks.py, narratives.py, investigations.py, subsystems.py, models.py, artifact_ordering.py |
| template_system | EXISTS (STABLE) | Unified template rendering | 6 | template_system.py, project.py |
| orchestrator | NEW | Parallel agent management | 20 | orchestrator/*.py |
| cross_repo_operations | NEW | Multi-repo task mode | 25 | task_utils.py, task_init.py, external_refs.py, external_resolve.py, sync.py |
| cluster_analysis | NEW | Chunk naming patterns | 6 | cluster_analysis.py, cluster_rename.py |
| friction_log | NEW | Pain point tracking | 6 | friction.py |

---

## Backreference Migration Summary

| Metric | Count |
|--------|-------|
| Files with `# Chunk:` before | ~30 |
| Files with `# Subsystem:` after | ~25 |
| Backreferences to consolidate | ~500 |
| Backreferences to remove (infrastructure) | ~18 |
| New backreferences to add | ~2 |
| Template files requiring update | 6 |

---

## Human Effort Required

### Synthesis Confidence by Subsystem

| Subsystem | Synthesized | Inferred | Needs Human | Conflicts | Confidence |
|-----------|-------------|----------|-------------|-----------|------------|
| orchestrator | 34 | 6 | 5 | 0 | 76% |
| cross_repo_operations | 37 | 5 | 5 | 0 | 79% |
| cluster_analysis | 22 | 3 | 5 | 0 | 73% |
| friction_log | 30 | 4 | 5 | 0 | 77% |
| **Total (new)** | **123** | **18** | **20** | **0** | **76%** |

### Human Tasks by Category

| Category | Count | Estimated Effort | Priority |
|----------|-------|------------------|----------|
| Conflict resolution | 0 | 0 min | N/A |
| Business context (Intent) | 4 | 10 min each = 40 min | MEDIUM |
| Scope clarification (Out of Scope) | 4 | 5 min each = 20 min | MEDIUM |
| Deviation documentation | 4 | 10 min each = 40 min | LOW |
| Reference validation | 4 | 5 min each = 20 min | LOW |

**Total human review time**: ~2 hours

### Effort Estimate

- **Automated work**: ~8 hours saved (chunk reading, consolidation, analysis, conflict detection)
- **Human review needed**: ~2 hours (context enrichment, validation)
- **Migration execution**: ~3 hours (backreference updates, testing)
- **Overall automation rate**: ~76%

### Files Requiring Human Review

Priority order for human review:

1. **HIGH** (lowest confidence):
   - `ve_migration_v2/subsystems/cluster_analysis/OVERVIEW.md` - 73% confidence
   - Review [NEEDS_HUMAN] sections for business context

2. **MEDIUM** (needs business context):
   - `ve_migration_v2/subsystems/orchestrator/OVERVIEW.md` - 76% confidence
   - `ve_migration_v2/subsystems/friction_log/OVERVIEW.md` - 77% confidence
   - `ve_migration_v2/subsystems/cross_repo_operations/OVERVIEW.md` - 79% confidence

3. **LOW** (validation only):
   - All subsystems: verify code_references are current
   - Validate inferred scope items

---

## Validation Results

| Check | Result |
|-------|--------|
| All subsystem OVERVIEW.md files created | PASS (4 files) |
| All backreferences migrated | PENDING (execution not yet started) |
| All tests passing | PENDING |
| No orphan chunk references | PENDING |
| Conflicts resolved | PASS (0 conflicts) |

---

## Lessons Learned

### What Worked Well

1. **Prefix clustering was highly effective** - orch_* chunks mapped cleanly to orchestrator subsystem
2. **Existing subsystems confirmed** - workflow_artifacts and template_system boundaries validated by chunk analysis
3. **File cluster analysis** - >50% shared files reliably identified capability boundaries
4. **No conflicts** - Chunk content was complementary, not contradictory

### Recommendations for Future Migrations

1. **Naming conventions matter** - Projects with consistent chunk prefixes (orch_*, task_*, etc.) migrate more easily
2. **HISTORICAL status is valuable** - Clearly marking superseded chunks prevents confusion
3. **Comprehensive code_references** - Chunks with detailed code_references produce better subsystem docs
4. **Document "out of scope" early** - Chunks rarely document what they don't cover

### Areas for Process Improvement

1. **Automatic code_reference validation** - Tool to verify refs point to existing symbols
2. **Deviation detection** - Automatic identification of code that doesn't match chunk descriptions
3. **Interactive conflict resolution** - Better workflow for human decisions on conflicts

---

## Intermediate Output Files

| Phase | Output File | Purpose |
|-------|-------------|---------|
| 1 | `phase1_chunk_inventory.md` | Chunk map, all cluster types |
| 2 | `phase2_business_capabilities.md` | Chunk-informed capability discovery |
| 3 | `phase3_entity_lifecycle.md` | Entity/value object mapping |
| 4 | `phase4_business_rules.md` | Invariants with conflict resolution |
| 5 | `phase5_domain_boundaries.md` | Subsystem boundaries with granularity decisions |
| 6 | `phase6_infrastructure.md` | Infrastructure patterns |
| 7 | `phase7_backreference_plan.md` | Migration plan with priorities |
| 8 | `phase8_synthesis_archive.md` | Synthesized docs and archive plan |
| 9 | `phase9_execution_order.md` | Prioritized execution plan |
| Final | `chunk_migration_report.md` | This report |

## Subsystem Files Created

| Path | Purpose |
|------|---------|
| `ve_migration_v2/subsystems/orchestrator/OVERVIEW.md` | Orchestrator subsystem |
| `ve_migration_v2/subsystems/cross_repo_operations/OVERVIEW.md` | Cross-repo operations subsystem |
| `ve_migration_v2/subsystems/cluster_analysis/OVERVIEW.md` | Cluster analysis subsystem |
| `ve_migration_v2/subsystems/friction_log/OVERVIEW.md` | Friction log subsystem |
