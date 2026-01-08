"""Utility functions for cross-repository task management."""

from pathlib import Path

import yaml

from models import TaskConfig, ExternalChunkRef


def is_task_directory(path: Path) -> bool:
    """Detect if path contains a .ve-task.yaml file."""
    return (path / ".ve-task.yaml").exists()


def is_external_chunk(chunk_path: Path) -> bool:
    """Detect if chunk_path is an external chunk reference.

    An external chunk has external.yaml but no GOAL.md.
    """
    has_external = (chunk_path / "external.yaml").exists()
    has_goal = (chunk_path / "GOAL.md").exists()
    return has_external and not has_goal


def load_task_config(path: Path) -> TaskConfig:
    """Load and validate .ve-task.yaml from path.

    Args:
        path: Directory containing .ve-task.yaml

    Returns:
        Validated TaskConfig

    Raises:
        FileNotFoundError: If .ve-task.yaml doesn't exist
        ValidationError: If YAML content is invalid
    """
    config_file = path / ".ve-task.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f".ve-task.yaml not found in {path}")

    with open(config_file) as f:
        data = yaml.safe_load(f)

    return TaskConfig.model_validate(data)


def load_external_ref(chunk_path: Path) -> ExternalChunkRef:
    """Load and validate external.yaml from chunk path.

    Args:
        chunk_path: Directory containing external.yaml

    Returns:
        Validated ExternalChunkRef

    Raises:
        FileNotFoundError: If external.yaml doesn't exist
        ValidationError: If YAML content is invalid
    """
    ref_file = chunk_path / "external.yaml"
    if not ref_file.exists():
        raise FileNotFoundError(f"external.yaml not found in {chunk_path}")

    with open(ref_file) as f:
        data = yaml.safe_load(f)

    return ExternalChunkRef.model_validate(data)
