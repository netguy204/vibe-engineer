---
status: DOCUMENTED
# MIGRATION NOTE: This subsystem was synthesized from chunks.
# Review all [NEEDS_HUMAN] and [CONFLICT] sections before finalizing.
# Confidence: 70% synthesized, 20% inferred, 10% needs human input
chunks:
  - name: task_init
    relationship: implements
  - name: task_init_scaffolding
    relationship: implements
  - name: task_config_local_paths
    relationship: implements
  - name: task_status_command
    relationship: implements
  - name: task_list_proposed
    relationship: implements
  - name: task_qualified_refs
    relationship: implements
  - name: task_chunk_validation
    relationship: implements
  - name: chunk_create_task_aware
    relationship: implements
  - name: list_task_aware
    relationship: implements
  - name: task_aware_narrative_cmds
    relationship: implements
  - name: task_aware_investigations
    relationship: implements
  - name: task_aware_subsystem_cmds
    relationship: implements
  - name: selective_project_linking
    relationship: implements
  - name: taskdir_context_cmds
    relationship: implements
  - name: external_resolve
    relationship: implements
  - name: external_resolve_all_types
    relationship: implements
  - name: external_chunk_causal
    relationship: implements
  - name: consolidate_ext_refs
    relationship: implements
  - name: consolidate_ext_ref_utils
    relationship: implements
  - name: copy_as_external
    relationship: implements
  - name: artifact_copy_backref
    relationship: implements
  - name: remove_external_ref
    relationship: implements
  - name: sync_all_workflows
    relationship: implements
  - name: ve_sync_command
    relationship: implements
  - name: cross_repo_schemas
    relationship: implements
code_references:
  - ref: src/task_utils.py
    implements: Core task directory utilities and cross-repo operations
    compliance: COMPLIANT
  - ref: src/task_init.py#TaskInit
    implements: Task directory initialization
    compliance: COMPLIANT
  - ref: src/external_refs.py
    implements: External artifact reference utilities
    compliance: COMPLIANT
  - ref: src/external_resolve.py
    implements: External artifact resolution across repos
    compliance: COMPLIANT
  - ref: src/sync.py
    implements: External reference synchronization
    compliance: COMPLIANT
  - ref: src/models.py#TaskConfig
    implements: Task directory configuration schema
    compliance: COMPLIANT
  - ref: src/models.py#ExternalArtifactRef
    implements: External artifact reference schema
    compliance: COMPLIANT
proposed_chunks: []
created_after:
  - workflow_artifacts
  - template_system
---

# cross_repo_operations

## Intent

<!-- SYNTHESIS CONFIDENCE: HIGH -->

[SYNTHESIZED] Enable work that spans multiple repositories via a task directory pattern, where a shared external repo holds artifacts and multiple project repos link to them.

From chunk_create_task_aware chunk: "When in a task directory context (detected by .ve-task.yaml), create the chunk in the external artifact repository and add external.yaml references in each project repository."

From task_init chunk: "Initialize a task directory structure that coordinates work across multiple repositories, with a central external artifact repo and multiple project repos."

[NEEDS_HUMAN] Business context and strategic importance:
<!-- Why does this subsystem matter to the organization? -->
<!-- Consider: Platform teams, multi-service changes, cross-cutting concerns -->

## Scope

### In Scope

<!-- SYNTHESIS CONFIDENCE: HIGH -->

[SYNTHESIZED] Based on chunk code_references and success criteria:
- **Task directory initialization**: `.ve-task.yaml` configuration, CLAUDE.md scaffolding
- **External artifact references**: `external.yaml` files linking to artifacts in external repo
- **Task-aware artifact creation**: Creating chunks/narratives/investigations/subsystems in external repo with project links
- **Task-aware listing**: Listing artifacts across all repos in task context
- **External resolution**: Resolving external references to actual content
- **Sync command**: Updating pinned SHAs in external.yaml files
- **Project-qualified references**: `org/repo::path#symbol` format for cross-repo code refs
- **Selective project linking**: `--projects` flag for controlling which projects get external.yaml

[INFERRED] From code structure:
- **Causal ordering for external refs**: External artifacts participate in local `created_after` DAG
- **Repo cache**: `~/.ve-cache/repos/` for fetching external repos in single-repo mode

### Out of Scope

<!-- SYNTHESIS CONFIDENCE: MEDIUM -->

[NEEDS_HUMAN] What explicitly does NOT belong here:
- [INFERRED] Artifact lifecycle management (belongs to workflow_artifacts)
- [INFERRED] Template rendering (belongs to template_system)
- [INFERRED] Agent orchestration (belongs to orchestrator)

## Invariants

<!-- SYNTHESIS CONFIDENCE: HIGH -->

[SYNTHESIZED] From chunk success criteria:

1. **Task directory identified by .ve-task.yaml presence**
   - `is_task_directory()` checks for this file to determine context
   - Source: chunk_create_task_aware

2. **Repository references use org/repo format**
   - Both `external_artifact_repo` and `projects` list use GitHub's org/repo format
   - Validated by `_require_valid_repo_ref()` in models.py
   - Source: cross_repo_schemas

3. **External references track artifact_type and artifact_id**
   - `ExternalArtifactRef` model has `artifact_type` (CHUNK/NARRATIVE/etc.) and `artifact_id` fields
   - Source: consolidate_ext_refs

4. **External artifacts participate in local causal ordering**
   - `external.yaml` files have `created_after` field for local DAG ordering
   - External artifacts use "EXTERNAL" pseudo-status for tip eligibility
   - Source: external_chunk_causal

5. **All task-aware create commands support --projects flag**
   - When omitted, all projects in task config are linked
   - When provided, only specified projects get external.yaml
   - Commands: `ve chunk create`, `ve narrative create`, `ve investigation create`, `ve subsystem discover`, `ve friction log`
   - Source: selective_project_linking

6. **Project-qualified refs use org/repo::path#symbol format**
   - Double-colon separates project qualifier from file path
   - Enables cross-repo symbol validation
   - Source: task_qualified_refs

7. **Pinned SHA must be 40-character hex**
   - External references can pin to specific commit
   - Validated by regex in ExternalArtifactRef
   - Source: consolidate_ext_refs

[NEEDS_HUMAN] Implicit invariants not in chunks:
<!-- What rules exist in code but weren't documented? -->
- Projects list must be non-empty in TaskConfig
- GitHub org max length 39 chars, repo max 100 chars

## Code References

<!-- SYNTHESIS CONFIDENCE: HIGH -->

[SYNTHESIZED] Consolidated from chunk code_references:

### Task Configuration
- `src/models.py#TaskConfig` - Task directory configuration schema
- `src/models.py#ExternalArtifactRef` - External artifact reference schema
- `src/task_utils.py#is_task_directory` - Context detection
- `src/task_utils.py#load_task_config` - Config loading

### Task Initialization
- `src/task_init.py#TaskInit` - Task directory initialization class
- `src/task_init.py#TaskInitResult` - Initialization result tracking

### External References
- `src/external_refs.py#is_external_artifact` - Detect external reference directories
- `src/external_refs.py#load_external_ref` - Load external.yaml content
- `src/external_refs.py#create_external_yaml` - Create external reference files
- `src/external_refs.py#normalize_artifact_path` - Flexible path normalization
- `src/external_refs.py#ARTIFACT_MAIN_FILE` - Artifact type to main file mapping
- `src/external_refs.py#ARTIFACT_DIR_NAME` - Artifact type to directory name mapping

### Resolution
- `src/external_resolve.py#find_artifact_in_project` - Find artifact in project repos
- `src/external_resolve.py#resolve_artifact_task_directory` - Task context resolution
- `src/external_resolve.py#resolve_artifact_single_repo` - Single repo resolution

### Sync
- `src/sync.py#find_external_refs` - Find all external.yaml files
- `src/sync.py#sync_task_directory` - Sync in task context
- `src/sync.py#sync_single_repo` - Sync in single repo context

### Task-Aware Operations
- `src/task_utils.py#create_task_chunk` - Cross-repo chunk creation
- `src/task_utils.py#create_task_narrative` - Cross-repo narrative creation
- `src/task_utils.py#create_task_investigation` - Cross-repo investigation creation
- `src/task_utils.py#create_task_subsystem` - Cross-repo subsystem creation
- `src/task_utils.py#list_task_chunks` - Cross-repo chunk listing
- `src/task_utils.py#copy_artifact_as_external` - Copy external artifact

[INFERRED] Additional references found in code but not in chunks:
- `src/repo_cache.py` - Repository caching for single-repo mode

[NEEDS_HUMAN] Validate these references are current:
<!-- Some chunk references may be stale -->

## Deviations

<!-- SYNTHESIS CONFIDENCE: LOW -->

[NEEDS_HUMAN] Known deviations from ideal:
- [INFERRED] `suggest_prefix` does not dereference external artifacts in single-repo mode (documented in workflow_artifacts)
- [INFERRED] Error handling could be more consistent across task operations

## Chunk Provenance

This subsystem was synthesized from the following chunks:

| Chunk | Status | Contribution | Confidence |
|-------|--------|--------------|------------|
| task_init | ACTIVE | Task initialization | HIGH |
| task_init_scaffolding | ACTIVE | CLAUDE.md and commands scaffolding | HIGH |
| task_config_local_paths | ACTIVE | Local path resolution | HIGH |
| task_status_command | ACTIVE | Status command | MEDIUM |
| task_list_proposed | ACTIVE | Proposed chunk listing | MEDIUM |
| task_qualified_refs | ACTIVE | Invariant 6, qualified refs | HIGH |
| task_chunk_validation | ACTIVE | Validation in task context | HIGH |
| chunk_create_task_aware | ACTIVE | Invariants 1, 3, core creation | HIGH |
| list_task_aware | ACTIVE | Task-aware listing | HIGH |
| task_aware_narrative_cmds | ACTIVE | Narrative commands | HIGH |
| task_aware_investigations | ACTIVE | Investigation commands | HIGH |
| task_aware_subsystem_cmds | ACTIVE | Subsystem commands | HIGH |
| selective_project_linking | ACTIVE | Invariant 5 | HIGH |
| taskdir_context_cmds | ACTIVE | Context commands | MEDIUM |
| external_resolve | ACTIVE | Resolution foundation | HIGH |
| external_resolve_all_types | ACTIVE | All artifact types | HIGH |
| external_chunk_causal | ACTIVE | Invariant 4 | HIGH |
| consolidate_ext_refs | ACTIVE | Invariants 3, 7 | HIGH |
| consolidate_ext_ref_utils | ACTIVE | Utility functions | HIGH |
| copy_as_external | ACTIVE | Copy operations | MEDIUM |
| artifact_copy_backref | ACTIVE | Backref updates | MEDIUM |
| remove_external_ref | ACTIVE | Remove operations | MEDIUM |
| sync_all_workflows | ACTIVE | Sync command | HIGH |
| ve_sync_command | ACTIVE | Sync foundation | HIGH |
| cross_repo_schemas | ACTIVE | Invariant 2 | HIGH |

## Synthesis Metrics

| Section | Synthesized | Inferred | Needs Human | Conflicts |
|---------|-------------|----------|-------------|-----------|
| Intent | 2 | 0 | 1 | 0 |
| Scope | 8 | 2 | 1 | 0 |
| Invariants | 7 | 0 | 1 | 0 |
| Code References | 20 | 1 | 1 | 0 |
| Deviations | 0 | 2 | 1 | 0 |
| **Total** | **37** | **5** | **5** | **0** |

**Overall Confidence**: 79% (37 synthesized / 47 total items)
