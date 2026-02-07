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


class TaskChunkError(TaskError):
    """Error during task chunk creation with user-friendly message."""

    pass


class TaskNarrativeError(TaskError):
    """Error during task narrative creation with user-friendly message."""

    pass


class TaskInvestigationError(TaskError):
    """Error during task investigation creation with user-friendly message."""

    pass


class TaskSubsystemError(TaskError):
    """Error during task subsystem creation with user-friendly message."""

    pass


class TaskPromoteError(TaskError):
    """Error during artifact promotion with user-friendly message."""

    pass


class TaskArtifactListError(TaskError):
    """Error during task artifact listing with user-friendly message."""

    pass


class TaskCopyExternalError(TaskError):
    """Error during artifact copy as external with user-friendly message."""

    pass


class TaskRemoveExternalError(TaskError):
    """Error during artifact removal from external with user-friendly message."""

    pass


class TaskFrictionError(TaskError):
    """Error during task friction logging with user-friendly message."""

    pass


class TaskOverlapError(TaskError):
    """Error during task overlap detection with user-friendly message."""

    pass


class TaskActivateError(TaskError):
    """Error during task chunk activation with user-friendly message."""

    pass
