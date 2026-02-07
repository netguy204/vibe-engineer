"""Chunks module - business logic for chunk management.

# Chunk: docs/chunks/chunks_decompose - Module decomposition to reduce file size
# Chunk: docs/chunks/chunk_validator_extract - Chunk validation logic extraction

This module provides the core Chunks class and chunk management functions.
Related functionality has been extracted to focused modules:

- backreferences.py: BackreferenceInfo, count_backreferences, update_backreferences
- consolidation.py: ConsolidationResult, consolidate_chunks
- cluster_analysis.py: SuggestPrefixResult, ClusterResult, cluster_chunks, suggest_prefix
- chunk_validation.py: ValidationResult, validate_chunk_complete, validate_chunk_injectable, plan_has_content

All extracted symbols are re-exported for backward compatibility.
"""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Subsystem: docs/subsystems/cluster_analysis - Chunk naming and clustering
# Chunk: docs/chunks/artifact_manager_base - Refactored to inherit from ArtifactManager
# Chunk: docs/chunks/ordering_remove_seqno - Short name directory format and chunk resolution
# Chunk: docs/chunks/populate_created_after - Automatic created_after population on chunk creation

from __future__ import annotations

from dataclasses import dataclass, field
import pathlib
from pathlib import Path
import re
from typing import TYPE_CHECKING

from pydantic import ValidationError

from artifact_manager import ArtifactManager
from backreferences import (
    BackreferenceInfo,
    CHUNK_BACKREF_PATTERN,
    NARRATIVE_BACKREF_PATTERN,
    SUBSYSTEM_BACKREF_PATTERN,
    count_backreferences,
    update_backreferences,
)
from consolidation import ConsolidationResult, consolidate_chunks
from cluster_analysis import SuggestPrefixResult, ClusterResult, cluster_chunks, suggest_prefix
from artifact_ordering import ArtifactIndex, ArtifactType
from external_refs import is_external_artifact, load_external_ref, ARTIFACT_DIR_NAME
import repo_cache
from models import (
    CodeReference,
    SymbolicReference,
    SubsystemRelationship,
    CHUNK_ID_PATTERN,
    ChunkFrontmatter,
    ChunkStatus,
    VALID_CHUNK_TRANSITIONS,
)
from symbols import is_parent_of, parse_reference, extract_symbols, qualify_ref
from template_system import ActiveChunk, TemplateContext, render_to_directory
from chunk_validation import (
    ValidationResult,
    plan_has_content,
    validate_chunk_complete as _validate_chunk_complete,
    validate_chunk_injectable as _validate_chunk_injectable,
)

if TYPE_CHECKING:
    from investigations import Investigations
    from narratives import Narratives
    from project import Project
    from subsystems import Subsystems


# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/task_chunk_validation - Result dataclass for resolved chunk locations
@dataclass
class ChunkLocation:
    """Result of resolving a chunk's location.

    Used to track whether a chunk is local or external, and provide
    the resolved path for validation.

    For cache-based resolution (external chunks without task context),
    chunk_path and project_dir point to the local reference directory,
    but cached_content contains the actual GOAL.md content from the cache.
    """

    chunk_name: str
    chunk_path: pathlib.Path
    project_dir: pathlib.Path  # The project directory containing the chunk
    is_external: bool = False
    external_repo: str | None = None  # org/repo format for external chunks
    # For cache-based resolution (no task context)
    cached_content: str | None = None  # GOAL.md content from repo cache
    cached_sha: str | None = None  # SHA used for cache resolution


# Subsystem: docs/subsystems/template_system - Uses template rendering
class Chunks(ArtifactManager[ChunkFrontmatter, ChunkStatus]):
    """Utility class for managing chunk documentation."""

    # Chunk: docs/chunks/implement_chunk_start-ve-001 - Chunks class initialization
    def __init__(self, project_dir: Path | pathlib.Path) -> None:
        """Initialize with project directory.

        Args:
            project_dir: Path to the project root directory.
        """
        super().__init__(Path(project_dir))
        # Ensure chunk_dir exists (backward compatibility)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

    # Abstract property implementations from ArtifactManager
    @property
    def artifact_dir_name(self) -> str:
        return "chunks"

    @property
    def main_filename(self) -> str:
        return "GOAL.md"

    @property
    def frontmatter_model_class(self) -> type[ChunkFrontmatter]:
        return ChunkFrontmatter

    @property
    def status_enum(self) -> type[ChunkStatus]:
        return ChunkStatus

    @property
    def transition_map(self) -> dict[ChunkStatus, set[ChunkStatus]]:
        return VALID_CHUNK_TRANSITIONS

    # Backward compatibility aliases
    @property
    def project_dir(self) -> Path:
        """Return the project root directory (alias for backward compatibility)."""
        return self._project_dir

    @property
    def chunk_dir(self) -> Path:
        """Return the path to the chunks directory (alias for artifact_dir)."""
        return self.artifact_dir

    # Chunk: docs/chunks/implement_chunk_start-ve-001 - List existing chunk directories
    def enumerate_chunks(self) -> list[str]:
        """List chunk directory names (alias for enumerate_artifacts)."""
        return self.enumerate_artifacts()

    # Chunk: docs/chunks/implement_chunk_start-ve-001 - Count of existing chunks
    @property
    def num_chunks(self) -> int:
        """Return the number of chunks."""
        return len(self.enumerate_chunks())

    # Chunk: docs/chunks/chunknaming_drop_ticket - Collision detection ignoring ticket_id
    # Chunk: docs/chunks/implement_chunk_start-ve-001 - Detects existing chunks with same short_name only
    def find_duplicates(self, short_name: str, ticket_id: str | None) -> list[str]:
        """Find existing chunks with the same short_name.

        Args:
            short_name: The short name to check for collisions.
            ticket_id: Optional ticket ID (kept for backward compatibility but
                       not used - ticket_id no longer affects directory names).

        Returns:
            List of existing chunk directory names that would collide.
        """
        # Match on short_name only - ticket_id is stored in frontmatter, not directory name
        duplicates = []
        for name in self.enumerate_chunks():
            # Directory name is the short name
            if name == short_name:
                duplicates.append(name)
        return duplicates

    # Chunk: docs/chunks/artifact_list_ordering - Updated to use ArtifactIndex for causal ordering
    # Chunk: docs/chunks/chunk_list_command-ve-002 - Lists chunks in causal order (newest first) using ArtifactIndex
    def list_chunks(self) -> list[str]:
        """List all chunks in causal order (newest first).

        Uses ArtifactIndex for topological ordering based on created_after
        dependencies. Falls back to sequence number order when created_after
        is not populated.

        Returns:
            List of chunk directory names, ordered newest first.
            Returns empty list if no chunks exist.
        """
        artifact_index = ArtifactIndex(self.project_dir)
        ordered = artifact_index.get_ordered(ArtifactType.CHUNK)
        # Reverse to get newest first (ArtifactIndex returns oldest first)
        return list(reversed(ordered))

    # Chunk: docs/chunks/artifact_list_ordering - Updated for new list_chunks return type
    # Chunk: docs/chunks/chunk_list_command-ve-002 - Returns first chunk in causal order (newest)
    def get_latest_chunk(self) -> str | None:
        """Return the first chunk in causal order (newest).

        Returns:
            The chunk directory name if chunks exist, None otherwise.
        """
        chunks = self.list_chunks()
        if chunks:
            return chunks[0]
        return None

    # Chunk: docs/chunks/artifact_list_ordering - Updated for new list_chunks return type
    # Chunk: docs/chunks/chunk_frontmatter_model - Uses ChunkStatus.IMPLEMENTING for status comparison
    # Chunk: docs/chunks/future_chunk_creation - Returns the first IMPLEMENTING chunk in causal order, ignoring FUTURE/ACTIVE/SUPERSEDED/HISTORICAL
    def get_current_chunk(self) -> str | None:
        """Return the first IMPLEMENTING chunk in causal order.

        This finds the "current" chunk that is actively being worked on,
        ignoring FUTURE, ACTIVE, SUPERSEDED, and HISTORICAL chunks.

        Returns:
            The chunk directory name if an IMPLEMENTING chunk exists, None otherwise.
        """
        chunks = self.list_chunks()
        for chunk_name in chunks:
            frontmatter = self.parse_chunk_frontmatter(chunk_name)
            if frontmatter and frontmatter.status == ChunkStatus.IMPLEMENTING:
                return chunk_name
        return None

    # Chunk: docs/chunks/chunk_list_flags - New method returning up to 10 most recently created ACTIVE chunks
    def get_recent_active_chunks(self, limit: int = 10) -> list[str]:
        """Return the most recently created ACTIVE chunks.

        Returns ACTIVE chunks ordered by creation (newest first), limited to
        the specified number. Uses the existing list_chunks() causal ordering
        and filters to only ACTIVE status.

        Args:
            limit: Maximum number of chunks to return (default: 10).

        Returns:
            List of chunk directory names, ordered newest first, limited to `limit`.
            Returns empty list if no ACTIVE chunks exist.
        """
        chunks = self.list_chunks()
        active_chunks = []
        for chunk_name in chunks:
            frontmatter = self.parse_chunk_frontmatter(chunk_name)
            if frontmatter and frontmatter.status == ChunkStatus.ACTIVE:
                active_chunks.append(chunk_name)
                if len(active_chunks) >= limit:
                    break
        return active_chunks

    # Chunk: docs/chunks/chunk_last_active - Core ACTIVE tip lookup with mtime-based selection
    def get_last_active_chunk(self) -> str | None:
        """Return the most recently completed ACTIVE tip chunk.

        This finds the ACTIVE chunk that:
        1. Has ACTIVE status
        2. Is a "tip" in the causal ordering (not in any other chunk's created_after)
        3. Has the most recent GOAL.md mtime among qualifying chunks

        This is useful for identifying the just-completed chunk after running
        chunk-complete, when the chunk status has changed from IMPLEMENTING to ACTIVE.

        Returns:
            The chunk directory name if an ACTIVE tip exists, None otherwise.
        """
        # Get all tips from the artifact index
        artifact_index = ArtifactIndex(self.project_dir)
        tips = artifact_index.find_tips(ArtifactType.CHUNK)

        # Filter to only ACTIVE status
        active_tips = []
        for tip in tips:
            frontmatter = self.parse_chunk_frontmatter(tip)
            if frontmatter and frontmatter.status == ChunkStatus.ACTIVE:
                active_tips.append(tip)

        if not active_tips:
            return None

        # If only one ACTIVE tip, return it
        if len(active_tips) == 1:
            return active_tips[0]

        # Multiple ACTIVE tips: select by most recent GOAL.md mtime
        def get_goal_mtime(chunk_name: str) -> float:
            goal_path = self.chunk_dir / chunk_name / "GOAL.md"
            if goal_path.exists():
                return goal_path.stat().st_mtime
            return 0.0

        # Sort by mtime descending, return the most recent
        active_tips.sort(key=get_goal_mtime, reverse=True)
        return active_tips[0]

    # Chunk: docs/chunks/chunk_frontmatter_model - Uses ChunkStatus.FUTURE for status comparison
    # Chunk: docs/chunks/future_chunk_creation - Transitions FUTURE chunk to IMPLEMENTING, enforcing single IMPLEMENTING constraint
    def activate_chunk(self, chunk_id: str) -> str:
        """Activate a FUTURE chunk by changing its status to IMPLEMENTING.

        Args:
            chunk_id: The chunk ID (4-digit or full name) to activate.

        Returns:
            The activated chunk's directory name.

        Raises:
            ValueError: If chunk doesn't exist, isn't FUTURE, or another
                       chunk is already IMPLEMENTING.
        """
        from frontmatter import update_frontmatter_field

        chunk_name = self.resolve_chunk_id(chunk_id)
        if chunk_name is None:
            raise ValueError(f"Chunk '{chunk_id}' not found")

        # Check if there's already an IMPLEMENTING chunk
        current = self.get_current_chunk()
        if current is not None:
            raise ValueError(
                f"Cannot activate: chunk '{current}' is already IMPLEMENTING. "
                f"Complete or mark it as ACTIVE first."
            )

        # Check if target chunk is FUTURE
        frontmatter, errors = self.parse_chunk_frontmatter_with_errors(chunk_name)
        if frontmatter is None:
            error_detail = "; ".join(errors) if errors else "unknown error"
            raise ValueError(f"Could not parse frontmatter for chunk '{chunk_id}': {error_detail}")

        if frontmatter.status != ChunkStatus.FUTURE:
            raise ValueError(
                f"Cannot activate: chunk '{chunk_name}' has status '{frontmatter.status.value}', "
                f"expected 'FUTURE'"
            )

        # Update status to IMPLEMENTING
        goal_path = self.get_chunk_goal_path(chunk_name)
        update_frontmatter_field(goal_path, "status", "IMPLEMENTING")

        return chunk_name

    # Subsystem: docs/subsystems/template_system - Template rendering system
    # Subsystem: docs/subsystems/template_system - Uses render_to_directory
    # Chunk: docs/chunks/chunk_template_expansion - Template rendering with ActiveChunk context
    # Chunk: docs/chunks/chunknaming_drop_ticket - Directory naming without ticket suffix
    # Chunk: docs/chunks/coderef_format_prompting - Projects parameter for task-context template rendering
    # Chunk: docs/chunks/future_chunk_creation - Extended with status parameter to support FUTURE and IMPLEMENTING statuses
    # Chunk: docs/chunks/implement_chunk_start-ve-001 - Directory creation with correct path format, template rendering
    def create_chunk(
        self,
        ticket_id: str | None,
        short_name: str,
        status: str = "IMPLEMENTING",
        task_context: bool = False,
        projects: list[str] | None = None,
    ):
        """Instantiate the chunk templates for the given ticket and short name.

        Args:
            ticket_id: Optional ticket ID to include in chunk directory name.
            short_name: Short name for the chunk.
            status: Initial status for the chunk (default: "IMPLEMENTING").
            task_context: If True, render task-context-aware template examples.
            projects: List of project org/repo strings for template examples.

        Raises:
            ValueError: If a chunk with the same short_name already exists.
        """
        # Check for collisions before creating
        duplicates = self.find_duplicates(short_name, ticket_id)
        if duplicates:
            raise ValueError(
                f"Chunk with short_name '{short_name}' already exists: {duplicates[0]}"
            )

        # Chunk: docs/chunks/chunk_create_guard - Guard logic preventing multiple IMPLEMENTING chunks
        # Only guard non-FUTURE chunk creation
        if status != "FUTURE":
            current = self.get_current_chunk()
            if current is not None:
                raise ValueError(
                    f"Cannot create: chunk '{current}' is already IMPLEMENTING. "
                    f"Run 've chunk complete' first."
                )

        # Get current chunk tips for created_after field
        artifact_index = ArtifactIndex(self.project_dir)
        tips = artifact_index.find_tips(ArtifactType.CHUNK)

        # Build directory name using short_name only (ticket_id goes in frontmatter, not directory)
        chunk_path = self.chunk_dir / short_name
        chunk = ActiveChunk(
            short_name=short_name,
            id=chunk_path.name,
            _project_dir=self.project_dir,
        )
        context = TemplateContext(active_chunk=chunk)
        render_to_directory(
            "chunk",
            chunk_path,
            context=context,
            ticket_id=ticket_id,
            status=status,
            created_after=tips,
            task_context=task_context,
            projects=projects or [],
        )
        return chunk_path

    # Chunk: docs/chunks/chunk_overlap_command - Resolves chunk ID to directory name
    def resolve_chunk_id(self, chunk_id: str) -> str | None:
        """Resolve a chunk ID to its directory name.

        Looks for an exact match in chunk directories.

        Returns:
            The full chunk directory name, or None if not found.
        """
        chunks = self.enumerate_chunks()
        # Exact match
        if chunk_id in chunks:
            return chunk_id
        return None

    # Chunk: docs/chunks/chunk_overlap_command - Resolves chunk ID to GOAL.md path
    def get_chunk_goal_path(self, chunk_id: str) -> pathlib.Path | None:
        """Resolve chunk ID to GOAL.md path.

        Returns:
            Path to GOAL.md, or None if chunk not found.
        """
        chunk_name = self.resolve_chunk_id(chunk_id)
        if chunk_name is None:
            return None
        return self.chunk_dir / chunk_name / "GOAL.md"

    # Chunk: docs/chunks/reviewer_decision_create_cli - Extracts success criteria from GOAL.md
    def get_success_criteria(self, chunk_id: str) -> list[str]:
        """Extract success criteria from a chunk's GOAL.md.

        Finds the `## Success Criteria` section and extracts bullet points.

        Args:
            chunk_id: The chunk ID to extract criteria from.

        Returns:
            List of success criteria strings. Empty list if chunk not found
            or no criteria section exists.
        """
        goal_path = self.get_chunk_goal_path(chunk_id)
        if goal_path is None or not goal_path.exists():
            return []

        content = goal_path.read_text()

        # Find the Success Criteria section
        # Match "## Success Criteria" and extract until the next ## or end of file
        criteria_match = re.search(
            r"## Success Criteria\s*\n(.*?)(?=\n## |\Z)",
            content,
            re.DOTALL | re.IGNORECASE
        )

        if not criteria_match:
            return []

        criteria_section = criteria_match.group(1)

        # Extract bullet points (lines starting with - or *)
        criteria = []
        for line in criteria_section.split("\n"):
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                # Remove the bullet prefix
                criterion = line[2:].strip()
                if criterion:
                    criteria.append(criterion)

        return criteria

    # Chunk: docs/chunks/chunk_overlap_command - Extracts and parses YAML frontmatter from GOAL.md
    def parse_chunk_frontmatter(self, chunk_id: str) -> ChunkFrontmatter | None:
        """Parse YAML frontmatter from a chunk's GOAL.md.

        Returns:
            ChunkFrontmatter if valid, or None if chunk not found or frontmatter invalid.
        """
        frontmatter, _ = self.parse_chunk_frontmatter_with_errors(chunk_id)
        return frontmatter

    # Chunk: docs/chunks/coderef_format_prompting - Frontmatter parsing that surfaces validation error details
    # Chunk: docs/chunks/frontmatter_io - Migrated to use shared frontmatter utilities
    def parse_chunk_frontmatter_with_errors(
        self, chunk_id: str
    ) -> tuple[ChunkFrontmatter | None, list[str]]:
        """Parse YAML frontmatter from a chunk's GOAL.md with error details.

        Returns:
            Tuple of (ChunkFrontmatter, errors) where:
            - ChunkFrontmatter is the parsed frontmatter if valid, None otherwise
            - errors is a list of error messages (empty if parsing succeeded)
        """
        from frontmatter import parse_frontmatter_with_errors

        goal_path = self.get_chunk_goal_path(chunk_id)
        if goal_path is None or not goal_path.exists():
            return None, [f"Chunk '{chunk_id}' not found"]

        return parse_frontmatter_with_errors(goal_path, ChunkFrontmatter)

    # Chunk: docs/chunks/task_chunk_validation - Parse frontmatter from cached content strings
    # Chunk: docs/chunks/frontmatter_io - Migrated to use shared frontmatter utilities
    def _parse_frontmatter_from_content(self, content: str) -> ChunkFrontmatter | None:
        """Parse YAML frontmatter from GOAL.md content string.

        Used for cache-based resolution where we have content but not a file path.

        Args:
            content: Full GOAL.md content including frontmatter

        Returns:
            ChunkFrontmatter if valid, or None if frontmatter invalid.
        """
        from frontmatter import parse_frontmatter_from_content

        return parse_frontmatter_from_content(content, ChunkFrontmatter)

    # Chunk: docs/chunks/task_chunk_validation - External chunk resolution via task context
    def resolve_chunk_location(
        self, chunk_id: str, task_dir: pathlib.Path | None = None
    ) -> ChunkLocation | None:
        """Resolve a chunk's location, supporting external chunk references.

        For local chunks (GOAL.md exists), returns the local path.
        For external chunks (external.yaml without GOAL.md):
          - With task context: resolves to live working copy in task directory
          - Without task context: uses repo cache to read content at pinned SHA

        Args:
            chunk_id: The chunk directory name to resolve.
            task_dir: Optional task directory for resolving to live working copies.

        Returns:
            ChunkLocation if found, None if not found.
            For cache-based resolution, cached_content contains the GOAL.md content.
        """
        chunk_path = self.chunk_dir / chunk_id

        # Check if chunk directory exists
        if not chunk_path.exists():
            return None

        # Check if this is an external reference
        if is_external_artifact(chunk_path, ArtifactType.CHUNK):
            # Load external.yaml to get the reference info
            try:
                external_ref = load_external_ref(chunk_path)
            except FileNotFoundError:
                return None

            # With task context, resolve to the live working copy
            if task_dir is not None:
                from task_utils import (
                    load_task_config,
                    resolve_repo_directory,
                )

                try:
                    config = load_task_config(task_dir)
                    external_repo_path = resolve_repo_directory(
                        task_dir, config.external_artifact_repo
                    )

                    # Find the actual chunk in the external repo
                    external_chunk_path = (
                        external_repo_path
                        / "docs"
                        / ARTIFACT_DIR_NAME[ArtifactType.CHUNK]
                        / external_ref.artifact_id
                    )

                    if external_chunk_path.exists():
                        return ChunkLocation(
                            chunk_name=external_ref.artifact_id,
                            chunk_path=external_chunk_path,
                            project_dir=external_repo_path,
                            is_external=True,
                            external_repo=external_ref.repo,
                        )
                    else:
                        # External chunk referenced but not found in external repo
                        return None

                except (FileNotFoundError, ValueError):
                    # Task config missing or repo not found - fall through to cache
                    pass

            # Without task context (or task resolution failed), use repo cache
            # Determine SHA to use - prefer pinned, fall back to track
            if external_ref.pinned:
                resolved_sha = external_ref.pinned
            else:
                track = external_ref.track or "HEAD"
                try:
                    resolved_sha = repo_cache.resolve_ref(external_ref.repo, track)
                except ValueError:
                    # Can't resolve ref - return location without content
                    return ChunkLocation(
                        chunk_name=external_ref.artifact_id,
                        chunk_path=chunk_path,
                        project_dir=self.project_dir,
                        is_external=True,
                        external_repo=external_ref.repo,
                    )

            # Read GOAL.md from cache
            goal_path = f"docs/{ARTIFACT_DIR_NAME[ArtifactType.CHUNK]}/{external_ref.artifact_id}/GOAL.md"
            try:
                cached_content = repo_cache.get_file_at_ref(
                    external_ref.repo, resolved_sha, goal_path
                )
            except ValueError:
                # Chunk not found in cache
                return None

            return ChunkLocation(
                chunk_name=external_ref.artifact_id,
                chunk_path=chunk_path,
                project_dir=self.project_dir,
                is_external=True,
                external_repo=external_ref.repo,
                cached_content=cached_content,
                cached_sha=resolved_sha,
            )

        # Local chunk with GOAL.md - resolve directly
        return ChunkLocation(
            chunk_name=chunk_id,
            chunk_path=chunk_path,
            project_dir=self.project_dir,
            is_external=False,
        )

    # Chunk: docs/chunks/chunk_overlap_command - Parses nested code_references format into file->line mappings
    def parse_code_references(self, refs: list) -> dict[str, tuple[int, int]]:
        """Parse code_references from frontmatter into file -> (earliest, latest) mapping.

        Uses Pydantic models for validation. Raises ValidationError if malformed.

        Args:
            refs: List of code reference dicts from frontmatter.

        Returns:
            Dict mapping file paths to (earliest_line, latest_line) tuples.

        Raises:
            pydantic.ValidationError: If any reference is malformed.
        """
        result: dict[str, tuple[int, int]] = {}

        for ref in refs:
            validated = CodeReference.model_validate(ref)

            for r in validated.ranges:
                # Parse "10-20" or "10" format
                if "-" in r.lines:
                    parts = r.lines.split("-")
                    start, end = int(parts[0]), int(parts[1])
                else:
                    start = end = int(r.lines)

                if validated.file in result:
                    curr_earliest, curr_latest = result[validated.file]
                    result[validated.file] = (min(curr_earliest, start), max(curr_latest, end))
                else:
                    result[validated.file] = (start, end)

        return result

    def _extract_symbolic_refs(self, code_refs: list) -> list[str]:
        """Extract symbolic reference strings from code_references list.

        Args:
            code_refs: List of code reference dicts (symbolic format).

        Returns:
            List of reference strings (e.g., ["src/foo.py#Bar", "src/baz.py"]).
        """
        refs = []
        for ref in code_refs:
            if "ref" in ref:
                refs.append(ref["ref"])
        return refs

    def _is_symbolic_format(self, code_refs: list) -> bool:
        """Check if code_references use symbolic format (has 'ref' key)."""
        return any("ref" in ref for ref in code_refs)

    # Chunk: docs/chunks/chunk_overlap_command - Finds ACTIVE chunks with lower IDs having overlapping references
    def find_overlapping_chunks(self, chunk_id: str) -> list[str]:
        """Find ACTIVE chunks created before target with overlapping code references.

        Uses causal ordering (created_after field) to determine which chunks are
        "older" than the target. Supports both symbolic references and line-based
        references.

        Args:
            chunk_id: The chunk ID to check.

        Returns:
            List of affected chunk directory names.

        Raises:
            ValueError: If chunk_id doesn't exist.
        """
        chunk_name = self.resolve_chunk_id(chunk_id)
        if chunk_name is None:
            raise ValueError(f"Chunk '{chunk_id}' not found")

        # Parse target chunk
        frontmatter = self.parse_chunk_frontmatter(chunk_id)
        if frontmatter is None:
            raise ValueError(f"Chunk '{chunk_id}' not found")

        # Convert SymbolicReference objects to dicts for existing helper methods
        code_refs = [{"ref": ref.ref, "implements": ref.implements} for ref in frontmatter.code_references]
        if not code_refs:
            return []

        # Detect format and extract references
        target_is_symbolic = self._is_symbolic_format(code_refs)
        if target_is_symbolic:
            target_refs = self._extract_symbolic_refs(code_refs)
            if not target_refs:
                return []
        else:
            target_refs_dict = self.parse_code_references(code_refs)
            if not target_refs_dict:
                return []

        # Get ancestors of the target chunk (all chunks created before it)
        artifact_index = ArtifactIndex(self.project_dir)
        target_ancestors = artifact_index.get_ancestors(ArtifactType.CHUNK, chunk_name)

        # Find all ACTIVE chunks that are ancestors (created before target)
        affected = []
        for name in self.enumerate_chunks():
            # Only check chunks that are ancestors
            if name not in target_ancestors:
                continue

            # Check if ACTIVE
            fm = self.parse_chunk_frontmatter(name)
            if fm is None or fm.status != ChunkStatus.ACTIVE:
                continue

            # Convert SymbolicReference objects to dicts for existing helper methods
            candidate_refs_raw = [{"ref": ref.ref, "implements": ref.implements} for ref in fm.code_references]
            if not candidate_refs_raw:
                continue

            candidate_is_symbolic = self._is_symbolic_format(candidate_refs_raw)

            # Handle overlap based on format combinations
            local_project = "."
            if target_is_symbolic and candidate_is_symbolic:
                # Both symbolic: use compute_symbolic_overlap
                candidate_refs = self._extract_symbolic_refs(candidate_refs_raw)
                if compute_symbolic_overlap(target_refs, candidate_refs, local_project):
                    affected.append(name)
            elif not target_is_symbolic and not candidate_is_symbolic:
                # Both line-based: use old line number comparison
                candidate_refs = self.parse_code_references(candidate_refs_raw)
                for file_path, (_, candidate_latest) in candidate_refs.items():
                    if file_path in target_refs_dict:
                        target_earliest, _ = target_refs_dict[file_path]
                        if target_earliest <= candidate_latest:
                            affected.append(name)
                            break
            else:
                # Mixed formats: extract file paths and check file-level overlap
                # For symbolic refs, qualify and extract just the file path portion
                if target_is_symbolic:
                    target_files = {parse_reference(qualify_ref(r, local_project))[1] for r in target_refs}
                    candidate_files = set(self.parse_code_references(candidate_refs_raw).keys())
                else:
                    target_files = set(target_refs_dict.keys())
                    candidate_refs = self._extract_symbolic_refs(candidate_refs_raw)
                    candidate_files = {parse_reference(qualify_ref(r, local_project))[1] for r in candidate_refs}

                # Any shared file means potential overlap
                if target_files & candidate_files:
                    affected.append(name)

        return sorted(affected)

    # Chunk: docs/chunks/chunk_validate - Status, code_references, subsystem, investigation, and narrative validation
    # Chunk: docs/chunks/bidirectional_refs - Extended to include subsystem reference validation
    # Chunk: docs/chunks/chunk_frontmatter_model - Uses typed ChunkStatus and frontmatter.code_references
    # Chunk: docs/chunks/task_chunk_validation - Task-context awareness for validation
    # Chunk: docs/chunks/investigation_chunk_refs - Integration of investigation validation into chunk completion
    # Chunk: docs/chunks/chunk_validator_extract - Delegates to chunk_validation module
    def validate_chunk_complete(
        self,
        chunk_id: str | None = None,
        task_dir: pathlib.Path | None = None,
    ) -> ValidationResult:
        """Validate that a chunk is ready for completion.

        Delegates to chunk_validation.validate_chunk_complete().
        """
        return _validate_chunk_complete(self, chunk_id, task_dir)

    # Chunk: docs/chunks/project_artifact_registry - Refactored to accept Project for unified manager access
    def list_proposed_chunks(
        self,
        project: "Project",
    ) -> list[dict]:
        """List all proposed chunks across investigations, narratives, and subsystems.

        Args:
            project: Project instance providing access to all artifact managers.

        Returns:
            List of dicts with keys: prompt, chunk_directory, source_type, source_id
            Filtered to entries where chunk_directory is None (not yet created).
        """
        # Import Project inside method to avoid circular import
        # (Chunks is imported by Project)
        from project import Project

        results: list[dict] = []

        # Collect from investigations
        for inv_id in project.investigations.enumerate_investigations():
            frontmatter = project.investigations.parse_investigation_frontmatter(inv_id)
            if frontmatter is None:
                continue
            for proposed in frontmatter.proposed_chunks:
                # Only include if chunk hasn't been created yet
                if not proposed.chunk_directory:
                    results.append({
                        "prompt": proposed.prompt,
                        "chunk_directory": proposed.chunk_directory,
                        "source_type": "investigation",
                        "source_id": inv_id,
                    })

        # Collect from narratives
        for narr_id in project.narratives.enumerate_narratives():
            frontmatter = project.narratives.parse_narrative_frontmatter(narr_id)
            if frontmatter is None:
                continue
            for proposed in frontmatter.proposed_chunks:
                # Only include if chunk hasn't been created yet
                if not proposed.chunk_directory:
                    results.append({
                        "prompt": proposed.prompt,
                        "chunk_directory": proposed.chunk_directory,
                        "source_type": "narrative",
                        "source_id": narr_id,
                    })

        # Collect from subsystems
        for sub_id in project.subsystems.enumerate_subsystems():
            frontmatter = project.subsystems.parse_subsystem_frontmatter(sub_id)
            if frontmatter is None:
                continue
            for proposed in frontmatter.proposed_chunks:
                # Only include if chunk hasn't been created yet
                if not proposed.chunk_directory:
                    results.append({
                        "prompt": proposed.prompt,
                        "chunk_directory": proposed.chunk_directory,
                        "source_type": "subsystem",
                        "source_id": sub_id,
                    })

        return results

    def get_status(self, chunk_id: str) -> ChunkStatus:
        """Get the current status of a chunk.

        Overrides base class to support chunk ID resolution (4-digit prefix,
        short name, or exact match).

        Args:
            chunk_id: The chunk ID to get status for.

        Returns:
            The current ChunkStatus.

        Raises:
            ValueError: If chunk not found or has invalid frontmatter.
        """
        chunk_name = self.resolve_chunk_id(chunk_id)
        if chunk_name is None:
            raise ValueError(f"Chunk '{chunk_id}' not found in docs/chunks/")

        frontmatter = self.parse_chunk_frontmatter(chunk_name)
        if frontmatter is None:
            raise ValueError(f"Chunk '{chunk_id}' has invalid frontmatter")

        return frontmatter.status

    def update_status(
        self, chunk_id: str, new_status: ChunkStatus
    ) -> tuple[ChunkStatus, ChunkStatus]:
        """Update chunk status with transition validation.

        Overrides base class to support chunk ID resolution and use
        get_chunk_goal_path for file updates.

        Args:
            chunk_id: The chunk ID to update.
            new_status: The new status to transition to.

        Returns:
            Tuple of (old_status, new_status) on success.

        Raises:
            ValueError: If chunk not found, invalid status, or invalid transition.
        """
        from frontmatter import update_frontmatter_field

        # Get current status (uses resolve_chunk_id internally)
        current_status = self.get_status(chunk_id)

        # Validate the transition using StateMachine from base class
        sm = self._get_state_machine()
        sm.validate_transition(current_status, new_status)

        # Update the frontmatter
        goal_path = self.get_chunk_goal_path(chunk_id)
        update_frontmatter_field(goal_path, "status", new_status.value)

        return (current_status, new_status)

    # Chunk: docs/chunks/bidirectional_refs - Validates subsystem references in chunk frontmatter exist
    # Chunk: docs/chunks/chunks_decompose - Thin wrapper delegating to integrity.validate_chunk_subsystem_refs
    def validate_subsystem_refs(self, chunk_id: str) -> list[str]:
        """Validate subsystem references in a chunk's frontmatter.

        Delegates to integrity.validate_chunk_subsystem_refs().

        Args:
            chunk_id: The chunk ID to validate.

        Returns:
            List of error messages (empty if all refs valid or no refs).
        """
        from integrity import validate_chunk_subsystem_refs
        return validate_chunk_subsystem_refs(self.project_dir, chunk_id)

    # Chunk: docs/chunks/chunk_validate - Validation that referenced investigations exist
    # Chunk: docs/chunks/chunks_decompose - Thin wrapper delegating to integrity.validate_chunk_investigation_ref
    def validate_investigation_ref(self, chunk_id: str) -> list[str]:
        """Validate investigation reference in a chunk's frontmatter.

        Delegates to integrity.validate_chunk_investigation_ref().

        Args:
            chunk_id: The chunk ID to validate.

        Returns:
            List of error messages (empty if valid or no reference).
        """
        from integrity import validate_chunk_investigation_ref
        return validate_chunk_investigation_ref(self.project_dir, chunk_id)

    # Chunk: docs/chunks/chunk_validate - Validation that referenced narratives exist
    # Chunk: docs/chunks/chunks_decompose - Thin wrapper delegating to integrity.validate_chunk_narrative_ref
    def validate_narrative_ref(self, chunk_id: str) -> list[str]:
        """Validate narrative reference in a chunk's frontmatter.

        Delegates to integrity.validate_chunk_narrative_ref().

        Args:
            chunk_id: The chunk ID to validate.

        Returns:
            List of error messages (empty if valid or no reference).
        """
        from integrity import validate_chunk_narrative_ref
        return validate_chunk_narrative_ref(self.project_dir, chunk_id)

    # Chunk: docs/chunks/chunks_decompose - Thin wrapper delegating to integrity.validate_chunk_friction_entries_ref
    # Chunk: docs/chunks/friction_chunk_linking - Validation method checking friction entry references exist in FRICTION.md
    def validate_friction_entries_ref(self, chunk_id: str) -> list[str]:
        """Validate friction entry references in a chunk's frontmatter.

        Delegates to integrity.validate_chunk_friction_entries_ref().

        Args:
            chunk_id: The chunk ID to validate.

        Returns:
            List of error messages (empty if valid or no references).
        """
        from integrity import validate_chunk_friction_entries_ref
        return validate_chunk_friction_entries_ref(self.project_dir, chunk_id)

    # Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
    # Chunk: docs/chunks/orch_inject_validate - Injection-time chunk validation
    # Chunk: docs/chunks/chunk_validator_extract - Delegates to chunk_validation module
    def validate_chunk_injectable(self, chunk_id: str) -> ValidationResult:
        """Validate that a chunk is ready for injection into the orchestrator work pool.

        Delegates to chunk_validation.validate_chunk_injectable().
        """
        return _validate_chunk_injectable(self, chunk_id)


# Chunk: docs/chunks/symbolic_code_refs - Overlap detection using symbolic references
def compute_symbolic_overlap(refs_a: list[str], refs_b: list[str], project: str) -> bool:
    """Determine if two lists of symbolic references have any overlap.

    Overlap occurs when any reference in refs_a is a parent of, child of,
    or equal to any reference in refs_b.

    Args:
        refs_a: List of symbolic reference strings.
        refs_b: List of symbolic reference strings.
        project: Project context for qualifying non-qualified refs.

    Returns:
        True if any overlap exists, False otherwise.
    """
    if not refs_a or not refs_b:
        return False

    for ref_a in refs_a:
        for ref_b in refs_b:
            # Qualify refs and check both directions since is_parent_of is not symmetric
            qualified_a = qualify_ref(ref_a, project)
            qualified_b = qualify_ref(ref_b, project)
            if is_parent_of(qualified_a, qualified_b) or is_parent_of(qualified_b, qualified_a):
                return True
    return False


# Chunk: docs/chunks/cluster_prefix_suggest - Extract text content from GOAL.md
def extract_goal_text(goal_path: pathlib.Path) -> str:
    """Extract text content from GOAL.md, skipping frontmatter and HTML comments.

    Args:
        goal_path: Path to the GOAL.md file.

    Returns:
        Extracted text content, stripped of frontmatter and comments.
    """
    if not goal_path.exists():
        return ""

    content = goal_path.read_text()

    # Remove YAML frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2]

    # Remove HTML comments
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)

    return content.strip()


# Chunk: docs/chunks/cluster_prefix_suggest - Get alphabetical prefix (first word before underscore)
def get_chunk_prefix(chunk_name: str) -> str:
    """Get alphabetical prefix (first word before underscore).

    Args:
        chunk_name: The chunk directory name.

    Returns:
        The first underscore-delimited word, or the full name if no underscore.
    """
    return chunk_name.split("_")[0]
