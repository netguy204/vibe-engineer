# Phases 3-6: Combined Analysis

This document consolidates phases 3-6 of the migration analysis, building on the operator-approved subsystem structure:

**Final Subsystem Structure (6 subsystems)**:
1. template_system (EXISTS - 9 chunks)
2. workflow_artifacts (EXISTS - 40+ chunks)
3. orchestrator (NEW - 21 chunks)
4. cross_repo_operations (NEW - 21 chunks including git_sync)
5. cluster_analysis (NEW - 6 chunks)
6. friction_tracking (NEW - 5 chunks)

---

## Phase 3: Entity & Lifecycle Mapping

### Entities by Subsystem

#### template_system
| Entity | Type | States | Key Attributes |
|--------|------|--------|----------------|
| Template | VALUE_OBJECT | N/A | collection, name, path |
| VeConfig | VALUE_OBJECT | N/A | is_ve_source_repo, config values |
| RenderResult | VALUE_OBJECT | N/A | created, skipped, overwritten files |
| TemplateContext | VALUE_OBJECT | N/A | active chunk/narrative/subsystem |

*No lifecycle entities - all are value objects for template rendering*

#### workflow_artifacts
| Entity | Type | States | Key Attributes |
|--------|------|--------|----------------|
| Chunk | ENTITY | FUTURE → IMPLEMENTING → ACTIVE → SUPERSEDED/HISTORICAL | status, code_references, created_after |
| Narrative | ENTITY | DRAFTING → ACTIVE → COMPLETED | status, proposed_chunks, created_after |
| Investigation | ENTITY | ONGOING → SOLVED/NOTED/DEFERRED | status, proposed_chunks, created_after |
| Subsystem | ENTITY | DISCOVERING → DOCUMENTED → REFACTORING → STABLE → DEPRECATED | status, code_references, chunks |
| ArtifactIndex | VALUE_OBJECT | N/A | cached ordering by type |
| SymbolicReference | VALUE_OBJECT | N/A | file_path#symbol_path |
| ProposedChunk | VALUE_OBJECT | N/A | prompt, chunk_directory |

**Lifecycle Diagrams**:

```
Chunk Lifecycle:
FUTURE ──create──> IMPLEMENTING ──complete──> ACTIVE
                         │                      │
                         └──abandon──> HISTORICAL
                                               │
                                       supersede──> SUPERSEDED

Narrative Lifecycle:
DRAFTING ──approve──> ACTIVE ──complete──> COMPLETED

Investigation Lifecycle:
ONGOING ──solved──> SOLVED
    │
    ├──noted──> NOTED
    │
    └──deferred──> DEFERRED

Subsystem Lifecycle:
DISCOVERING ──document──> DOCUMENTED ──refactor──> REFACTORING ──stabilize──> STABLE
                              ↑              │                                    │
                              └──pause───────┘                         deprecate──> DEPRECATED
```

#### orchestrator
| Entity | Type | States | Key Attributes |
|--------|------|--------|----------------|
| WorkUnit | ENTITY | READY → RUNNING → BLOCKED/NEEDS_ATTENTION/DONE | chunk, phase, status, worktree, priority |
| Daemon | ENTITY | STOPPED → RUNNING | pid, uptime, port |
| Scheduler | VALUE_OBJECT | N/A | max_agents, dispatch_interval |
| AgentResult | VALUE_OBJECT | N/A | success, output, session_id |
| Worktree | ENTITY | CREATED → ACTIVE → MERGED/REMOVED | path, branch, chunk |
| AttentionItem | ENTITY | PENDING → ANSWERED → RESOLVED | type, chunk, question, blocks_count |
| Conflict | ENTITY | DETECTED → RESOLVED | chunk_a, chunk_b, verdict |

**Lifecycle Diagrams**:

```
WorkUnit Lifecycle:
READY ──dispatch──> RUNNING ──complete──> DONE
    │                   │
    │                   ├──question──> NEEDS_ATTENTION ──answer──> READY
    │                   │
    │                   └──conflict──> BLOCKED ──resolve──> READY
    │
    └──inject──> READY (from FUTURE chunk)

Daemon Lifecycle:
STOPPED ──start──> RUNNING ──stop──> STOPPED
```

#### cross_repo_operations
| Entity | Type | States | Key Attributes |
|--------|------|--------|----------------|
| TaskConfig | VALUE_OBJECT | N/A | external_artifact_repo, projects |
| ExternalArtifactRef | VALUE_OBJECT | N/A | repo, artifact_id, artifact_type, track, pinned, created_after |
| RepoCache | ENTITY | EMPTY → CLONED → UPDATED | repo_url, local_path, last_sync |

*Mostly value objects - cross-repo operations are transformations on artifacts*

#### cluster_analysis
| Entity | Type | States | Key Attributes |
|--------|------|--------|----------------|
| SuggestPrefixResult | VALUE_OBJECT | N/A | suggested_prefix, similar_chunks, similarity_scores |
| ClusterRenameResult | VALUE_OBJECT | N/A | renamed_chunks, old_names, new_names |

*All value objects - analysis operations*

#### friction_tracking
| Entity | Type | States | Key Attributes |
|--------|------|--------|----------------|
| FrictionEntry | ENTITY | OPEN → ADDRESSED → RESOLVED | id, date, theme, title, description |
| FrictionTheme | VALUE_OBJECT | N/A | id, name |

**Lifecycle Diagram**:
```
FrictionEntry Lifecycle:
OPEN ──propose_chunk──> ADDRESSED ──complete_chunk──> RESOLVED
```

*Status is derived: OPEN if not in any proposed_chunks.addresses, ADDRESSED if chunk exists, RESOLVED if chunk is ACTIVE*

---

## Phase 4: Business Rule Extraction

### Invariants by Subsystem

#### template_system (from existing OVERVIEW.md)
1. **All templates must be rendered through the template system** - Direct Jinja2 bypasses configured Environment
2. **Template files must use .jinja2 suffix** - Enables syntax highlighting, stripped on write
3. **Include paths resolve relative to template collection** - Collections are self-contained

#### workflow_artifacts (from existing OVERVIEW.md + chunk success criteria)
1. **Artifact ordering is determined by created_after frontmatter field** - Causal DAG ordering
2. **Every workflow artifact must have a created_after field** - Array of short names
3. **Every workflow artifact must have a status field** - Enables lifecycle management
4. **Status values must be defined as StrEnum in models.py** - Type safety
5. **Frontmatter schema must be a Pydantic model in models.py** - Validation
6. **Manager class must implement the core interface** - enumerate_, create_, parse_frontmatter
7. **Creation must use the template_system** - Via render_to_directory()
8. **All workflow artifacts must support external references** - Cross-repo capability
9. **Frontmatter must include proposed_chunks field** - Mechanical discovery
10. **Status transitions must be defined in both template and code** - VALID_*_TRANSITIONS dicts
11. **All task-aware commands must support --projects flag** - Selective linking

#### orchestrator (from chunk success criteria)
1. **Only one daemon instance allowed per project** - PID file enforcement
2. **Work unit transitions are logged for debugging** - Status audit trail
3. **Each phase is a fresh agent context** - No context carryover
4. **Worktrees are isolated execution environments** - Branch per chunk
5. **Configurable max agent slots** - Control throughput/cost
6. **Questions must be captured with session_id for resume** - Attention queue pattern
7. **Conflicts must be detected before parallel execution** - Oracle pattern
8. **Phase completion detected when async generator exhausts** - Clean completion
9. **Daemon must broadcast state changes to dashboard** - WebSocket updates

#### cross_repo_operations (from chunk success criteria)
1. **Task directory detected by presence of .ve-task.yaml** - Context detection
2. **External references must have pinned SHA for archaeology** - Point-in-time snapshots
3. **All specified directories must be VE-initialized git repos** - Validation
4. **Bidirectional references enable full graph traversal** - Dependents in both directions
5. **Sync updates pinned fields to current SHA** - Archaeology preservation
6. **External artifacts participate in local causal ordering** - created_after in external.yaml
7. **External resolution works in both task and single-repo mode** - Dual context support

#### cluster_analysis (from chunk success criteria)
1. **TF-IDF similarity threshold ~0.4 for suggestions** - Avoid weak matches
2. **Top-k similar chunks must share prefix for suggestion** - Consensus requirement
3. **Suggest-prefix runs during chunk planning** - Integrated workflow
4. **Batch rename preserves git history** - Proper mv operations

#### friction_tracking (from chunk success criteria)
1. **Entry status is derived, not stored** - Computed from proposed_chunks
2. **Sequential F-number IDs for stable references** - F001, F002, etc.
3. **Pattern emergence at 3+ entries in theme** - Trigger for chunk proposal
4. **Friction log has indefinite lifespan** - Journal, not document

---

## Phase 5: Domain Boundary Refinement

### Final Chunk Assignment

#### template_system (9 chunks) - EXISTS, no changes
- template_unified_module
- template_system_consolidation
- template_drift_prevention
- migrate_chunks_template
- project_init_command
- init_creates_chunks_dir
- jinja_backrefs
- code_to_docs_backrefs
- restore_template_content

#### workflow_artifacts (55 chunks) - EXISTS, absorb more
**Already attributed** (36): See existing OVERVIEW.md chunks list

**Newly attributed** (19):
- bidirectional_refs
- symbolic_code_refs
- proposed_chunks_frontmatter
- valid_transitions
- populate_created_after
- bug_type_field
- investigation_chunk_refs
- ordering_field
- ordering_field_clarity
- ordering_active_only
- ordering_audit_seqnums
- ordering_remove_seqno
- artifact_ordering_index
- artifact_list_ordering
- artifact_index_no_git
- artifact_promote
- causal_ordering_migration
- update_crossref_format
- background_keyword_semantic
- learning_philosophy_docs
- spec_docs_update

#### orchestrator (21 chunks) - NEW
- orch_foundation
- orch_scheduling
- orch_dashboard
- orch_attention_queue
- orch_attention_reason
- orch_blocked_lifecycle
- orch_broadcast_invariant
- orch_conflict_oracle
- orch_conflict_template_fix
- orch_activate_on_inject
- orch_agent_question_tool
- orch_agent_skills
- orch_question_forward
- orch_sandbox_enforcement
- orch_mechanical_commit
- orch_tcp_port
- orch_verify_active
- orch_inject_validate
- orch_inject_path_compat
- orch_submit_future_cmd
- deferred_worktree_creation

**FUTURE chunk (exclude from synthesis)**:
- orch_unblock_transition

#### cross_repo_operations (21 chunks) - NEW
**Task/external operations**:
- task_init
- task_init_scaffolding
- task_config_local_paths
- task_aware_investigations
- task_aware_narrative_cmds
- task_aware_subsystem_cmds
- task_chunk_validation
- task_list_proposed
- task_qualified_refs
- task_status_command
- taskdir_context_cmds
- chunk_create_task_aware
- chunk_list_repo_source
- list_task_aware
- cross_repo_schemas

**External reference utilities**:
- external_resolve
- external_resolve_all_types
- external_chunk_causal
- consolidate_ext_refs
- consolidate_ext_ref_utils
- copy_as_external
- accept_full_artifact_paths
- selective_artifact_friction
- selective_project_linking
- remove_external_ref

**Git/sync (folded in per operator decision)**:
- git_local_utilities
- ve_sync_command
- sync_all_workflows

#### cluster_analysis (6 chunks) - NEW
- cluster_list_command
- cluster_naming_guidance
- cluster_prefix_suggest
- cluster_rename
- cluster_seed_naming
- cluster_subsystem_prompt

#### friction_tracking (5 chunks) - NEW
- friction_template_and_cli
- friction_chunk_workflow
- friction_claude_docs
- friction_noninteractive
- friction_chunk_linking

### Chunk Disposition Summary

| Disposition | Count | Notes |
|-------------|-------|-------|
| Absorbed into existing subsystem | 55 | workflow_artifacts grows |
| Absorbed into new subsystem | 53 | orch, cross_repo, cluster, friction |
| HISTORICAL (provenance only) | 1 | coderef_format_prompting |
| FUTURE (exclude) | 1 | orch_unblock_transition |
| Uncategorized | 8 | Misc improvements - see below |

### Uncategorized Chunks

These chunks don't fit cleanly into any subsystem:

| Chunk | Best Fit | Rationale |
|-------|----------|-----------|
| rename_chunk_start_to_create | workflow_artifacts | CLI consistency |
| fix_ticket_frontmatter_null | workflow_artifacts | Template fix |
| remove_trivial_tests | (none - meta) | Testing philosophy |
| document_investigations | workflow_artifacts | Documentation |
| narrative_consolidation | workflow_artifacts | Narrative management |
| narrative_backreference_support | workflow_artifacts | Backreference support |

---

## Phase 6: Infrastructure Annotation

### Infrastructure Patterns (Not Subsystems)

#### CLI Pattern (src/ve.py)
- **Used by**: All subsystems
- **Pattern**: Click command groups with consistent naming
- **Consistency**: HIGH (all commands follow same pattern)
- **Recommendation**: Not a subsystem - standard CLI framework usage

#### Error Handling Pattern
- **Used by**: All subsystems
- **Pattern**: Custom exception classes per module
- **Consistency**: HIGH
- **Recommendation**: Not a subsystem - standard Python patterns

#### Testing Pattern
- **Used by**: All subsystems
- **Pattern**: pytest with fixtures, integration tests
- **Documentation**: docs/trunk/TESTING_PHILOSOPHY.md
- **Recommendation**: Already documented as trunk document

### Infrastructure Chunks

| Chunk | Pattern | Disposition |
|-------|---------|-------------|
| git_local_utilities | Git operations | Folded into cross_repo_operations |
| remove_trivial_tests | Testing philosophy | Archive only (no subsystem) |

---

## Summary

### Final Subsystem Structure

| Subsystem | Status | Chunks | Key Responsibility |
|-----------|--------|--------|-------------------|
| template_system | EXISTS | 9 | Jinja2 template rendering |
| workflow_artifacts | EXISTS | 55 | Artifact lifecycle, schemas, ordering |
| orchestrator | NEW | 21 | Parallel agent execution |
| cross_repo_operations | NEW | 21 | Task directories, external refs, sync |
| cluster_analysis | NEW | 6 | Chunk naming similarity |
| friction_tracking | NEW | 5 | Friction log management |
| **Total** | | **117** | (118 - 1 FUTURE) |

### Next Steps

1. **Phase 7**: Plan backreference migration (# Chunk: → # Subsystem:)
2. **Phase 8**: Synthesize OVERVIEW.md for 4 new subsystems
3. **Phase 9**: Create execution order and validation plan
