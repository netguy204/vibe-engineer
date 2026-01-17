"""Scratchpad storage module - user-global work notes outside git repositories.

Provides storage at ~/.vibe/scratchpad/ for personal work notes that don't
belong in git repositories. Supports both project-scoped and task-scoped
scratchpad entries.
"""
# Subsystem: docs/subsystems/workflow_artifacts - User-global scratchpad storage variant
# Chunk: docs/chunks/scratchpad_storage - Scratchpad storage infrastructure
# Chunk: docs/chunks/scratchpad_cross_project - Cross-project scratchpad queries

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

from pydantic import ValidationError
import yaml

from models import (
    ScratchpadChunkFrontmatter,
    ScratchpadChunkStatus,
    ScratchpadNarrativeFrontmatter,
    ScratchpadNarrativeStatus,
)
from template_system import render_template


@dataclass
class ScratchpadEntry:
    """Represents a single scratchpad entry (chunk or narrative).

    Used for cross-project listing results.
    """

    context_name: str  # e.g., "vibe-engineer" or "task:cloud-migration"
    artifact_type: str  # "chunk" or "narrative"
    name: str  # directory name
    status: str  # e.g., "IMPLEMENTING", "DRAFTING"
    created_at: str  # ISO timestamp


@dataclass
class ScratchpadListResult:
    """Result of a scratchpad list operation.

    Groups entries by context for display purposes.
    """

    entries_by_context: dict[str, list[ScratchpadEntry]]
    total_count: int


class Scratchpad:
    """Manages the user-global scratchpad storage at ~/.vibe/scratchpad/.

    The scratchpad is independent of git repositories and provides a place
    for personal work notes. Entries are organized by project or task context.

    Storage structure:
        ~/.vibe/scratchpad/
        ├── [project-name]/           # single-project work
        │   ├── chunks/
        │   └── narratives/
        └── task:[task-name]/         # multi-repo task work
            ├── chunks/
            └── narratives/
    """

    DEFAULT_ROOT = Path.home() / ".vibe" / "scratchpad"

    def __init__(self, scratchpad_root: Path | None = None):
        """Initialize the scratchpad manager.

        Args:
            scratchpad_root: Override the default ~/.vibe/scratchpad/ location.
                            Primarily for testing purposes.
        """
        self.root = scratchpad_root or self.DEFAULT_ROOT

    def ensure_initialized(self) -> None:
        """Create scratchpad directory structure if it doesn't exist."""
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def derive_project_name(repo_path: Path) -> str:
        """Derive project name from repository path.

        Uses the directory name as the project name. This is simple but
        could collide if users have multiple projects with the same
        directory name in different locations.

        Args:
            repo_path: Path to the git repository.

        Returns:
            Project name derived from the directory name.
        """
        # Resolve symlinks and get the directory name
        return repo_path.resolve().name

    @staticmethod
    def get_task_prefix(task_name: str) -> str:
        """Format task name as 'task:' prefix.

        Args:
            task_name: The task name (e.g., "my-migration-task").

        Returns:
            Prefixed task name (e.g., "task:my-migration-task").
        """
        return f"task:{task_name}"

    def get_project_dir(self, project_name: str) -> Path:
        """Get path to project's scratchpad directory.

        Args:
            project_name: The project name.

        Returns:
            Path to the project's scratchpad directory.
        """
        return self.root / project_name

    def get_task_dir(self, task_name: str) -> Path:
        """Get path to task's scratchpad directory.

        Tasks are prefixed with 'task:' to distinguish from project names.

        Args:
            task_name: The task name.

        Returns:
            Path to the task's scratchpad directory.
        """
        return self.root / self.get_task_prefix(task_name)

    def resolve_context(
        self,
        project_path: Path | None = None,
        task_name: str | None = None,
    ) -> Path:
        """Resolve scratchpad directory from context.

        Priority:
        1. task_name (if provided) -> task:[task_name]/
        2. project_path (if provided) -> [derived_project_name]/

        Args:
            project_path: Path to a project/repository directory.
            task_name: Task name for multi-repo work.

        Returns:
            Path to the resolved scratchpad context directory.

        Raises:
            ValueError: If neither project_path nor task_name is provided.
        """
        if task_name is not None:
            return self.get_task_dir(task_name)
        if project_path is not None:
            project_name = self.derive_project_name(project_path)
            return self.get_project_dir(project_name)
        raise ValueError("Either project_path or task_name must be provided")

    def list_contexts(self) -> list[str]:
        """List all scratchpad contexts (projects and tasks).

        Returns:
            List of context names (project names and task:name prefixes).
        """
        if not self.root.exists():
            return []
        return [
            d.name
            for d in self.root.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    def _collect_entries_for_context(
        self,
        context_name: str,
        artifact_type: str | None = None,
        status: str | None = None,
    ) -> list[ScratchpadEntry]:
        """Collect entries from a single context.

        Args:
            context_name: The context name (project or task:name).
            artifact_type: Filter by "chunk" or "narrative" (None = both).
            status: Filter by status value (None = all statuses).

        Returns:
            List of ScratchpadEntry objects, sorted by created_at descending.
        """
        entries: list[ScratchpadEntry] = []
        context_path = self.root / context_name

        if not context_path.exists():
            return entries

        # Normalize status filter to uppercase
        status_filter = status.upper() if status else None

        # Collect chunks
        if artifact_type is None or artifact_type == "chunk":
            chunks_mgr = ScratchpadChunks(self, context_path)
            for chunk_id in chunks_mgr.enumerate_chunks():
                fm = chunks_mgr.parse_chunk_frontmatter(chunk_id)
                if fm:
                    entry_status = fm.status.value
                    created = fm.created_at
                else:
                    entry_status = "UNKNOWN"
                    created = ""

                # Apply status filter
                if status_filter and entry_status != status_filter:
                    continue

                entries.append(
                    ScratchpadEntry(
                        context_name=context_name,
                        artifact_type="chunk",
                        name=chunk_id,
                        status=entry_status,
                        created_at=created,
                    )
                )

        # Collect narratives
        if artifact_type is None or artifact_type == "narrative":
            narratives_mgr = ScratchpadNarratives(self, context_path)
            for narrative_id in narratives_mgr.enumerate_narratives():
                fm = narratives_mgr.parse_narrative_frontmatter(narrative_id)
                if fm:
                    entry_status = fm.status.value
                    created = fm.created_at
                else:
                    entry_status = "UNKNOWN"
                    created = ""

                # Apply status filter
                if status_filter and entry_status != status_filter:
                    continue

                entries.append(
                    ScratchpadEntry(
                        context_name=context_name,
                        artifact_type="narrative",
                        name=narrative_id,
                        status=entry_status,
                        created_at=created,
                    )
                )

        # Sort by created_at descending (newest first)
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries

    def list_all(
        self,
        artifact_type: str | None = None,
        context_type: str | None = None,
        status: str | None = None,
    ) -> ScratchpadListResult:
        """List all scratchpad entries across all contexts.

        Args:
            artifact_type: Filter by "chunk" or "narrative" (None = both).
            context_type: Filter by "task" or "project" (None = all).
            status: Filter by status value (None = all statuses).

        Returns:
            ScratchpadListResult with entries grouped by context.
        """
        entries_by_context: dict[str, list[ScratchpadEntry]] = {}
        total_count = 0

        for context_name in self.list_contexts():
            # Apply context type filter
            is_task = context_name.startswith("task:")
            if context_type == "task" and not is_task:
                continue
            if context_type == "project" and is_task:
                continue

            entries = self._collect_entries_for_context(
                context_name,
                artifact_type=artifact_type,
                status=status,
            )

            if entries:
                entries_by_context[context_name] = entries
                total_count += len(entries)

        return ScratchpadListResult(
            entries_by_context=entries_by_context,
            total_count=total_count,
        )

    def list_context(
        self,
        context_name: str,
        artifact_type: str | None = None,
        status: str | None = None,
    ) -> ScratchpadListResult:
        """List scratchpad entries for a single context.

        Args:
            context_name: The context name (project or task:name).
            artifact_type: Filter by "chunk" or "narrative" (None = both).
            status: Filter by status value (None = all statuses).

        Returns:
            ScratchpadListResult with entries for the specified context only.
        """
        entries = self._collect_entries_for_context(
            context_name,
            artifact_type=artifact_type,
            status=status,
        )

        if entries:
            return ScratchpadListResult(
                entries_by_context={context_name: entries},
                total_count=len(entries),
            )
        return ScratchpadListResult(entries_by_context={}, total_count=0)


class ScratchpadChunks:
    """Manages scratchpad chunks within a context directory.

    Provides CRUD operations for scratchpad chunks, which are simpler than
    in-repo chunks (no code_references, subsystems, etc.).
    """

    def __init__(self, scratchpad: Scratchpad, context_path: Path):
        """Initialize the chunks manager.

        Args:
            scratchpad: Parent Scratchpad instance.
            context_path: Path to the context (project or task) directory.
        """
        self.scratchpad = scratchpad
        self.context_path = context_path
        self.chunks_dir = context_path / "chunks"

    def enumerate_chunks(self) -> list[str]:
        """List chunk directory names.

        Returns:
            List of chunk directory names.
        """
        if not self.chunks_dir.exists():
            return []
        return [
            d.name
            for d in self.chunks_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    def create_chunk(
        self,
        short_name: str,
        ticket: str | None = None,
    ) -> Path:
        """Create a new scratchpad chunk with GOAL.md.

        Args:
            short_name: Short name for the chunk.
            ticket: Optional ticket reference (e.g., Linear ID).

        Returns:
            Path to the created chunk directory.

        Raises:
            ValueError: If a chunk with the same name already exists.
        """
        # Validate short_name format
        if not short_name or not re.match(r"^[a-z][a-z0-9_-]*$", short_name):
            raise ValueError(
                f"Invalid short_name '{short_name}': must start with lowercase letter "
                "and contain only lowercase letters, digits, underscores, and hyphens"
            )

        # Check for duplicates
        if short_name in self.enumerate_chunks():
            raise ValueError(f"Chunk '{short_name}' already exists")

        # Create the directory structure
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        chunk_path = self.chunks_dir / short_name
        chunk_path.mkdir()

        # Render GOAL.md from template
        created_at = datetime.now().isoformat()
        goal_content = render_template(
            "scratchpad_chunk",
            "GOAL.md.jinja2",
            short_name=short_name,
            ticket=ticket,
            created_at=created_at,
        )
        (chunk_path / "GOAL.md").write_text(goal_content)

        return chunk_path

    def get_chunk_path(self, chunk_id: str) -> Path | None:
        """Get path to a chunk directory.

        Args:
            chunk_id: The chunk directory name.

        Returns:
            Path to the chunk directory, or None if not found.
        """
        chunk_path = self.chunks_dir / chunk_id
        if chunk_path.exists() and chunk_path.is_dir():
            return chunk_path
        return None

    def get_chunk_goal_path(self, chunk_id: str) -> Path | None:
        """Get path to a chunk's GOAL.md file.

        Args:
            chunk_id: The chunk directory name.

        Returns:
            Path to GOAL.md, or None if not found.
        """
        chunk_path = self.get_chunk_path(chunk_id)
        if chunk_path is None:
            return None
        goal_path = chunk_path / "GOAL.md"
        if goal_path.exists():
            return goal_path
        return None

    def parse_chunk_frontmatter(self, chunk_id: str) -> ScratchpadChunkFrontmatter | None:
        """Parse YAML frontmatter from a chunk's GOAL.md.

        Args:
            chunk_id: The chunk directory name.

        Returns:
            ScratchpadChunkFrontmatter if valid, or None if not found or invalid.
        """
        goal_path = self.get_chunk_goal_path(chunk_id)
        if goal_path is None:
            return None

        content = goal_path.read_text()
        # Extract frontmatter between --- markers
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return None

        try:
            frontmatter = yaml.safe_load(match.group(1))
            if not isinstance(frontmatter, dict):
                return None
            return ScratchpadChunkFrontmatter.model_validate(frontmatter)
        except (yaml.YAMLError, ValidationError):
            return None

    def list_chunks(self) -> list[str]:
        """List chunks ordered by creation time (newest first).

        Returns:
            List of chunk directory names, ordered by created_at descending.
        """
        chunks = self.enumerate_chunks()
        if not chunks:
            return []

        # Parse frontmatter to get created_at for sorting
        chunk_times: list[tuple[str, str]] = []
        for chunk_id in chunks:
            fm = self.parse_chunk_frontmatter(chunk_id)
            if fm:
                chunk_times.append((chunk_id, fm.created_at))
            else:
                # Fallback: use empty string (will sort to end)
                chunk_times.append((chunk_id, ""))

        # Sort by created_at descending (newest first)
        chunk_times.sort(key=lambda x: x[1], reverse=True)
        return [chunk_id for chunk_id, _ in chunk_times]

    def archive_chunk(self, chunk_id: str) -> Path:
        """Archive a chunk by updating its status.

        Args:
            chunk_id: The chunk directory name.

        Returns:
            Path to the archived chunk directory.

        Raises:
            ValueError: If chunk not found.
        """
        goal_path = self.get_chunk_goal_path(chunk_id)
        if goal_path is None:
            raise ValueError(f"Chunk '{chunk_id}' not found")

        # Update status in frontmatter
        content = goal_path.read_text()
        match = re.match(r"^(---\s*\n)(.*?)(\n---)", content, re.DOTALL)
        if not match:
            raise ValueError(f"Chunk '{chunk_id}' has invalid frontmatter")

        try:
            frontmatter = yaml.safe_load(match.group(2))
            if not isinstance(frontmatter, dict):
                raise ValueError(f"Chunk '{chunk_id}' has invalid frontmatter")

            frontmatter["status"] = ScratchpadChunkStatus.ARCHIVED.value
            new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)

            # Preserve content after frontmatter
            rest_of_file = content[match.end():]
            goal_path.write_text(f"---\n{new_frontmatter}---{rest_of_file}")

        except yaml.YAMLError as e:
            raise ValueError(f"Chunk '{chunk_id}' has invalid YAML frontmatter: {e}")

        return self.chunks_dir / chunk_id


class ScratchpadNarratives:
    """Manages scratchpad narratives within a context directory.

    Provides CRUD operations for scratchpad narratives, which are used
    for planning multi-chunk work.
    """

    def __init__(self, scratchpad: Scratchpad, context_path: Path):
        """Initialize the narratives manager.

        Args:
            scratchpad: Parent Scratchpad instance.
            context_path: Path to the context (project or task) directory.
        """
        self.scratchpad = scratchpad
        self.context_path = context_path
        self.narratives_dir = context_path / "narratives"

    def enumerate_narratives(self) -> list[str]:
        """List narrative directory names.

        Returns:
            List of narrative directory names.
        """
        if not self.narratives_dir.exists():
            return []
        return [
            d.name
            for d in self.narratives_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    def create_narrative(self, short_name: str) -> Path:
        """Create a new scratchpad narrative with OVERVIEW.md.

        Args:
            short_name: Short name for the narrative.

        Returns:
            Path to the created narrative directory.

        Raises:
            ValueError: If a narrative with the same name already exists.
        """
        # Validate short_name format
        if not short_name or not re.match(r"^[a-z][a-z0-9_-]*$", short_name):
            raise ValueError(
                f"Invalid short_name '{short_name}': must start with lowercase letter "
                "and contain only lowercase letters, digits, underscores, and hyphens"
            )

        # Check for duplicates
        if short_name in self.enumerate_narratives():
            raise ValueError(f"Narrative '{short_name}' already exists")

        # Create the directory structure
        self.narratives_dir.mkdir(parents=True, exist_ok=True)
        narrative_path = self.narratives_dir / short_name
        narrative_path.mkdir()

        # Render OVERVIEW.md from template
        created_at = datetime.now().isoformat()
        overview_content = render_template(
            "scratchpad_narrative",
            "OVERVIEW.md.jinja2",
            short_name=short_name,
            created_at=created_at,
        )
        (narrative_path / "OVERVIEW.md").write_text(overview_content)

        return narrative_path

    def get_narrative_path(self, narrative_id: str) -> Path | None:
        """Get path to a narrative directory.

        Args:
            narrative_id: The narrative directory name.

        Returns:
            Path to the narrative directory, or None if not found.
        """
        narrative_path = self.narratives_dir / narrative_id
        if narrative_path.exists() and narrative_path.is_dir():
            return narrative_path
        return None

    def get_narrative_overview_path(self, narrative_id: str) -> Path | None:
        """Get path to a narrative's OVERVIEW.md file.

        Args:
            narrative_id: The narrative directory name.

        Returns:
            Path to OVERVIEW.md, or None if not found.
        """
        narrative_path = self.get_narrative_path(narrative_id)
        if narrative_path is None:
            return None
        overview_path = narrative_path / "OVERVIEW.md"
        if overview_path.exists():
            return overview_path
        return None

    def parse_narrative_frontmatter(self, narrative_id: str) -> ScratchpadNarrativeFrontmatter | None:
        """Parse YAML frontmatter from a narrative's OVERVIEW.md.

        Args:
            narrative_id: The narrative directory name.

        Returns:
            ScratchpadNarrativeFrontmatter if valid, or None if not found or invalid.
        """
        overview_path = self.get_narrative_overview_path(narrative_id)
        if overview_path is None:
            return None

        content = overview_path.read_text()
        # Extract frontmatter between --- markers
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return None

        try:
            frontmatter = yaml.safe_load(match.group(1))
            if not isinstance(frontmatter, dict):
                return None
            return ScratchpadNarrativeFrontmatter.model_validate(frontmatter)
        except (yaml.YAMLError, ValidationError):
            return None

    def list_narratives(self) -> list[str]:
        """List narratives ordered by creation time (newest first).

        Returns:
            List of narrative directory names, ordered by created_at descending.
        """
        narratives = self.enumerate_narratives()
        if not narratives:
            return []

        # Parse frontmatter to get created_at for sorting
        narrative_times: list[tuple[str, str]] = []
        for narrative_id in narratives:
            fm = self.parse_narrative_frontmatter(narrative_id)
            if fm:
                narrative_times.append((narrative_id, fm.created_at))
            else:
                # Fallback: use empty string (will sort to end)
                narrative_times.append((narrative_id, ""))

        # Sort by created_at descending (newest first)
        narrative_times.sort(key=lambda x: x[1], reverse=True)
        return [narrative_id for narrative_id, _ in narrative_times]

    # Chunk: docs/chunks/scratchpad_narrative_commands - Scratchpad narrative commands
    def update_status(
        self, narrative_id: str, new_status: ScratchpadNarrativeStatus
    ) -> tuple[ScratchpadNarrativeStatus, ScratchpadNarrativeStatus]:
        """Update a narrative's status.

        Args:
            narrative_id: The narrative directory name.
            new_status: The new status to set.

        Returns:
            Tuple of (old_status, new_status).

        Raises:
            ValueError: If narrative not found or has invalid frontmatter.
        """
        overview_path = self.get_narrative_overview_path(narrative_id)
        if overview_path is None:
            raise ValueError(f"Narrative '{narrative_id}' not found")

        content = overview_path.read_text()
        match = re.match(r"^(---\s*\n)(.*?)(\n---)", content, re.DOTALL)
        if not match:
            raise ValueError(f"Narrative '{narrative_id}' has invalid frontmatter")

        try:
            frontmatter = yaml.safe_load(match.group(2))
            if not isinstance(frontmatter, dict):
                raise ValueError(f"Narrative '{narrative_id}' has invalid frontmatter")

            old_status = ScratchpadNarrativeStatus(frontmatter.get("status", "DRAFTING"))
            frontmatter["status"] = new_status.value
            new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)

            rest_of_file = content[match.end():]
            overview_path.write_text(f"---\n{new_frontmatter}---{rest_of_file}")

            return (old_status, new_status)

        except yaml.YAMLError as e:
            raise ValueError(f"Narrative '{narrative_id}' has invalid YAML frontmatter: {e}")

    def archive_narrative(self, narrative_id: str) -> Path:
        """Archive a narrative by updating its status.

        Args:
            narrative_id: The narrative directory name.

        Returns:
            Path to the archived narrative directory.

        Raises:
            ValueError: If narrative not found.
        """
        self.update_status(narrative_id, ScratchpadNarrativeStatus.ARCHIVED)
        return self.narratives_dir / narrative_id
