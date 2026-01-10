"""Utility functions for cross-repository task management."""
# Chunk: docs/chunks/0010-chunk_create_task_aware - Cross-repo task utilities
# Chunk: docs/chunks/0013-future_chunk_creation - Status support

import re
from pathlib import Path

import yaml

from chunks import Chunks
from git_utils import get_current_sha
from models import TaskConfig, ExternalChunkRef


# Chunk: docs/chunks/0010-chunk_create_task_aware - Detect task directory
def is_task_directory(path: Path) -> bool:
    """Detect if path contains a .ve-task.yaml file."""
    return (path / ".ve-task.yaml").exists()


# Chunk: docs/chunks/0010-chunk_create_task_aware - Resolve org/repo to path
def resolve_repo_directory(task_dir: Path, repo_ref: str) -> Path:
    """Resolve a GitHub-style org/repo reference to a filesystem path.

    Resolution order:
    1. Try {task_dir}/{repo}/ (just the repo name)
    2. Try {task_dir}/{org}/{repo}/ (nested for collision handling)

    Args:
        task_dir: The task directory containing repository worktrees
        repo_ref: GitHub-style org/repo reference (e.g., "acme/service-a")

    Returns:
        Path to the repository directory

    Raises:
        ValueError: If repo_ref is not in org/repo format
        FileNotFoundError: If neither resolution path exists
    """
    if "/" not in repo_ref:
        raise ValueError(f"repo_ref must be in 'org/repo' format, got: {repo_ref}")

    parts = repo_ref.split("/")
    if len(parts) != 2:
        raise ValueError(f"repo_ref must have exactly one slash, got: {repo_ref}")

    org, repo = parts

    # Try just the repo name first (common case)
    simple_path = task_dir / repo
    if simple_path.exists() and simple_path.is_dir():
        return simple_path

    # Try nested org/repo for collision handling
    nested_path = task_dir / org / repo
    if nested_path.exists() and nested_path.is_dir():
        return nested_path

    raise FileNotFoundError(
        f"Repository '{repo_ref}' not found. "
        f"Tried: {simple_path}, {nested_path}"
    )


# Chunk: docs/chunks/0010-chunk_create_task_aware - Detect external chunk
def is_external_chunk(chunk_path: Path) -> bool:
    """Detect if chunk_path is an external chunk reference.

    An external chunk has external.yaml but no GOAL.md.
    """
    has_external = (chunk_path / "external.yaml").exists()
    has_goal = (chunk_path / "GOAL.md").exists()
    return has_external and not has_goal


# Chunk: docs/chunks/0010-chunk_create_task_aware - Load task configuration
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


# Chunk: docs/chunks/0010-chunk_create_task_aware - Load external chunk reference
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


# Chunk: docs/chunks/0010-chunk_create_task_aware - Get next chunk ID
def get_next_chunk_id(project_path: Path) -> str:
    """Return next sequential chunk ID (e.g., '0005') for a project.

    Args:
        project_path: Path to the project directory

    Returns:
        4-digit zero-padded string for the next chunk ID
    """
    chunks = Chunks(project_path)
    chunk_list = chunks.list_chunks()

    if not chunk_list:
        return "0001"

    # list_chunks() returns (chunk_number, chunk_name) sorted descending
    highest_number = chunk_list[0][0]
    return f"{highest_number + 1:04d}"


# Chunk: docs/chunks/0010-chunk_create_task_aware - Create external.yaml
def create_external_yaml(
    project_path: Path,
    chunk_id: str,
    short_name: str,
    external_repo_ref: str,
    external_chunk_id: str,
    pinned_sha: str,
    track: str = "main",
) -> Path:
    """Create external.yaml in project's chunk directory.

    Args:
        project_path: Path to the project directory
        chunk_id: 4-digit chunk ID for this project (e.g., "0003")
        short_name: Short name for the chunk directory
        external_repo_ref: External chunk repo identifier (org/repo format)
        external_chunk_id: Chunk ID in the external repo (e.g., "0001-auth_token")
        pinned_sha: 40-character SHA to pin
        track: Branch to track (default "main")

    Returns:
        Path to the created external.yaml file
    """
    chunk_dir = project_path / "docs" / "chunks" / f"{chunk_id}-{short_name}"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    external_yaml_path = chunk_dir / "external.yaml"
    data = {
        "repo": external_repo_ref,
        "chunk": external_chunk_id,
        "track": track,
        "pinned": pinned_sha,
    }

    with open(external_yaml_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)

    return external_yaml_path


# Chunk: docs/chunks/0010-chunk_create_task_aware - Update frontmatter field
# Chunk: docs/chunks/0013-future_chunk_creation - Used for status updates
def update_frontmatter_field(
    goal_path: Path,
    field: str,
    value,
) -> None:
    """Update a single field in GOAL.md frontmatter.

    Args:
        goal_path: Path to the GOAL.md file
        field: The frontmatter field name to update
        value: The new value for the field

    Raises:
        FileNotFoundError: If goal_path doesn't exist
        ValueError: If the file has no frontmatter
    """
    if not goal_path.exists():
        raise FileNotFoundError(f"File not found: {goal_path}")

    content = goal_path.read_text()

    # Parse frontmatter between --- markers
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        raise ValueError(f"Could not parse frontmatter in {goal_path}")

    frontmatter_text = match.group(1)
    body = match.group(2)

    # Parse YAML frontmatter
    frontmatter = yaml.safe_load(frontmatter_text) or {}

    # Update the field
    frontmatter[field] = value

    # Reconstruct the file
    new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    new_content = f"---\n{new_frontmatter}---\n{body}"

    goal_path.write_text(new_content)


# Chunk: docs/chunks/0010-chunk_create_task_aware - Add dependents to chunk
def add_dependents_to_chunk(
    chunk_path: Path,
    dependents: list[dict],
) -> None:
    """Update chunk GOAL.md frontmatter to include dependents list.

    Args:
        chunk_path: Path to the chunk directory containing GOAL.md
        dependents: List of {repo, chunk} dicts to add as dependents

    Raises:
        FileNotFoundError: If GOAL.md doesn't exist in chunk_path
    """
    goal_path = chunk_path / "GOAL.md"
    if not goal_path.exists():
        raise FileNotFoundError(f"GOAL.md not found in {chunk_path}")

    update_frontmatter_field(goal_path, "dependents", dependents)


# Chunk: docs/chunks/0010-chunk_create_task_aware - Task chunk error class
class TaskChunkError(Exception):
    """Error during task chunk creation with user-friendly message."""

    pass


# Chunk: docs/chunks/0010-chunk_create_task_aware - Orchestrate multi-repo chunk
# Chunk: docs/chunks/0013-future_chunk_creation - Status parameter support
def create_task_chunk(
    task_dir: Path,
    short_name: str,
    ticket_id: str | None = None,
    status: str = "IMPLEMENTING",
) -> dict:
    """Create chunk in task directory context.

    Orchestrates multi-repo chunk creation:
    1. Creates chunk in external repo
    2. Creates external.yaml in each project
    3. Updates external chunk's GOAL.md with dependents

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        short_name: Short name for the chunk
        ticket_id: Optional ticket ID
        status: Initial status for the chunk (default: "IMPLEMENTING")

    Returns:
        Dict with keys:
        - external_chunk_path: Path to created chunk in external repo
        - project_refs: Dict mapping project repo ref to created external.yaml path

    Raises:
        TaskChunkError: If any step fails, with user-friendly message
    """
    # 1. Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskChunkError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # 2. Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_chunk_repo)
    except FileNotFoundError:
        raise TaskChunkError(
            f"External chunk repository '{config.external_chunk_repo}' not found or not accessible"
        )

    # 3. Get current SHA from external repo
    try:
        pinned_sha = get_current_sha(external_repo_path)
    except ValueError as e:
        raise TaskChunkError(
            f"Failed to resolve HEAD SHA in external repository '{config.external_chunk_repo}': {e}"
        )

    # 4. Create chunk in external repo
    chunks = Chunks(external_repo_path)
    external_chunk_path = chunks.create_chunk(ticket_id, short_name, status=status)
    external_chunk_id = external_chunk_path.name  # e.g., "0001-auth_token"

    # 5-6. For each project: calculate next ID, create external.yaml, build dependents
    dependents = []
    project_refs = {}

    for project_ref in config.projects:
        # Resolve project path
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
        except FileNotFoundError:
            raise TaskChunkError(
                f"Project directory '{project_ref}' not found or not accessible"
            )

        # Calculate next chunk ID for this project
        next_id = get_next_chunk_id(project_path)

        # Create external.yaml
        external_yaml_path = create_external_yaml(
            project_path=project_path,
            chunk_id=next_id,
            short_name=short_name,
            external_repo_ref=config.external_chunk_repo,
            external_chunk_id=external_chunk_id,
            pinned_sha=pinned_sha,
        )

        # Build dependent entry
        project_chunk_id = f"{next_id}-{short_name}"
        dependents.append({"repo": project_ref, "chunk": project_chunk_id})

        # Track created path
        project_refs[project_ref] = external_yaml_path

    # 7. Update external chunk's GOAL.md with dependents
    add_dependents_to_chunk(external_chunk_path, dependents)

    # 8. Return results
    return {
        "external_chunk_path": external_chunk_path,
        "project_refs": project_refs,
    }


# Chunk: docs/chunks/0033-list_task_aware - Task-aware chunk listing
def list_task_chunks(task_dir: Path) -> list[dict]:
    """List chunks from external repo with their dependents.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml

    Returns:
        List of dicts with keys: name, status, dependents
        Sorted by chunk number descending.

    Raises:
        TaskChunkError: If external repo not accessible
    """
    # Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskChunkError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_chunk_repo)
    except FileNotFoundError:
        raise TaskChunkError(
            f"External chunk repository '{config.external_chunk_repo}' not found or not accessible"
        )

    # List chunks from external repo
    chunks = Chunks(external_repo_path)
    chunk_list = chunks.list_chunks()

    results = []
    for _, chunk_name in chunk_list:
        frontmatter = chunks.parse_chunk_frontmatter(chunk_name)
        status = frontmatter.status.value if frontmatter else "UNKNOWN"
        # Convert ExternalChunkRef objects to dicts for API compatibility
        dependents = [{"repo": d.repo, "chunk": d.chunk} for d in frontmatter.dependents] if frontmatter else []
        results.append({
            "name": chunk_name,
            "status": status,
            "dependents": dependents,
        })

    return results


# Chunk: docs/chunks/0033-list_task_aware - Task-aware current chunk
def get_current_task_chunk(task_dir: Path) -> str | None:
    """Get the current (IMPLEMENTING) chunk from external repo.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml

    Returns:
        The chunk directory name if an IMPLEMENTING chunk exists, None otherwise.

    Raises:
        TaskChunkError: If external repo not accessible
    """
    # Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskChunkError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_chunk_repo)
    except FileNotFoundError:
        raise TaskChunkError(
            f"External chunk repository '{config.external_chunk_repo}' not found or not accessible"
        )

    # Get current chunk from external repo
    chunks = Chunks(external_repo_path)
    return chunks.get_current_chunk()
