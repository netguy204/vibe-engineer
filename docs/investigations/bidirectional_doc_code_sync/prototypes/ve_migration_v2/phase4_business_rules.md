# Phase 4: Business Rule Extraction

## Business Rules by Capability

### Workflow Artifacts

#### State Rules

| Rule | Source | Enforcement Location |
|------|--------|---------------------|
| Chunk status must follow valid transitions (FUTURE->IMPLEMENTING->ACTIVE->SUPERSEDED->HISTORICAL) | valid_transitions success criteria | `src/models.py#VALID_CHUNK_TRANSITIONS`, `src/chunks.py#update_status` |
| Narrative status must follow valid transitions (DRAFTING->ACTIVE->COMPLETED) | valid_transitions success criteria | `src/models.py#VALID_NARRATIVE_TRANSITIONS`, `src/narratives.py#update_status` |
| Investigation status must follow valid transitions (ONGOING->SOLVED\|NOTED\|DEFERRED) | valid_transitions success criteria | `src/models.py#VALID_INVESTIGATION_TRANSITIONS`, `src/investigations.py#update_status` |
| Subsystem status must follow valid transitions | subsystem_status_transitions success criteria | `src/models.py#VALID_STATUS_TRANSITIONS`, `src/subsystems.py#update_status` |
| Only one IMPLEMENTING chunk allowed per repository at a time | chunk_create_guard success criteria | `src/chunks.py#create_chunk` (guard check) |
| HISTORICAL is a terminal state for all artifact types | valid_transitions success criteria | `VALID_*_TRANSITIONS` dicts (empty sets for terminal states) |

#### Validation Rules

| Rule | Source | Enforcement Location |
|------|--------|---------------------|
| Chunk short_name must be a valid identifier (lowercase, underscore-separated) | implement_chunk_start success criteria | `src/validation.py#validate_identifier` |
| Frontmatter must have required status field | chunk_frontmatter_model, subsystem_schemas_and_model | Pydantic model validation in `src/models.py` |
| Code references must use symbolic format (not line numbers) | symbolic_code_refs success criteria | `src/models.py#SymbolicReference` validator |
| Symbolic reference format: `{file_path}#{symbol_path}` with `::` nesting | symbolic_code_refs success criteria | `src/models.py#SymbolicReference#validate_ref` |
| Project-qualified refs must use `org/repo::path#symbol` format | task_qualified_refs success criteria | `src/models.py#SymbolicReference#validate_ref` |
| Artifact ID pattern: `{short_name}` (new) or `{NNNN}-{short_name}` (legacy) | ordering_remove_seqno success criteria | `src/models.py#ARTIFACT_ID_PATTERN` |
| Short name collision detection within artifact type | ordering_remove_seqno success criteria | `src/chunks.py#check_collision`, `src/narratives.py#check_collision` |

#### Causal Ordering Rules

| Rule | Source | Enforcement Location |
|------|--------|---------------------|
| Every artifact must have created_after field | ordering_field success criteria | Pydantic models (required field) |
| created_after references artifacts by short_name | ordering_remove_seqno success criteria | `src/artifact_ordering.py#ArtifactIndex` |
| created_after is immutable after creation | ordering_field success criteria (implicit) | No mutation code exists |
| Tips are artifacts with no dependents (nothing references them in created_after) | artifact_ordering_index success criteria | `src/artifact_ordering.py#ArtifactIndex::find_tips` |
| FUTURE chunks are excluded from tip calculation | ordering_active_only success criteria | `src/artifact_ordering.py#_TIP_ELIGIBLE_STATUSES` |
| DRAFTING narratives are excluded from tip calculation | ordering_active_only success criteria | `src/artifact_ordering.py#_TIP_ELIGIBLE_STATUSES` |
| Topological order computed via Kahn's algorithm | artifact_ordering_index success criteria | `src/artifact_ordering.py#ArtifactIndex::get_ordered` |

#### Cross-Reference Rules

| Rule | Source | Enforcement Location |
|------|--------|---------------------|
| Subsystem relationships must be bidirectional (chunk->subsystem if subsystem->chunk) | bidirectional_refs success criteria | `src/subsystems.py#validate_chunk_references`, `src/chunks.py#validate_subsystem_references` |
| Chunk referencing subsystem must exist in subsystem's chunks list | bidirectional_refs success criteria | `src/chunks.py#validate_subsystem_references` |
| Investigation reference in chunk must point to valid investigation | investigation_chunk_refs success criteria | `src/chunks.py#validate_investigation_reference` |
| Narrative reference in chunk must point to valid narrative | narrative_backreference_support success criteria | `src/chunks.py#validate_narrative_reference` |
| Friction entry references must match F{digits} pattern | friction_chunk_linking success criteria | `src/models.py#FRICTION_ENTRY_ID_PATTERN` |

---

### Orchestrator

#### State Rules

| Rule | Source | Enforcement Location |
|------|--------|---------------------|
| Work unit must be in READY state to be assigned | orch_scheduling success criteria | `src/orchestrator/scheduler.py` |
| Only one active work unit per agent | orch_foundation success criteria | `src/orchestrator/scheduler.py` |
| NEEDS_ATTENTION requires attention_reason | orch_attention_reason success criteria | `src/orchestrator/state.py#update_work_unit_status` |
| BLOCKED work units track blocked_by relationship | orch_blocked_lifecycle success criteria | `src/orchestrator/state.py` |

#### Concurrency Rules

| Rule | Source | Enforcement Location |
|------|--------|---------------------|
| Conflict detection runs before agent assignment | orch_conflict_oracle success criteria | `src/orchestrator/scheduler.py` |
| Conflicting chunks cannot run simultaneously without INDEPENDENT verdict | orch_conflict_oracle success criteria | `src/orchestrator/scheduler.py#_get_ready_with_conflicts` |
| Work units with pending conflicts enter NEEDS_ATTENTION | orch_conflict_oracle success criteria | `src/orchestrator/scheduler.py` |
| Inject activates FUTURE chunk if one exists | orch_activate_on_inject success criteria | `src/orchestrator/api.py#inject_chunk` |
| Displaced chunk is tracked in work unit metadata | orch_activate_on_inject success criteria | `src/orchestrator/state.py#displaced_chunk` |

#### Validation Rules

| Rule | Source | Enforcement Location |
|------|--------|---------------------|
| Chunk must be committed before injection | orch_inject_validate success criteria | `src/orchestrator/api.py#inject_chunk` |
| Chunk must have PLAN.md content for injection | orch_inject_validate success criteria | `src/chunks.py#_check_plan_exists` |
| Agent must operate within sandbox boundaries | orch_sandbox_enforcement success criteria | `src/orchestrator/agent.py` |

---

### Cross-Repo Operations

#### Configuration Rules

| Rule | Source | Enforcement Location |
|------|--------|---------------------|
| external_artifact_repo must be in org/repo format | cross_repo_schemas success criteria | `src/models.py#TaskConfig#validate_external_artifact_repo` |
| projects list must be non-empty | cross_repo_schemas success criteria | `src/models.py#TaskConfig#validate_projects` |
| Each project must be in org/repo format | cross_repo_schemas success criteria | `src/models.py#TaskConfig#validate_projects` |

#### External Reference Rules

| Rule | Source | Enforcement Location |
|------|--------|---------------------|
| external.yaml must specify artifact_type and artifact_id | consolidate_ext_refs success criteria | `src/models.py#ExternalArtifactRef` |
| pinned SHA must be 40-character hex | consolidate_ext_refs success criteria | `src/models.py#ExternalArtifactRef#validate_pinned` |
| External chunks participate in local causal ordering | external_chunk_causal success criteria | `src/artifact_ordering.py#_enumerate_artifacts` |
| External chunks use EXTERNAL pseudo-status for tip eligibility | external_chunk_causal success criteria | `src/artifact_ordering.py#_TIP_ELIGIBLE_STATUSES` |

#### Task-Aware Command Rules

| Rule | Source | Enforcement Location |
|------|--------|---------------------|
| All task-aware create commands must support --projects flag | selective_project_linking success criteria | CLI commands in `src/ve.py` |
| When --projects omitted, all projects in task config are linked | selective_project_linking success criteria | `src/task_utils.py#parse_project_filter` |
| Task directory detected by presence of .ve-task.yaml | chunk_create_task_aware success criteria | `src/task_utils.py#is_task_directory` |

---

### Template System

#### Rendering Rules

| Rule | Source | Enforcement Location |
|------|--------|---------------------|
| All templates must be rendered through template_system | template_unified_module success criteria | `src/template_system.py#render_template` |
| Template files must use .jinja2 suffix | template_unified_module success criteria | File naming convention |
| Suffix is stripped when writing output | template_system_consolidation success criteria | `src/template_system.py#render_to_directory` |
| Include paths resolve relative to template collection | template_unified_module success criteria | `src/template_system.py#get_environment` |

---

### Friction Log

#### Entry Rules

| Rule | Source | Enforcement Location |
|------|--------|---------------------|
| Entry ID format must be F followed by digits | friction_template_and_cli success criteria | `src/models.py#FRICTION_ENTRY_ID_PATTERN` |
| Entry IDs must be sequential within friction log | friction_template_and_cli success criteria | `src/friction.py#get_next_entry_id` |
| Each entry must have date, theme_id, and title | friction_template_and_cli success criteria | Entry parsing in `src/friction.py` |

#### Lifecycle Rules (Derived)

| Rule | Source | Enforcement Location |
|------|--------|---------------------|
| Entry status is derived, not stored | friction_chunk_workflow success criteria | No status field in entries |
| OPEN = entry_id not in any proposed_chunks.addresses | friction_chunk_workflow success criteria | Derived at query time |
| ADDRESSED = entry_id in proposed_chunks.addresses | friction_chunk_workflow success criteria | Derived at query time |
| RESOLVED = ADDRESSED + chunk reached ACTIVE | friction_chunk_workflow success criteria | Derived at query time |

---

## Rule Conflicts

| Rule A | Rule B | Status | Resolution |
|--------|--------|--------|------------|
| "Line numbers are acceptable" (coderef_format_prompting, HISTORICAL) | "Only symbolic references allowed" (symbolic_code_refs, ACTIVE) | **RESOLVED** | symbolic_code_refs wins (coderef_format_prompting is HISTORICAL) |
| No other conflicts detected | - | - | - |

---

## Rules in Code Not in Chunks

| Rule | Code Location | Suggested Documentation |
|------|---------------|------------------------|
| Identifier max length 31 chars (project names) | `src/models.py#_require_valid_dir_name` | Add to workflow_artifacts invariants |
| GitHub org max length 39 chars | `src/models.py#_require_valid_repo_ref` | Add to cross_repo_operations invariants |
| GitHub repo max length 100 chars | `src/models.py#_require_valid_repo_ref` | Add to cross_repo_operations invariants |
| Daemon TCP port default 8765 | `src/orchestrator/daemon.py` | Add to orchestrator invariants |
| Cache directory ~/.ve-cache/repos/ | `src/repo_cache.py` | Infrastructure documentation |
| Artifact ordering cache .artifact-order.json | `src/artifact_ordering.py` | Add to workflow_artifacts invariants |

---

## Invariant Summary by Proposed Subsystem

### workflow_artifacts (existing, STABLE)
1. Every artifact must have `status` and `created_after` fields
2. Status values defined as StrEnum in models.py
3. Valid transitions defined in `VALID_*_TRANSITIONS` dicts
4. Only one IMPLEMENTING chunk per repository
5. Causal ordering via `created_after` DAG, computed by ArtifactIndex
6. FUTURE/DRAFTING artifacts excluded from tip calculation
7. Code references must be symbolic (not line numbers)
8. Bidirectional references between chunks and subsystems enforced
9. Short names must be unique within artifact type

### orchestrator (new)
1. Work units progress through defined state machine
2. Conflicts must be resolved before parallel execution
3. Agents operate within sandbox boundaries
4. Chunks must be committed and have PLAN.md before injection
5. NEEDS_ATTENTION state requires attention_reason

### cross_repo_operations (new)
1. Task directory identified by .ve-task.yaml
2. Repository references use org/repo format
3. External references track artifact_type and artifact_id
4. External artifacts participate in local causal ordering
5. All task-aware commands support --projects flag

### template_system (existing, STABLE)
1. All templates rendered through unified system
2. .jinja2 suffix required, stripped on output
3. Includes resolve relative to template collection

### friction_log (new)
1. Entry IDs are F{digits} format, sequential
2. Status is derived (OPEN/ADDRESSED/RESOLVED), not stored
3. Themes emerge organically from entries

### cluster_analysis (new)
1. Clusters identified by naming prefix
2. Large clusters (>threshold) trigger subsystem prompts
3. Prefix suggestions use TF-IDF similarity
