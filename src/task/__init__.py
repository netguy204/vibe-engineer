"""Task operations package.

# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/task_operations_decompose - Task utilities package decomposition

This package provides utilities for cross-repository task management,
organized into cohesive modules by responsibility:

- config: Task directory detection, configuration loading, project resolution
- artifact_ops: Generic CRUD operations for task artifacts
- promote: Artifact promotion to external repository
- external: External artifact copy/remove operations
- friction: Friction entry operations
- overlap: Overlap detection across repos
- exceptions: Exception hierarchy with TaskError base class

All public names are re-exported here for backward compatibility with
existing `from task_utils import X` patterns.
"""

# Exception classes
from task.exceptions import (
    TaskError,
    TaskChunkError,
    TaskNarrativeError,
    TaskInvestigationError,
    TaskSubsystemError,
    TaskPromoteError,
    TaskArtifactListError,
    TaskCopyExternalError,
    TaskRemoveExternalError,
    TaskFrictionError,
    TaskOverlapError,
    TaskActivateError,
    TaskDemoteError,
)

# Config functions
from task.config import (
    is_task_directory,
    load_task_config,
    resolve_repo_directory,
    parse_projects_option,
    resolve_project_ref,
    resolve_project_qualified_ref,
    find_task_directory,
    TaskProjectContext,
    check_task_project_context,
)

# Artifact operations
from task.artifact_ops import (
    # Generic operations
    add_dependents_to_artifact,
    append_dependent_to_artifact,
    # Type-specific wrappers (backward compatibility)
    add_dependents_to_chunk,
    add_dependents_to_narrative,
    add_dependents_to_investigation,
    add_dependents_to_subsystem,
    # Creation functions
    create_task_chunk,
    create_task_narrative,
    create_task_investigation,
    create_task_subsystem,
    # Listing functions
    list_task_chunks,
    list_task_narratives,
    list_task_investigations,
    list_task_subsystems,
    list_task_artifacts_grouped,
    list_task_proposed_chunks,
    # Utility functions
    get_current_task_chunk,
    get_next_chunk_id,
    is_external_chunk,
    activate_task_chunk,
)

# Promotion
from task.promote import (
    identify_source_project,
    promote_artifact,
)

# External operations
from task.external import (
    copy_artifact_as_external,
    remove_artifact_from_external,
    remove_dependent_from_artifact,
)

# Demotion
from task.demote import (
    demote_artifact,
    scan_demotable_artifacts,
    read_artifact_frontmatter,
)

# Friction operations
from task.friction import (
    create_task_friction_entry,
    add_external_friction_source,
)

# Overlap detection
from task.overlap import (
    TaskOverlapResult,
    find_task_overlapping_chunks,
)


__all__ = [
    # Exceptions
    "TaskError",
    "TaskChunkError",
    "TaskNarrativeError",
    "TaskInvestigationError",
    "TaskSubsystemError",
    "TaskPromoteError",
    "TaskArtifactListError",
    "TaskCopyExternalError",
    "TaskRemoveExternalError",
    "TaskFrictionError",
    "TaskOverlapError",
    "TaskActivateError",
    "TaskDemoteError",
    # Config
    "is_task_directory",
    "load_task_config",
    "resolve_repo_directory",
    "parse_projects_option",
    "resolve_project_ref",
    "resolve_project_qualified_ref",
    "find_task_directory",
    "TaskProjectContext",
    "check_task_project_context",
    # Artifact operations
    "add_dependents_to_artifact",
    "append_dependent_to_artifact",
    "add_dependents_to_chunk",
    "add_dependents_to_narrative",
    "add_dependents_to_investigation",
    "add_dependents_to_subsystem",
    "create_task_chunk",
    "create_task_narrative",
    "create_task_investigation",
    "create_task_subsystem",
    "list_task_chunks",
    "list_task_narratives",
    "list_task_investigations",
    "list_task_subsystems",
    "list_task_artifacts_grouped",
    "list_task_proposed_chunks",
    "get_current_task_chunk",
    "get_next_chunk_id",
    "is_external_chunk",
    "activate_task_chunk",
    # Promotion
    "identify_source_project",
    "promote_artifact",
    # External
    "copy_artifact_as_external",
    "remove_artifact_from_external",
    "remove_dependent_from_artifact",
    # Demotion
    "demote_artifact",
    "scan_demotable_artifacts",
    "read_artifact_frontmatter",
    # Friction
    "create_task_friction_entry",
    "add_external_friction_source",
    # Overlap
    "TaskOverlapResult",
    "find_task_overlapping_chunks",
]
