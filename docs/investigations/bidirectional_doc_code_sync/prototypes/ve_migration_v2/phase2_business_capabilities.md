# Phase 2: Business Capability Discovery (Chunk-Informed)

## Chunk-Derived Capabilities

### Capability: Parallel Agent Orchestration
- **Source clusters**: orch_* (21 chunks)
- **Contributing chunks**: orch_foundation (ACTIVE), orch_scheduling (ACTIVE), orch_conflict_oracle (ACTIVE), orch_dashboard (ACTIVE), orch_attention_queue (ACTIVE), orch_attention_reason (ACTIVE), orch_blocked_lifecycle (ACTIVE), orch_activate_on_inject (ACTIVE), orch_sandbox_enforcement (ACTIVE), orch_verify_active (ACTIVE), orch_inject_validate (ACTIVE), orch_inject_path_compat (ACTIVE), orch_mechanical_commit (ACTIVE), orch_agent_question_tool (ACTIVE), orch_agent_skills (ACTIVE), orch_question_forward (ACTIVE), orch_submit_future_cmd (ACTIVE), orch_tcp_port (ACTIVE), orch_broadcast_invariant (ACTIVE), orch_conflict_template_fix (ACTIVE), orch_unblock_transition (FUTURE - excluded)
- **Business intent**: Enable operators to run multiple AI agents in parallel on different chunks of work, with automatic conflict detection, scheduling, and attention routing when agents need human input.
- **Beneficiaries**: Operators managing parallel AI-assisted development workflows
- **Validation**: src/orchestrator/ directory contains 7+ modules (daemon, scheduler, state, api, agent, models, websocket) all dedicated to this capability
- **Boundary assessment**: **STRONG** - Self-contained, clear domain with minimal coupling
- **Boundary adjustments**: None needed

### Capability: Workflow Artifact Lifecycle
- **Source clusters**: chunk_*, narrative_*, investigation_*, subsystem_* (partial), valid_transitions, bidirectional_refs
- **Contributing chunks**: implement_chunk_start (ACTIVE), chunk_list_command (ACTIVE), chunk_overlap_command (ACTIVE), chunk_validate (ACTIVE), chunk_frontmatter_model (ACTIVE), chunk_template_expansion (ACTIVE), chunk_create_guard (ACTIVE), future_chunk_creation (ACTIVE), narrative_cli_commands (ACTIVE), narrative_consolidation (ACTIVE), narrative_backreference_support (ACTIVE), investigation_commands (ACTIVE), investigation_template (ACTIVE), investigation_chunk_refs (ACTIVE), subsystem_cli_scaffolding (ACTIVE), subsystem_schemas_and_model (ACTIVE), subsystem_template (ACTIVE), subsystem_status_transitions (ACTIVE), subsystem_impact_resolution (ACTIVE), proposed_chunks_frontmatter (ACTIVE), valid_transitions (ACTIVE), bidirectional_refs (ACTIVE), symbolic_code_refs (ACTIVE), rename_chunk_start_to_create (ACTIVE)
- **Business intent**: Provide a consistent structure for documentation-driven workflow artifacts (chunks, narratives, investigations, subsystems) with predictable lifecycle states, cross-references, and mechanical discoverability.
- **Beneficiaries**: All users of vibe-engineering - developers, operators, AI agents
- **Validation**: src/chunks.py, src/narratives.py, src/investigations.py, src/subsystems.py all implement the same pattern (enumerate, create, parse_frontmatter)
- **Boundary assessment**: **STRONG** - Exists as documented subsystem already
- **Boundary adjustments**: None - aligns with existing workflow_artifacts subsystem

### Capability: Causal Artifact Ordering
- **Source clusters**: ordering_*, artifact_ordering_index, artifact_index_no_git, populate_created_after
- **Contributing chunks**: ordering_field (ACTIVE), ordering_field_clarity (ACTIVE), ordering_remove_seqno (ACTIVE), ordering_active_only (ACTIVE), ordering_audit_seqnums (ACTIVE), artifact_ordering_index (ACTIVE), artifact_index_no_git (ACTIVE), artifact_list_ordering (ACTIVE), populate_created_after (ACTIVE), causal_ordering_migration (ACTIVE)
- **Business intent**: Maintain a causal ordering of workflow artifacts without requiring global coordination, enabling parallel work and merge-friendly development.
- **Beneficiaries**: Multi-developer teams, parallel AI agents, anyone doing concurrent chunk work
- **Validation**: src/artifact_ordering.py contains ArtifactIndex with topological sorting via created_after DAG
- **Boundary assessment**: **NEEDS_MERGE** - This is a supporting capability for Workflow Artifact Lifecycle, not a standalone subsystem
- **Boundary adjustments**: Should be folded into workflow_artifacts subsystem as a "Causal Ordering" section

### Capability: Cross-Repository Task Mode
- **Source clusters**: task_* (most), chunk_create_task_aware, list_task_aware, selective_project_linking, taskdir_context_cmds
- **Contributing chunks**: task_init (ACTIVE), task_init_scaffolding (ACTIVE), task_config_local_paths (ACTIVE), task_status_command (ACTIVE), task_list_proposed (ACTIVE), task_qualified_refs (ACTIVE), task_chunk_validation (ACTIVE), chunk_create_task_aware (ACTIVE), list_task_aware (ACTIVE), task_aware_narrative_cmds (ACTIVE), task_aware_investigations (ACTIVE), task_aware_subsystem_cmds (ACTIVE), selective_project_linking (ACTIVE), taskdir_context_cmds (ACTIVE)
- **Business intent**: Enable work that spans multiple repositories via a task directory pattern, where a shared external repo holds artifacts and multiple project repos link to them.
- **Beneficiaries**: Developers working on multi-repo projects, platform teams managing cross-cutting concerns
- **Validation**: src/task_utils.py (2700+ lines) + src/task_init.py dedicated to this capability
- **Boundary assessment**: **STRONG** - Clear domain boundary, though uses workflow_artifacts patterns
- **Boundary adjustments**: None needed - distinct from single-repo workflow

### Capability: External Artifact References
- **Source clusters**: external_*, consolidate_ext_*, sync_*, copy_as_external, artifact_copy_backref, remove_external_ref
- **Contributing chunks**: external_resolve (ACTIVE), external_resolve_all_types (ACTIVE), external_chunk_causal (ACTIVE), consolidate_ext_refs (ACTIVE), consolidate_ext_ref_utils (ACTIVE), copy_as_external (ACTIVE), artifact_copy_backref (ACTIVE), remove_external_ref (ACTIVE), sync_all_workflows (ACTIVE), ve_sync_command (ACTIVE)
- **Business intent**: Allow artifacts in one repository to reference and track artifacts in another repository, keeping references synchronized across git boundaries.
- **Beneficiaries**: Multi-repo users, task directory mode users
- **Validation**: src/external_refs.py, src/external_resolve.py, src/sync.py form a cohesive module group
- **Boundary assessment**: **NEEDS_MERGE** - This is the mechanism enabling Cross-Repository Task Mode
- **Boundary adjustments**: Should be folded into Cross-Repository Task Mode capability or be a supporting section

### Capability: Template Rendering
- **Source clusters**: template_*
- **Contributing chunks**: template_unified_module (ACTIVE), template_system_consolidation (ACTIVE), template_drift_prevention (ACTIVE), migrate_chunks_template (ACTIVE), jinja_backrefs (ACTIVE), restore_template_content (ACTIVE)
- **Business intent**: Provide unified Jinja2 template rendering for all artifact creation with consistent context injection, includes support, and drift prevention.
- **Beneficiaries**: All artifact creation operations (chunks, narratives, investigations, subsystems, project init)
- **Validation**: src/template_system.py is the canonical implementation; already has STABLE subsystem
- **Boundary assessment**: **STRONG** - Exists as documented subsystem
- **Boundary adjustments**: None - aligns with existing template_system subsystem

### Capability: Chunk Cluster Analysis
- **Source clusters**: cluster_*
- **Contributing chunks**: cluster_list_command (ACTIVE), cluster_rename (ACTIVE), cluster_prefix_suggest (ACTIVE), cluster_seed_naming (ACTIVE), cluster_naming_guidance (ACTIVE), cluster_subsystem_prompt (ACTIVE)
- **Business intent**: Help users understand and manage chunk naming patterns, suggesting prefixes for cohesion and warning when clusters become too large.
- **Beneficiaries**: Operators maintaining chunk organization, agents creating chunks
- **Validation**: src/cluster_analysis.py, src/cluster_rename.py dedicated to this capability
- **Boundary assessment**: **STRONG** - Self-contained analysis tooling
- **Boundary adjustments**: None needed

### Capability: Friction Log Management
- **Source clusters**: friction_*
- **Contributing chunks**: friction_template_and_cli (ACTIVE), friction_chunk_workflow (ACTIVE), friction_chunk_linking (ACTIVE), friction_claude_docs (ACTIVE), friction_noninteractive (ACTIVE), selective_artifact_friction (ACTIVE)
- **Business intent**: Capture and track pain points encountered during project use, enabling pattern recognition and improvement prioritization.
- **Beneficiaries**: Operators, project maintainers tracking recurring issues
- **Validation**: src/friction.py dedicated to this capability
- **Boundary assessment**: **STRONG** - Clear artifact type with distinct lifecycle
- **Boundary adjustments**: Could be considered a workflow artifact type, but has unique characteristics (ledger vs. lifecycle)

### Capability: Project Initialization
- **Source clusters**: project_init_command, init_creates_chunks_dir
- **Contributing chunks**: project_init_command (ACTIVE), init_creates_chunks_dir (ACTIVE), accept_full_artifact_paths (ACTIVE - partial)
- **Business intent**: Set up a new vibe-engineering project with correct directory structure, templates, and configuration.
- **Beneficiaries**: New project creators
- **Validation**: src/project.py contains Project class with init methods
- **Boundary assessment**: **NEEDS_MERGE** - This is project-level infrastructure, not a standalone capability
- **Boundary adjustments**: Could be infrastructure or part of template_system usage

### Capability: Code Backreference Management
- **Source clusters**: symbolic_code_refs, code_to_docs_backrefs, coderef_format_prompting
- **Contributing chunks**: symbolic_code_refs (ACTIVE), code_to_docs_backrefs (ACTIVE), coderef_format_prompting (HISTORICAL), jinja_backrefs (ACTIVE), narrative_backreference_support (ACTIVE)
- **Business intent**: Enable bidirectional traceability between source code and documentation via `# Chunk:`, `# Narrative:`, and `# Subsystem:` comments.
- **Beneficiaries**: Developers navigating code, agents understanding code provenance
- **Validation**: src/symbols.py for parsing, src/chunks.py for census and update
- **Boundary assessment**: **NEEDS_SPLIT** - Part belongs to workflow_artifacts (backreference format), part to code analysis infrastructure
- **Boundary adjustments**: Backreference format/semantics → workflow_artifacts; Symbol parsing → infrastructure

---

## Existing Subsystem Reconciliation

| Existing Subsystem | Status | Chunk Agreement | Notes |
|--------------------|--------|-----------------|-------|
| template_system | STABLE | **AGREEMENT** | Chunks template_unified_module, template_system_consolidation, template_drift_prevention confirm scope. 9 chunks reference this subsystem. |
| workflow_artifacts | STABLE | **AGREEMENT** | Comprehensive subsystem with 36 chunk relationships. Chunk analysis confirms artifact lifecycle as core capability. |

### Agreement Details

**template_system**:
- Existing subsystem documents: unified render_template, render_to_directory, template enumeration
- Chunk-derived scope: Same + jinja_backrefs, restore_template_content
- Assessment: Strong alignment. No changes needed.

**workflow_artifacts**:
- Existing subsystem documents: Chunk/Narrative/Investigation/Subsystem lifecycle, frontmatter schemas, status transitions, manager class pattern, external reference support, causal ordering
- Chunk-derived scope: Same capabilities identified from chunk analysis
- Assessment: Strong alignment. Existing subsystem already comprehensive.

---

## Code-Discovered Capabilities

### Capability: CLI Framework
- **Code locations**: src/ve.py (main entry point, Click commands)
- **Business intent**: Provide a consistent command-line interface for all vibe-engineering operations
- **Why no chunks**: This is pure infrastructure - no specific "CLI framework" chunk because every feature chunk adds CLI commands

### Capability: Git Utilities
- **Code locations**: src/git_utils.py, src/repo_cache.py
- **Business intent**: Git operations for SHA resolution, remote fetching, repo caching
- **Why no chunks**: Infrastructure supporting sync and external resolve features

### Capability: Validation Utilities
- **Code locations**: src/validation.py
- **Business intent**: Shared validation functions (identifier format, etc.)
- **Why no chunks**: Generic infrastructure, no specific feature

---

## Capability Relationships

```
                      ┌─────────────────────────────────────────┐
                      │         TEMPLATE_SYSTEM (STABLE)        │
                      │   Jinja2 rendering for all artifacts    │
                      └────────────────┬────────────────────────┘
                                       │ uses
                                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     WORKFLOW_ARTIFACTS (STABLE)                          │
│   Chunk/Narrative/Investigation/Subsystem lifecycle management           │
│   + Causal ordering (created_after DAG, ArtifactIndex)                   │
│   + Frontmatter schemas (Pydantic models in models.py)                   │
│   + Status transitions (VALID_*_TRANSITIONS)                             │
│   + Code backreference format                                            │
└───────────────────────┬──────────────────────────────────────────────────┘
                        │ extends
                        ▼
    ┌─────────────────────────────────────────────────────────────┐
    │           CROSS_REPO_OPERATIONS (NEW)                       │
    │   Task directory mode, external references, sync            │
    │   Enables multi-repo workflows using workflow_artifacts     │
    └─────────────────────────────────────────────────────────────┘

                                       ▲ uses
                                       │
┌──────────────────────────────────────────────────────────────────────────┐
│                       ORCHESTRATOR (NEW)                                 │
│   Parallel agent management with scheduling, conflicts, attention        │
│   Uses workflow_artifacts (chunks as work units)                         │
└──────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────┐
    │           CLUSTER_ANALYSIS (NEW)                            │
    │   Chunk naming patterns, prefix suggestions, rename ops     │
    │   Operates on workflow_artifacts                            │
    └─────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────┐
    │           FRICTION_LOG (NEW)                                │
    │   Pain point tracking and pattern analysis                  │
    │   Special artifact type (ledger, not lifecycle)             │
    └─────────────────────────────────────────────────────────────┘
```

---

## Proposed Subsystem Structure

| Proposed Subsystem | Source Capabilities | Chunk Count | Status | Confidence |
|--------------------|---------------------|-------------|--------|------------|
| template_system | Template Rendering | 6 | EXISTS (STABLE) | HIGH |
| workflow_artifacts | Workflow Artifact Lifecycle + Causal Ordering + Code Backreference Format | 24 | EXISTS (STABLE) | HIGH |
| orchestrator | Parallel Agent Orchestration | 21 | NEW | HIGH |
| cross_repo_operations | Cross-Repository Task Mode + External Artifact References | 19 | NEW | HIGH |
| cluster_analysis | Chunk Cluster Analysis | 6 | NEW | MEDIUM |
| friction_log | Friction Log Management | 6 | NEW | MEDIUM |

### Subsystems NOT Proposed (Absorbed or Infrastructure)

| Capability | Disposition | Rationale |
|------------|-------------|-----------|
| Causal Artifact Ordering | Absorbed into workflow_artifacts | Supporting capability, not standalone domain |
| External Artifact References | Absorbed into cross_repo_operations | Mechanism for task mode, not standalone |
| Project Initialization | Infrastructure | Uses template_system, no domain-specific invariants |
| Code Backreference Management | Split | Format → workflow_artifacts; Parsing → infrastructure |
| CLI Framework | Infrastructure | No domain logic, just command dispatching |
| Git Utilities | Infrastructure | Generic git operations |
| Validation Utilities | Infrastructure | Generic validation |
