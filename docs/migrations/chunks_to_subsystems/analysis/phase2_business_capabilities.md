# Phase 2: Business Capability Discovery

## Executive Summary

Based on chunk GOAL.md analysis and capability clustering, I've identified **7 distinct business capabilities**:

1. **Parallel Agent Orchestration** (21 chunks) - NEW SUBSYSTEM NEEDED
2. **Cross-Repository Operations** (18+ chunks) - NEW SUBSYSTEM NEEDED
3. **Workflow Artifacts** (40+ chunks) - EXISTS (workflow_artifacts)
4. **Template System** (9 chunks) - EXISTS (template_system)
5. **Chunk Naming & Clustering** (6 chunks) - NEW SUBSYSTEM OR FOLD
6. **Friction Tracking** (5 chunks) - NEW SUBSYSTEM OR FOLD
7. **Git & Sync Infrastructure** (5 chunks) - INFRASTRUCTURE PATTERN

## Chunk-Derived Capabilities

### 1. Parallel Agent Orchestration

**Source clusters**: orch_* (21 chunks)
**Contributing chunks**: orch_foundation, orch_scheduling, orch_dashboard, orch_attention_queue, orch_attention_reason, orch_blocked_lifecycle, orch_broadcast_invariant, orch_conflict_oracle, orch_conflict_template_fix, orch_activate_on_inject, orch_agent_question_tool, orch_agent_skills, orch_question_forward, orch_sandbox_enforcement, orch_mechanical_commit, orch_tcp_port, orch_verify_active, orch_inject_validate, orch_inject_path_compat, orch_submit_future_cmd, (orch_unblock_transition - FUTURE)

**Business intent**: Enable parallel execution of chunk work across multiple AI agents, with:
- A daemon process that manages work units (chunks) through lifecycle phases
- Git worktrees as isolated execution environments
- Scheduling that dispatches ready work to available agent slots
- An attention queue for routing operator decisions
- Conflict detection between concurrent work
- A web dashboard for monitoring and intervention

**Beneficiaries**: Operators managing complex multi-chunk work who need throughput scaling

**Validation**: All 21 chunks exclusively reference src/orchestrator/* files. Perfect file cluster alignment.

**Boundary assessment**: **STRONG** - Self-contained module with clear boundaries

**Existing subsystem**: None - this is a gap
**Recommendation**: Create new subsystem `orchestrator`

---

### 2. Cross-Repository Operations

**Source clusters**: task_* (10), external_* (3), consolidate_* (2), selective_* (2), copy_as_external, accept_full_artifact_paths
**Contributing chunks**: task_init, task_init_scaffolding, task_config_local_paths, task_aware_investigations, task_aware_narrative_cmds, task_aware_subsystem_cmds, task_chunk_validation, task_list_proposed, task_qualified_refs, task_status_command, taskdir_context_cmds, external_resolve, external_resolve_all_types, external_chunk_causal, consolidate_ext_refs, consolidate_ext_ref_utils, copy_as_external, accept_full_artifact_paths, selective_artifact_friction, selective_project_linking, cross_repo_schemas, chunk_create_task_aware, chunk_list_repo_source, list_task_aware, remove_external_ref

**Business intent**: Enable engineering work that spans multiple git repositories by:
- Initializing task directories that coordinate multiple repo worktrees
- Creating/listing artifacts in an external "chunk repo" with references in project repos
- Syncing pinned SHAs to capture point-in-time state for archaeology
- Resolving external references to their canonical content
- Task-aware versions of all artifact commands (chunks, narratives, investigations, subsystems)

**Beneficiaries**: Teams working on features that span multiple codebases

**Validation**: All chunks share src/task_utils.py, src/external_refs.py, src/external_resolve.py

**Boundary assessment**: **STRONG** - Clear business problem, coherent file cluster

**Existing subsystem**: None - workflow_artifacts documents the pattern but not the cross-repo capability
**Narrative exists**: cross_repo_chunks (but only 2 chunks attributed)
**Recommendation**: Create new subsystem `cross_repo_operations`

---

### 3. Workflow Artifacts (Lifecycle Management)

**Source clusters**: chunk_* (8), narrative_* (3), investigation_* (3), subsystem_* (6), ordering_* (5), artifact_* (5), + scattered related chunks
**Contributing chunks**: (see existing workflow_artifacts subsystem - 36+ chunks)

Additional chunks to absorb:
- bidirectional_refs
- symbolic_code_refs
- proposed_chunks_frontmatter
- valid_transitions
- populate_created_after
- bug_type_field
- friction_chunk_linking
- investigation_chunk_refs

**Business intent**: Provide the unified structural pattern for documentation-driven workflow artifacts with:
- Consistent directory structure (docs/{type}s/{name}/)
- Frontmatter schemas as Pydantic models
- Status lifecycle with defined transitions
- Causal ordering via created_after field
- Manager class pattern (enumerate, create, parse)
- Template-based creation via template_system

**Beneficiaries**: All users of the vibe engineering workflow

**Validation**: Already documented - existing workflow_artifacts subsystem has 36 chunks

**Boundary assessment**: **STRONG** - Well-defined by existing subsystem

**Existing subsystem**: workflow_artifacts (STABLE)
**Agreement**: AGREEMENT - existing boundaries are correct
**Recommendation**: Keep as-is, absorb ~8 additional related chunks

---

### 4. Template System

**Source clusters**: template_* (3) + related
**Contributing chunks**: template_unified_module, template_system_consolidation, template_drift_prevention, migrate_chunks_template, project_init_command, init_creates_chunks_dir, jinja_backrefs, code_to_docs_backrefs

**Business intent**: Provide unified template rendering ensuring:
- All templates receive consistent base parameters
- Templates can compose shared content via includes
- Jinja2 Environment with proper configuration
- File writing with .jinja2 suffix stripping
- Slash command rendering

**Beneficiaries**: All artifact creation, project initialization

**Validation**: Already documented - existing template_system subsystem has 9 chunks

**Boundary assessment**: **STRONG** - Well-defined by existing subsystem

**Existing subsystem**: template_system (STABLE)
**Agreement**: AGREEMENT - existing boundaries are correct
**Recommendation**: Keep as-is

---

### 5. Chunk Naming & Clustering

**Source clusters**: cluster_* (6)
**Contributing chunks**: cluster_list_command, cluster_naming_guidance, cluster_prefix_suggest, cluster_rename, cluster_seed_naming, cluster_subsystem_prompt

**Business intent**: Help operators name chunks for semantic alphabetical clustering by:
- Analyzing existing chunk prefixes
- Computing TF-IDF similarity to suggest prefixes
- Batch-renaming chunks that share a prefix
- Prompting for naming guidance during chunk creation

**Beneficiaries**: Operators managing many chunks who need navigational structure

**Validation**: All chunks touch src/cluster_analysis.py or src/cluster_rename.py

**Boundary assessment**: **MODERATE** - Clear capability but small scope

**Existing subsystem**: None
**Recommendation**: Create small subsystem `cluster_analysis` OR fold into workflow_artifacts as a section

---

### 6. Friction Tracking

**Source clusters**: friction_* (5)
**Contributing chunks**: friction_template_and_cli, friction_chunk_workflow, friction_claude_docs, friction_noninteractive, friction_chunk_linking

**Business intent**: Capture and analyze friction points encountered during workflow use by:
- Creating/querying friction log entries
- Deriving entry status (OPEN/ADDRESSED/RESOLVED)
- Grouping entries by theme for pattern detection
- Linking friction entries to chunks that address them

**Beneficiaries**: Operators improving the workflow over time

**Validation**: All chunks touch src/friction.py or friction templates

**Boundary assessment**: **MODERATE** - Clear capability but small scope

**Existing subsystem**: None
**Recommendation**: Create small subsystem `friction_tracking` OR fold into workflow_artifacts as a section

---

### 7. Git & Sync Infrastructure

**Source clusters**: git_local_utilities, ve_sync_command, sync_all_workflows
**Contributing chunks**: git_local_utilities, ve_sync_command, sync_all_workflows

**Business intent**: Provide git operations and synchronization primitives:
- Git worktree and SHA operations
- Syncing external reference pinned fields
- Repository validation

**Beneficiaries**: Other subsystems (cross_repo_operations, orchestrator)

**Validation**: Shared src/git_utils.py, src/sync.py

**Boundary assessment**: **WEAK** - Infrastructure pattern, not domain capability

**Recommendation**: Document as INFRASTRUCTURE pattern, not full subsystem

---

## Code-Discovered Capabilities

### Documentation Updates (CLAUDE.md, docs/)

**Chunks**: background_keyword_semantic, learning_philosophy_docs, spec_docs_update, restore_template_content, ordering_audit_seqnums, code_to_docs_backrefs

**Code locations**: src/templates/claude/CLAUDE.md.jinja2, docs/trunk/

**Business intent**: Maintain and improve CLAUDE.md and documentation

**Why no subsystem**: These chunks improve existing templates, they don't form a coherent domain. Each chunk improves a different aspect.

**Recommendation**: Document as part of template_system scope (CLAUDE.md rendering) or workflow_artifacts scope (documentation structure)

---

## Capability Relationships

```
                    ┌─────────────────────┐
                    │   template_system   │
                    │      (EXISTS)       │
                    └──────────┬──────────┘
                               │ uses
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      workflow_artifacts                          │
│                          (EXISTS)                                │
│  - chunks, narratives, investigations, subsystems lifecycle      │
│  - frontmatter schemas, status transitions, causal ordering      │
│  - artifact_ordering, proposed_chunks, symbolic refs             │
│                                                                  │
│  ┌───────────────────┐   ┌───────────────────────────────────┐  │
│  │ cluster_analysis  │   │        friction_tracking          │  │
│  │  (fold or small)  │   │        (fold or small)            │  │
│  └───────────────────┘   └───────────────────────────────────┘  │
└──────────────────────────────────┬──────────────────────────────┘
                                   │ extends
                                   ▼
        ┌──────────────────────────────────────────────┐
        │          cross_repo_operations               │
        │               (NEW)                          │
        │  - task directories, external.yaml           │
        │  - task-aware artifact commands              │
        │  - sync, resolve, qualified refs             │
        └──────────────────────────────────────────────┘
                                   │
                                   │ used by
                                   ▼
              ┌─────────────────────────────────┐
              │          orchestrator           │
              │             (NEW)               │
              │  - daemon, scheduler, agents    │
              │  - worktrees, attention queue   │
              │  - conflicts, dashboard         │
              └─────────────────────────────────┘
```

---

## Proposed Subsystem Structure

| Proposed Subsystem | Source Capabilities | Chunk Count | Confidence | Status |
|--------------------|---------------------|-------------|------------|--------|
| template_system | Template rendering | 9 | HIGH | EXISTS - keep |
| workflow_artifacts | Artifact lifecycle | 40+ | HIGH | EXISTS - absorb ~8 more |
| orchestrator | Parallel agents | 21 | HIGH | NEW - create |
| cross_repo_operations | Task/external | 18+ | HIGH | NEW - create |
| cluster_analysis | Chunk naming | 6 | MEDIUM | NEW small or FOLD |
| friction_tracking | Friction log | 5 | MEDIUM | NEW small or FOLD |

## Questions for Operator

### Q1: Should cluster_analysis and friction_tracking be standalone subsystems?

**Context**: Both are well-defined capabilities with 5-6 chunks each, but they're relatively small and tightly coupled to workflow_artifacts.

**Options**:
- A) Create standalone subsystems (cluster_analysis, friction_tracking)
- B) Fold both into workflow_artifacts as documented sections
- C) Keep friction_tracking standalone, fold cluster_analysis

**Agent recommendation**: B (fold both) - They're implementation details of the workflow artifact pattern, not independent capabilities

### Q2: Should ordering_* chunks be absorbed into workflow_artifacts?

**Context**: The 5 ordering_* chunks (ordering_active_only, ordering_audit_seqnums, ordering_field, ordering_field_clarity, ordering_remove_seqno) all implement the causal ordering system, which is already documented in workflow_artifacts.

**Options**:
- A) Keep in workflow_artifacts (they're already referenced)
- B) Create separate artifact_ordering subsystem

**Agent recommendation**: A (keep in workflow_artifacts) - Causal ordering is integral to the artifact pattern

### Q3: How should git_sync infrastructure be documented?

**Context**: git_local_utilities, ve_sync_command, sync_all_workflows are infrastructure shared by cross_repo_operations and orchestrator.

**Options**:
- A) Document as "Supporting Patterns" section in repo docs (not a subsystem)
- B) Create small infrastructure subsystem
- C) Fold into cross_repo_operations (primary user)

**Agent recommendation**: C (fold into cross_repo_operations) - The sync capability is primarily about cross-repo coordination

### Q4: Confirm new subsystem names

**Proposed names**:
- `orchestrator` - Parallel agent orchestration
- `cross_repo_operations` - Cross-repository work coordination

**Alternative names considered**:
- `parallel_execution` instead of `orchestrator`
- `task_management` instead of `cross_repo_operations`

**Agent recommendation**: Use `orchestrator` and `cross_repo_operations` - they match the naming conventions of existing chunks and code
