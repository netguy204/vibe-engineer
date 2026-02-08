"""Exception classes for task operations.

# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/task_operations_decompose - Task utilities package decomposition

All task-related exceptions inherit from TaskError, enabling consistent
error handling across CLI commands.
"""


class TaskError(Exception):
    """Base exception for all task operations.

    All task-related exceptions inherit from this class to enable
    consistent error handling with a single except clause.
    """

    pass


# Chunk: docs/chunks/chunk_create_task_aware - Exception class for user-friendly error messages
class TaskChunkError(TaskError):
    """Error during task chunk creation with user-friendly message."""

    pass


class TaskNarrativeError(TaskError):
    """Error during task narrative creation with user-friendly message."""

    pass


# Chunk: docs/chunks/task_aware_investigations - Error class for task investigation operations
class TaskInvestigationError(TaskError):
    """Error during task investigation creation with user-friendly message."""

    pass


class TaskSubsystemError(TaskError):
    """Error during task subsystem creation with user-friendly message."""

    pass


# Chunk: docs/chunks/artifact_promote - Exception class for user-friendly promotion error messages
class TaskPromoteError(TaskError):
    """Error during artifact promotion with user-friendly message."""

    pass


class TaskArtifactListError(TaskError):
    """Error during task artifact listing with user-friendly message."""

    pass


class TaskCopyExternalError(TaskError):
    """Error during artifact copy as external with user-friendly message."""

    pass


# Chunk: docs/chunks/remove_external_ref - Error class for remove-external failures
class TaskRemoveExternalError(TaskError):
    """Error during artifact removal from external with user-friendly message."""

    pass


# Chunk: docs/chunks/selective_artifact_friction - Error class for task-aware friction operations
class TaskFrictionError(TaskError):
    """Error during task friction logging with user-friendly message."""

    pass


class TaskOverlapError(TaskError):
    """Error during task overlap detection with user-friendly message."""

    pass


class TaskActivateError(TaskError):
    """Error during task chunk activation with user-friendly message."""

    pass
