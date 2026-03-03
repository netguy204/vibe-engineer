"""Utility functions for cross-repository task management.

# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/task_operations_decompose - Task utilities package decomposition

This module is a thin re-export layer for backward compatibility.
All functionality has been moved to the `task` package with cohesive modules.
Use `from task import X` for new code.

Module structure:
- task.config: Configuration loading and project resolution
- task.artifact_ops: Generic CRUD operations for task artifacts
- task.promote: Artifact promotion to external repository
- task.external: External artifact copy/remove operations
- task.friction: Friction entry operations
- task.overlap: Overlap detection across repos
- task.exceptions: Exception hierarchy with TaskError base class
"""
# Chunk: docs/chunks/copy_as_external - Artifact copy-external command implementation
# Chunk: docs/chunks/external_artifact_unpin - External artifact unpinning
# Chunk: docs/chunks/external_chunk_causal - External chunk causal ordering
# Chunk: docs/chunks/remove_external_ref - Artifact remove-external command implementation
# Chunk: docs/chunks/ordering_remove_seqno - Short name format for task chunk creation

# Re-export external_refs utilities for backward compatibility
# (The original task_utils.py imported these at module level, making them re-exportable)
from external_refs import (
    is_external_artifact,
    load_external_ref,
    create_external_yaml,
    normalize_artifact_path,
    ARTIFACT_MAIN_FILE,
    ARTIFACT_DIR_NAME,
)

# Re-export everything from the task package for backward compatibility
from task import (
    # Exceptions
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
    # Config
    is_task_directory,
    load_task_config,
    resolve_repo_directory,
    parse_projects_option,
    resolve_project_ref,
    resolve_project_qualified_ref,
    find_task_directory,
    TaskProjectContext,
    check_task_project_context,
    # Artifact operations
    add_dependents_to_artifact,
    append_dependent_to_artifact,
    add_dependents_to_chunk,
    add_dependents_to_narrative,
    add_dependents_to_investigation,
    add_dependents_to_subsystem,
    create_task_chunk,
    create_task_narrative,
    create_task_investigation,
    create_task_subsystem,
    list_task_chunks,
    list_task_narratives,
    list_task_investigations,
    list_task_subsystems,
    list_task_artifacts_grouped,
    list_task_proposed_chunks,
    get_current_task_chunk,
    get_next_chunk_id,
    is_external_chunk,
    activate_task_chunk,
    # Promotion
    identify_source_project,
    promote_artifact,
    # External
    copy_artifact_as_external,
    remove_artifact_from_external,
    remove_dependent_from_artifact,
    # Friction
    create_task_friction_entry,
    add_external_friction_source,
    # Overlap
    TaskOverlapResult,
    find_task_overlapping_chunks,
)


__all__ = [
    # External refs (backward compatibility re-exports)
    "is_external_artifact",
    "load_external_ref",
    "create_external_yaml",
    "normalize_artifact_path",
    "ARTIFACT_MAIN_FILE",
    "ARTIFACT_DIR_NAME",
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
    # Friction
    "create_task_friction_entry",
    "add_external_friction_source",
    # Overlap
    "TaskOverlapResult",
    "find_task_overlapping_chunks",
]
