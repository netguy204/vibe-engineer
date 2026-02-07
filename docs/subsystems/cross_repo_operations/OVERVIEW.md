---
status: DOCUMENTED
chunks:
  - chunk_id: external_artifact_unpin
    relationship: implements
  - chunk_id: validate_external_chunks
    relationship: uses
  - chunk_id: taskdir_subsystem_overlap
    relationship: uses
  - chunk_id: task_operations_decompose
    relationship: implements
code_references:
- ref: src/task_init.py#TaskInit
  implements: Task directory initialization class
  compliance: COMPLIANT
- ref: src/task_init.py#TaskInitResult
  implements: Result dataclass for init operations
  compliance: COMPLIANT
- ref: src/task/artifact_ops.py#create_task_chunk
  implements: Task-aware chunk creation with external references
  compliance: COMPLIANT
- ref: src/task/artifact_ops.py#list_task_chunks
  implements: Task-aware chunk listing from external repo
  compliance: COMPLIANT
- ref: src/task/artifact_ops.py#create_task_narrative
  implements: Task-aware narrative creation
  compliance: COMPLIANT
- ref: src/task/artifact_ops.py#create_task_investigation
  implements: Task-aware investigation creation
  compliance: COMPLIANT
- ref: src/task/artifact_ops.py#create_task_subsystem
  implements: Task-aware subsystem creation
  compliance: COMPLIANT
- ref: src/task/config.py#resolve_project_qualified_ref
  implements: Parse and resolve project-qualified code references
  compliance: COMPLIANT
- ref: src/task/overlap.py#find_task_overlapping_chunks
  implements: Cross-project chunk overlap detection
  compliance: COMPLIANT
- ref: src/task/config.py#load_task_config
  implements: Task configuration loading and validation
  compliance: COMPLIANT
- ref: src/task/config.py#resolve_repo_directory
  implements: Resolve org/repo to filesystem path
  compliance: COMPLIANT
- ref: src/task/promote.py#promote_artifact
  implements: Promote local artifact to external repository
  compliance: COMPLIANT
- ref: src/task/external.py#copy_artifact_as_external
  implements: Copy artifact from external repo as external reference
  compliance: COMPLIANT
- ref: src/task/external.py#remove_artifact_from_external
  implements: Remove external artifact reference from project
  compliance: COMPLIANT
- ref: src/task/friction.py#create_task_friction_entry
  implements: Create friction entry in task context
  compliance: COMPLIANT
- ref: src/task/exceptions.py#TaskError
  implements: Base exception for all task operations
  compliance: COMPLIANT
- ref: src/external_refs.py#is_external_artifact
  implements: Generic external artifact detection
  compliance: COMPLIANT
- ref: src/external_refs.py#load_external_ref
  implements: External reference loading and validation
  compliance: COMPLIANT
- ref: src/external_refs.py#create_external_yaml
  implements: External reference file creation
  compliance: COMPLIANT
- ref: src/external_refs.py#detect_artifact_type_from_path
  implements: Infer artifact type from directory path
  compliance: COMPLIANT
- ref: src/external_resolve.py#find_artifact_in_project
  implements: Generic artifact finding for any type
  compliance: COMPLIANT
- ref: src/external_resolve.py#resolve_artifact_task_directory
  implements: Artifact resolution in task directory mode
  compliance: COMPLIANT
- ref: src/external_resolve.py#resolve_artifact_single_repo
  implements: Artifact resolution in single repo mode
  compliance: COMPLIANT
- ref: src/git_utils.py#is_git_repository
  implements: Git repository validation
  compliance: COMPLIANT
- ref: src/git_utils.py#get_current_sha
  implements: Get HEAD SHA of local repo
  compliance: COMPLIANT
- ref: src/repo_cache.py#RepoCache
  implements: Clone/fetch cache for external repos
  compliance: COMPLIANT
- ref: src/repo_cache.py#get_repo_path
  implements: Get filesystem path to cached repo working tree
  compliance: COMPLIANT
- ref: src/repo_cache.py#list_directory_at_ref
  implements: List directory contents at a specific git ref
  compliance: COMPLIANT
- ref: src/models.py#TaskConfig
  implements: .ve-task.yaml configuration model
  compliance: COMPLIANT
- ref: src/models.py#ExternalArtifactRef
  implements: Generic external reference model
  compliance: COMPLIANT
created_after:
- workflow_artifacts
---

# cross_repo_operations

## Intent

Enable engineering work that spans multiple git repositories by providing
task directories, external artifact references, and synchronization. Without this
subsystem, work spanning repos has no natural home and relies on ad-hoc coordination.

This subsystem formalizes cross-repo work:
- **Task directories** coordinate multiple repo worktrees with a central external repo
- **External references** let project repos point to artifacts in the external repo
- **Sync operations** maintain point-in-time snapshots for archaeology
- **Task-aware commands** detect context and operate across repos seamlessly

## Scope

### In Scope

- **Task directory initialization**: `ve task init` to set up cross-repo coordination
- **Task context detection**: Automatic detection of task vs single-repo mode
- **External artifact references**: `external.yaml` pattern for cross-repo artifacts
- **Bidirectional references**: Dependents list in artifacts, external.yaml in projects
- **Sync operations**: Update pinned SHAs to capture point-in-time state
- **External resolution**: View content, local path, and directory listing from external repos
- **Task-aware commands**: All artifact commands (create, list) in task context
- **Git utilities**: Local worktree operations (SHA, validation)
- **Repo cache**: Clone/fetch cache for external repos in single-repo mode
- **Project-qualified references**: `project:file#symbol` format

### Out of Scope

- **Artifact lifecycle management**: Defined in workflow_artifacts subsystem
- **Orchestrator operations**: Task directories don't require orchestrator
- **Template rendering**: Uses template_system but doesn't extend it

## Invariants

### Hard Invariants

1. **Task directory detected by presence of .ve-task.yaml** - Consistent context detection
   across all commands.

2. **External references always resolve to HEAD** - No point-in-time pinning;
   external content is always read from current HEAD of tracked branch (DEC-002).

3. **All specified directories must be VE-initialized git repos** - Validation during
   task init prevents configuration errors.

4. **Bidirectional references enable full graph traversal** - External artifacts list
   dependents, project repos point to external artifacts.

5. **External artifacts participate in local causal ordering** - `created_after` field
   in external.yaml enables proper ordering.

6. **External resolution works in both task and single-repo mode** - Dual context support
   for flexibility.

### Soft Conventions

1. **Task-aware commands support --projects flag** - Selective linking to specific projects.

2. **External repo uses standard VE structure** - Same docs/chunks/, docs/narratives/ layout.

## Implementation Locations

**Primary files**:
- `src/task_init.py` - Task directory initialization (TaskInit class)
- `src/task/` - Task operations package (decomposed from task_utils.py):
  - `task/config.py` - Configuration loading, project resolution, directory detection
  - `task/artifact_ops.py` - Generic CRUD operations for task artifacts
  - `task/promote.py` - Artifact promotion to external repository
  - `task/external.py` - External artifact copy/remove operations
  - `task/friction.py` - Friction entry operations
  - `task/overlap.py` - Overlap detection across repos
  - `task/exceptions.py` - Exception hierarchy with TaskError base class
- `src/task_utils.py` - Re-export shim for backward compatibility
- `src/external_refs.py` - External reference utilities (consolidated from multiple chunks)
- `src/external_resolve.py` - External artifact resolution
- `src/git_utils.py` - Git helper functions
- `src/repo_cache.py` - External repo clone/fetch cache

**Models**: `src/models.py#TaskConfig`, `src/models.py#ExternalArtifactRef`

CLI commands: `ve task init`, `ve external resolve`, plus task-aware versions
of all artifact commands.

## Known Deviations

### suggest_prefix Does Not Dereference External Artifacts (INHERITED)

This deviation is documented in workflow_artifacts subsystem. When operating in
single-repo mode, `suggest_prefix()` only considers local chunks. External artifact
references are silently skipped because the GOAL.md content isn't locally available.

**Impact**: Prefix suggestions don't consider semantically similar external chunks
in project context.

**Workaround**: Run from task directory for complete corpus coverage.

## Chunk Relationships

### Implements

28 chunks implement this subsystem. See frontmatter for complete list.

Key capability groups:
- **Task initialization**: task_init, task_init_scaffolding, task_config_local_paths
- **Task-aware commands**: chunk_create_task_aware, list_task_aware, task_aware_*
- **External references**: external_resolve, consolidate_ext_refs, external_chunk_causal
- **Git/sync**: git_local_utilities, ve_sync_command, sync_all_workflows

## Narrative Reference

This subsystem implements the vision from the `cross_repo_chunks` narrative, which
established the task directory pattern and external reference semantics.
