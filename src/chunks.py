"""Chunks module - business logic for chunk management."""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Subsystem: docs/subsystems/cluster_analysis - Chunk naming and clustering

from __future__ import annotations

from dataclasses import dataclass, field
import pathlib
import re
from typing import TYPE_CHECKING

from pydantic import ValidationError
import yaml

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
    extract_short_name,
)
from symbols import is_parent_of, parse_reference, extract_symbols, qualify_ref
from template_system import ActiveChunk, TemplateContext, render_to_directory

if TYPE_CHECKING:
    from investigations import Investigations
    from narratives import Narratives
    from subsystems import Subsystems


@dataclass
class ValidationResult:
    """Result of chunk completion validation."""

    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    chunk_name: str | None = None


@dataclass
class SuggestPrefixResult:
    """Result of prefix suggestion analysis."""

    suggested_prefix: str | None
    similar_chunks: list[tuple[str, float]]  # (chunk_name, similarity_score)
    reason: str


# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
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
class Chunks:
    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.chunk_dir = project_dir / "docs" / "chunks"
        self.chunk_dir.mkdir(parents=True, exist_ok=True)

    def enumerate_chunks(self):
        return [f.name for f in self.chunk_dir.iterdir() if f.is_dir()]

    @property
    def num_chunks(self):
        return len(self.enumerate_chunks())

    def find_duplicates(self, short_name: str, ticket_id: str | None) -> list[str]:
        """Find existing chunks with the same short_name.

        Detects collisions by extracting the short_name from existing directory
        names (handling both legacy {NNNN}-{name} and new {name} formats).

        Args:
            short_name: The short name to check for collisions.
            ticket_id: Optional ticket ID (kept for backward compatibility but
                       not used - ticket_id no longer affects directory names).

        Returns:
            List of existing chunk directory names that would collide.
        """
        # Match on short_name only - ticket_id is stored in frontmatter, not directory name
        target_short = short_name

        duplicates = []
        for name in self.enumerate_chunks():
            # Extract short_name from existing directory (handles both patterns)
            existing_short = extract_short_name(name)
            if existing_short == target_short:
                duplicates.append(name)
        return duplicates

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

    def get_latest_chunk(self) -> str | None:
        """Return the first chunk in causal order (newest).

        Returns:
            The chunk directory name if chunks exist, None otherwise.
        """
        chunks = self.list_chunks()
        if chunks:
            return chunks[0]
        return None

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
        from task_utils import update_frontmatter_field

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

    def resolve_chunk_id(self, chunk_id: str) -> str | None:
        """Resolve a chunk ID to its directory name.

        Supports multiple resolution strategies:
        1. Exact match (returns the directory name as-is)
        2. Legacy prefix match (e.g., "0003" matches "0003-feature")
        3. Short name match (e.g., "feature" matches either "0003-feature" or "feature")

        Returns:
            The full chunk directory name, or None if not found.
        """
        chunks = self.enumerate_chunks()
        # Exact match
        if chunk_id in chunks:
            return chunk_id
        # Legacy prefix match (e.g., "0003" matches "0003-feature")
        for name in chunks:
            if name.startswith(f"{chunk_id}-"):
                return name
        # Short name match (find by extracted short_name)
        for name in chunks:
            if extract_short_name(name) == chunk_id:
                return name
        return None

    def get_chunk_goal_path(self, chunk_id: str) -> pathlib.Path | None:
        """Resolve chunk ID to GOAL.md path.

        Returns:
            Path to GOAL.md, or None if chunk not found.
        """
        chunk_name = self.resolve_chunk_id(chunk_id)
        if chunk_name is None:
            return None
        return self.chunk_dir / chunk_name / "GOAL.md"

    def parse_chunk_frontmatter(self, chunk_id: str) -> ChunkFrontmatter | None:
        """Parse YAML frontmatter from a chunk's GOAL.md.

        Returns:
            ChunkFrontmatter if valid, or None if chunk not found or frontmatter invalid.
        """
        frontmatter, _ = self.parse_chunk_frontmatter_with_errors(chunk_id)
        return frontmatter

    def parse_chunk_frontmatter_with_errors(
        self, chunk_id: str
    ) -> tuple[ChunkFrontmatter | None, list[str]]:
        """Parse YAML frontmatter from a chunk's GOAL.md with error details.

        Returns:
            Tuple of (ChunkFrontmatter, errors) where:
            - ChunkFrontmatter is the parsed frontmatter if valid, None otherwise
            - errors is a list of error messages (empty if parsing succeeded)
        """
        goal_path = self.get_chunk_goal_path(chunk_id)
        if goal_path is None or not goal_path.exists():
            return None, [f"Chunk '{chunk_id}' not found"]

        content = goal_path.read_text()
        # Extract frontmatter between --- markers
        match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not match:
            return None, ["GOAL.md missing frontmatter (no --- markers found)"]

        try:
            frontmatter = yaml.safe_load(match.group(1))
            if not isinstance(frontmatter, dict):
                return None, ["Frontmatter is not a valid YAML mapping"]
            return ChunkFrontmatter.model_validate(frontmatter), []
        except yaml.YAMLError as e:
            return None, [f"YAML parsing error: {e}"]
        except ValidationError as e:
            # Extract user-friendly error messages from Pydantic validation
            errors = []
            for error in e.errors():
                loc = ".".join(str(x) for x in error["loc"])
                msg = error["msg"]
                errors.append(f"{loc}: {msg}")
            return None, errors

    def _parse_frontmatter_from_content(self, content: str) -> ChunkFrontmatter | None:
        """Parse YAML frontmatter from GOAL.md content string.

        Used for cache-based resolution where we have content but not a file path.

        Args:
            content: Full GOAL.md content including frontmatter

        Returns:
            ChunkFrontmatter if valid, or None if frontmatter invalid.
        """
        # Extract frontmatter between --- markers
        match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not match:
            return None

        try:
            frontmatter = yaml.safe_load(match.group(1))
            if not isinstance(frontmatter, dict):
                return None
            return ChunkFrontmatter.model_validate(frontmatter)
        except (yaml.YAMLError, ValidationError):
            return None

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

    def validate_chunk_complete(
        self,
        chunk_id: str | None = None,
        task_dir: pathlib.Path | None = None,
    ) -> ValidationResult:
        """Validate that a chunk is ready for completion.

        Checks:
        1. Chunk exists (resolves external chunks via task context if available)
        2. Status is IMPLEMENTING or ACTIVE
        3. code_references conforms to schema and is non-empty
        4. (For symbolic refs) Referenced symbols exist (produces warnings, not errors)
        5. Subsystem references are valid and exist

        Supports both old line-based format and new symbolic format.
        Also supports cross-project code references when run in task context.

        Args:
            chunk_id: The chunk ID to validate. Defaults to latest chunk.
            task_dir: Optional task directory for resolving external chunks
                      and cross-project code references.

        Returns:
            ValidationResult with success status, errors, and warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Resolve chunk_id
        if chunk_id is None:
            chunk_id = self.get_latest_chunk()
            if chunk_id is None:
                return ValidationResult(
                    success=False,
                    errors=["No chunks found"],
                )

        # Use resolve_chunk_location to handle external chunks
        location = self.resolve_chunk_location(chunk_id, task_dir)

        if location is None:
            return ValidationResult(
                success=False,
                errors=[f"Chunk '{chunk_id}' not found"],
            )

        # Handle cache-based resolution (external chunk without task context)
        if location.cached_content is not None:
            # Parse frontmatter from cached content
            frontmatter = self._parse_frontmatter_from_content(location.cached_content)
            if frontmatter is None:
                return ValidationResult(
                    success=False,
                    errors=[f"Could not parse frontmatter for chunk '{chunk_id}'"],
                    chunk_name=location.chunk_name,
                )

            # Check status
            valid_statuses = (ChunkStatus.IMPLEMENTING, ChunkStatus.ACTIVE)
            if frontmatter.status not in valid_statuses:
                errors.append(
                    f"Status is '{frontmatter.status.value}', must be 'IMPLEMENTING' or 'ACTIVE' to complete"
                )

            # Check code_references non-empty
            if not frontmatter.code_references:
                errors.append(
                    "code_references is empty; at least one reference is required"
                )
            else:
                # Note: Code reference validation is skipped for cache-based resolution
                # since we don't have filesystem access to the code repository
                warnings.append(
                    f"Code reference validation skipped (resolved from cache at {location.cached_sha[:8]})"
                )

            # Note: Subsystem and investigation validation skipped for cache-based resolution
            return ValidationResult(
                success=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                chunk_name=location.chunk_name,
            )

        # For external chunks with task context, create a temporary Chunks instance
        if location.is_external:
            validation_chunks = Chunks(location.project_dir)
            chunk_name_to_validate = location.chunk_name
        else:
            validation_chunks = self
            # Fall back to resolve_chunk_id for local chunks (handles short names)
            chunk_name_to_validate = self.resolve_chunk_id(chunk_id)
            if chunk_name_to_validate is None:
                return ValidationResult(
                    success=False,
                    errors=[f"Chunk '{chunk_id}' not found"],
                )

        # Parse frontmatter from the resolved chunk location with error details
        frontmatter, parse_errors = validation_chunks.parse_chunk_frontmatter_with_errors(
            chunk_name_to_validate
        )
        if frontmatter is None:
            # Include specific parsing errors instead of generic message
            error_detail = "; ".join(parse_errors) if parse_errors else "unknown error"
            return ValidationResult(
                success=False,
                errors=[f"Could not parse frontmatter for chunk '{chunk_id}': {error_detail}"],
                chunk_name=chunk_name_to_validate,
            )

        # Check status
        valid_statuses = (ChunkStatus.IMPLEMENTING, ChunkStatus.ACTIVE)
        if frontmatter.status not in valid_statuses:
            errors.append(
                f"Status is '{frontmatter.status.value}', must be 'IMPLEMENTING' or 'ACTIVE' to complete"
            )

        # Validate code_references - already validated by ChunkFrontmatter model
        # Just need to check non-empty and validate symbol existence for warnings
        if not frontmatter.code_references:
            errors.append(
                "code_references is empty; at least one reference is required"
            )
        else:
            # Validate that referenced symbols exist (produces warnings, not errors)
            # Use the validation_chunks instance for proper project context
            for ref in frontmatter.code_references:
                symbol_warnings = validation_chunks._validate_symbol_exists_with_context(
                    ref.ref,
                    task_dir=task_dir,
                    chunk_project=location.project_dir,
                )
                warnings.extend(symbol_warnings)

        # Validate subsystem references
        subsystem_errors = validation_chunks.validate_subsystem_refs(chunk_name_to_validate)
        errors.extend(subsystem_errors)

        investigation_errors = validation_chunks.validate_investigation_ref(chunk_name_to_validate)
        errors.extend(investigation_errors)

        narrative_errors = validation_chunks.validate_narrative_ref(chunk_name_to_validate)
        errors.extend(narrative_errors)

        # Subsystem: docs/subsystems/friction_tracking - Friction log management
        friction_errors = validation_chunks.validate_friction_entries_ref(chunk_name_to_validate)
        errors.extend(friction_errors)

        return ValidationResult(
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            chunk_name=chunk_name_to_validate,
        )

    def _validate_symbol_exists(self, ref: str) -> list[str]:
        """Validate that a symbolic reference points to an existing symbol.

        Args:
            ref: Symbolic reference string (e.g., "src/foo.py#Bar::baz")

        Returns:
            List of warning messages (empty if valid).
        """
        # Qualify the ref with local project context before parsing
        qualified_ref = qualify_ref(ref, ".")
        _, file_path, symbol_path = parse_reference(qualified_ref)

        # Check if file exists
        full_path = self.project_dir / file_path
        if not full_path.exists():
            return [f"Warning: File not found: {file_path} (ref: {ref})"]

        # If no symbol path, just check file exists (which we did above)
        if symbol_path is None:
            return []

        # Extract symbols from file and check if referenced symbol exists
        symbols = extract_symbols(full_path)
        if not symbols:
            # Could be syntax error or non-Python file
            if str(file_path).endswith(".py"):
                return [f"Warning: Could not extract symbols from {file_path} (ref: {ref})"]
            # Non-Python files can't have symbol validation
            return []

        if symbol_path not in symbols:
            return [f"Warning: Symbol not found: {symbol_path} in {file_path} (ref: {ref})"]

        return []

    def _validate_symbol_exists_with_context(
        self,
        ref: str,
        task_dir: pathlib.Path | None = None,
        chunk_project: pathlib.Path | None = None,
    ) -> list[str]:
        """Validate a symbolic reference with task context for cross-project refs.

        For non-qualified references (no project::), validates against chunk_project.
        For project-qualified references (project::file), resolves the project
        via task context and validates against that project.

        Args:
            ref: Symbolic reference string (may be project-qualified).
            task_dir: Optional task directory for resolving cross-project refs.
            chunk_project: Project directory where the chunk lives (default: self.project_dir).

        Returns:
            List of warning messages (empty if valid).
        """
        # Check if this is a project-qualified reference
        hash_pos = ref.find("#")
        check_portion = ref[:hash_pos] if hash_pos != -1 else ref
        is_cross_project = "::" in check_portion

        if is_cross_project:
            # Parse the project qualifier
            double_colon_pos = check_portion.find("::")
            project_ref = ref[:double_colon_pos]
            remaining = ref[double_colon_pos + 2:]

            # Without task context, we can't resolve cross-project refs
            if task_dir is None:
                return [
                    f"Skipped cross-project reference: {ref} (no task context)"
                ]

            # Resolve the project path
            from task_utils import load_task_config, resolve_repo_directory

            try:
                config = load_task_config(task_dir)
                project_path = resolve_repo_directory(task_dir, project_ref)
            except (FileNotFoundError, ValueError) as e:
                return [f"Warning: Could not resolve project '{project_ref}': {e} (ref: {ref})"]

            # Parse the file and symbol from remaining
            if "#" in remaining:
                file_path, symbol_path = remaining.split("#", 1)
            else:
                file_path = remaining
                symbol_path = None

            # Validate against the resolved project
            full_path = project_path / file_path
            if not full_path.exists():
                return [f"Warning: File not found: {file_path} in project {project_ref} (ref: {ref})"]

            if symbol_path is None:
                return []

            symbols = extract_symbols(full_path)
            if not symbols:
                if str(file_path).endswith(".py"):
                    return [f"Warning: Could not extract symbols from {file_path} in project {project_ref} (ref: {ref})"]
                return []

            if symbol_path not in symbols:
                return [f"Warning: Symbol not found: {symbol_path} in {file_path} (project: {project_ref}) (ref: {ref})"]

            return []
        else:
            # Non-qualified reference - validate against chunk's project
            project_dir = chunk_project if chunk_project else self.project_dir

            # Use local project context
            qualified_ref = qualify_ref(ref, ".")
            _, file_path, symbol_path = parse_reference(qualified_ref)

            full_path = project_dir / file_path
            if not full_path.exists():
                return [f"Warning: File not found: {file_path} (ref: {ref})"]

            if symbol_path is None:
                return []

            symbols = extract_symbols(full_path)
            if not symbols:
                if str(file_path).endswith(".py"):
                    return [f"Warning: Could not extract symbols from {file_path} (ref: {ref})"]
                return []

            if symbol_path not in symbols:
                return [f"Warning: Symbol not found: {symbol_path} in {file_path} (ref: {ref})"]

            return []

    def list_proposed_chunks(
        self,
        investigations: Investigations,
        narratives: Narratives,
        subsystems: Subsystems,
    ) -> list[dict]:
        """List all proposed chunks across investigations, narratives, and subsystems.

        Args:
            investigations: Investigations instance for parsing investigation frontmatter.
            narratives: Narratives instance for parsing narrative frontmatter.
            subsystems: Subsystems instance for parsing subsystem frontmatter.

        Returns:
            List of dicts with keys: prompt, chunk_directory, source_type, source_id
            Filtered to entries where chunk_directory is None (not yet created).
        """
        results: list[dict] = []

        # Collect from investigations
        for inv_id in investigations.enumerate_investigations():
            frontmatter = investigations.parse_investigation_frontmatter(inv_id)
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
        for narr_id in narratives.enumerate_narratives():
            frontmatter = narratives.parse_narrative_frontmatter(narr_id)
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
        for sub_id in subsystems.enumerate_subsystems():
            frontmatter = subsystems.parse_subsystem_frontmatter(sub_id)
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

        Args:
            chunk_id: The chunk ID to update.
            new_status: The new status to transition to.

        Returns:
            Tuple of (old_status, new_status) on success.

        Raises:
            ValueError: If chunk not found, invalid status, or invalid transition.
        """
        from task_utils import update_frontmatter_field
        from models import VALID_CHUNK_TRANSITIONS

        # Get current status
        current_status = self.get_status(chunk_id)

        # Validate the transition
        valid_transitions = VALID_CHUNK_TRANSITIONS.get(current_status, set())
        if new_status not in valid_transitions:
            valid_names = sorted(s.value for s in valid_transitions)
            if valid_names:
                valid_str = ", ".join(valid_names)
                raise ValueError(
                    f"Cannot transition from {current_status.value} to {new_status.value}. "
                    f"Valid transitions: {valid_str}"
                )
            else:
                raise ValueError(
                    f"Cannot transition from {current_status.value} to {new_status.value}. "
                    f"{current_status.value} is a terminal state with no valid transitions"
                )

        # Update the frontmatter
        goal_path = self.get_chunk_goal_path(chunk_id)
        update_frontmatter_field(goal_path, "status", new_status.value)

        return (current_status, new_status)

    def validate_subsystem_refs(self, chunk_id: str) -> list[str]:
        """Validate subsystem references in a chunk's frontmatter.

        Checks:
        1. Each subsystem_id matches the {NNNN}-{short_name} pattern
        2. Each referenced subsystem directory exists in docs/subsystems/

        Args:
            chunk_id: The chunk ID to validate.

        Returns:
            List of error messages (empty if all refs valid or no refs).
        """
        errors: list[str] = []

        # Get chunk frontmatter
        frontmatter = self.parse_chunk_frontmatter(chunk_id)
        if frontmatter is None:
            return []  # Chunk doesn't exist, nothing to validate

        # Get subsystems field (already validated by ChunkFrontmatter model)
        if not frontmatter.subsystems:
            return []

        # Subsystems directory path
        subsystems_dir = self.project_dir / "docs" / "subsystems"

        for entry in frontmatter.subsystems:
            # Check if subsystem directory exists
            subsystem_path = subsystems_dir / entry.subsystem_id
            if not subsystem_path.exists():
                errors.append(
                    f"Subsystem '{entry.subsystem_id}' does not exist in docs/subsystems/"
                )

        return errors

    def validate_investigation_ref(self, chunk_id: str) -> list[str]:
        """Validate investigation reference in a chunk's frontmatter.

        Checks:
        1. If investigation field is populated, the referenced investigation
           directory exists in docs/investigations/

        Args:
            chunk_id: The chunk ID to validate.

        Returns:
            List of error messages (empty if valid or no reference).
        """
        errors: list[str] = []

        # Get chunk frontmatter
        frontmatter = self.parse_chunk_frontmatter(chunk_id)
        if frontmatter is None:
            return []  # Chunk doesn't exist, nothing to validate

        # Get investigation field (already validated by ChunkFrontmatter model)
        if not frontmatter.investigation:
            return []

        # Investigations directory path
        investigations_dir = self.project_dir / "docs" / "investigations"

        # Check if investigation directory exists
        investigation_path = investigations_dir / frontmatter.investigation
        if not investigation_path.exists():
            errors.append(
                f"Investigation '{frontmatter.investigation}' does not exist in docs/investigations/"
            )

        return errors

    def validate_narrative_ref(self, chunk_id: str) -> list[str]:
        """Validate narrative reference in a chunk's frontmatter.

        Checks:
        1. If narrative field is populated, the referenced narrative
           directory exists in docs/narratives/

        Args:
            chunk_id: The chunk ID to validate.

        Returns:
            List of error messages (empty if valid or no reference).
        """
        errors: list[str] = []

        # Get chunk frontmatter
        frontmatter = self.parse_chunk_frontmatter(chunk_id)
        if frontmatter is None:
            return []  # Chunk doesn't exist, nothing to validate

        # Get narrative field (already validated by ChunkFrontmatter model)
        if not frontmatter.narrative:
            return []

        # Narratives directory path
        narratives_dir = self.project_dir / "docs" / "narratives"

        # Check if narrative directory exists
        narrative_path = narratives_dir / frontmatter.narrative
        if not narrative_path.exists():
            errors.append(
                f"Narrative '{frontmatter.narrative}' does not exist in docs/narratives/"
            )

        return errors

    def validate_friction_entries_ref(self, chunk_id: str) -> list[str]:
        """Validate friction entry references in a chunk's frontmatter.

        Checks that each referenced friction entry ID exists in FRICTION.md.
        If friction_entries is empty, validation passes (optional field).

        Args:
            chunk_id: The chunk ID to validate.

        Returns:
            List of error messages (empty if valid or no references).
        """
        from friction import Friction

        errors: list[str] = []

        # Get chunk frontmatter
        frontmatter = self.parse_chunk_frontmatter(chunk_id)
        if frontmatter is None:
            return []  # Chunk doesn't exist, nothing to validate

        # Get friction_entries field (already validated by ChunkFrontmatter model)
        if not frontmatter.friction_entries:
            return []

        # Parse friction log to get existing entry IDs
        friction = Friction(self.project_dir)
        if not friction.exists():
            errors.append(
                f"Friction log does not exist at docs/trunk/FRICTION.md but chunk "
                f"references friction entries: {[e.entry_id for e in frontmatter.friction_entries]}"
            )
            return errors

        # Get all existing friction entry IDs
        existing_entries = friction.parse_entries()
        existing_entry_ids = {entry.id for entry in existing_entries}

        # Validate each referenced entry exists
        for entry_ref in frontmatter.friction_entries:
            if entry_ref.entry_id not in existing_entry_ids:
                errors.append(
                    f"Friction entry '{entry_ref.entry_id}' does not exist in docs/trunk/FRICTION.md"
                )

        return errors

    # Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
    def validate_chunk_injectable(self, chunk_id: str) -> ValidationResult:
        """Validate that a chunk is ready for injection into the orchestrator work pool.

        This validation is called before creating a work unit. It checks:
        1. Chunk exists
        2. Status-content consistency:
           - IMPLEMENTING/ACTIVE status requires populated PLAN.md (not just template)
           - FUTURE status is allowed to have empty PLAN.md (it hasn't been planned yet)

        Args:
            chunk_id: The chunk ID to validate.

        Returns:
            ValidationResult with success status, errors, and warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Resolve chunk_id
        chunk_name = self.resolve_chunk_id(chunk_id)
        if chunk_name is None:
            return ValidationResult(
                success=False,
                errors=[f"Chunk '{chunk_id}' not found"],
            )

        # Parse frontmatter
        frontmatter = self.parse_chunk_frontmatter(chunk_name)
        if frontmatter is None:
            return ValidationResult(
                success=False,
                errors=[f"Could not parse frontmatter for chunk '{chunk_id}'"],
                chunk_name=chunk_name,
            )

        # Get PLAN.md path
        plan_path = self.chunk_dir / chunk_name / "PLAN.md"

        # Check status-content consistency
        if frontmatter.status in (ChunkStatus.IMPLEMENTING, ChunkStatus.ACTIVE):
            # IMPLEMENTING/ACTIVE chunks must have populated PLAN.md
            if not plan_path.exists():
                errors.append(
                    f"Chunk has status '{frontmatter.status.value}' but PLAN.md does not exist. "
                    f"Run /chunk-plan first or change status to FUTURE."
                )
            elif not plan_has_content(plan_path):
                errors.append(
                    f"Chunk has status '{frontmatter.status.value}' but PLAN.md has no content "
                    f"(only template). Run /chunk-plan to populate the plan or change status to FUTURE."
                )
        elif frontmatter.status == ChunkStatus.FUTURE:
            # FUTURE chunks are allowed to have empty PLAN.md - that's expected
            if not plan_path.exists() or not plan_has_content(plan_path):
                warnings.append(
                    f"Chunk has status 'FUTURE' with empty plan. "
                    f"Will start with PLAN phase to populate the plan."
                )
        elif frontmatter.status in (ChunkStatus.SUPERSEDED, ChunkStatus.HISTORICAL):
            # Terminal states - shouldn't be injected
            errors.append(
                f"Chunk has terminal status '{frontmatter.status.value}' and cannot be injected. "
                f"Only FUTURE, IMPLEMENTING, or ACTIVE chunks can be injected."
            )

        return ValidationResult(
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            chunk_name=chunk_name,
        )


def plan_has_content(plan_path: pathlib.Path) -> bool:
    """Check if PLAN.md has actual content beyond the template.

    Looks for content in the '## Approach' section that isn't just the
    template's HTML comment block.

    Args:
        plan_path: Path to the PLAN.md file

    Returns:
        True if the plan has actual content, False if it's just a template
    """
    try:
        content = plan_path.read_text()
    except Exception:
        return False

    # Look for the Approach section
    approach_match = re.search(
        r"## Approach\s*\n(.*?)(?=\n## |\Z)",
        content,
        re.DOTALL
    )

    if not approach_match:
        return False

    approach_content = approach_match.group(1).strip()

    # If the approach section is empty or only contains HTML comments, it's a template
    # Remove HTML comments and see what's left
    content_without_comments = re.sub(r"<!--.*?-->", "", approach_content, flags=re.DOTALL)
    content_without_comments = content_without_comments.strip()

    # If there's meaningful content after removing comments, the plan is populated
    return len(content_without_comments) > 0


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


@dataclass
class BackreferenceInfo:
    """Information about backreferences in a source file."""

    file_path: pathlib.Path
    chunk_refs: list[str]  # List of chunk IDs referenced
    narrative_refs: list[str]  # List of narrative IDs referenced
    subsystem_refs: list[str]  # List of subsystem IDs referenced

    @property
    def unique_chunk_count(self) -> int:
        """Count of unique chunk references."""
        return len(set(self.chunk_refs))

    @property
    def total_chunk_count(self) -> int:
        """Total count of chunk references (including duplicates)."""
        return len(self.chunk_refs)


CHUNK_BACKREF_PATTERN = re.compile(r"^#\s+Chunk:\s+docs/chunks/([a-z0-9_-]+)", re.MULTILINE)
NARRATIVE_BACKREF_PATTERN = re.compile(r"^#\s+Narrative:\s+docs/narratives/([a-z0-9_-]+)", re.MULTILINE)
SUBSYSTEM_BACKREF_PATTERN = re.compile(r"^#\s+Subsystem:\s+docs/subsystems/([a-z0-9_-]+)", re.MULTILINE)


def count_backreferences(
    project_dir: pathlib.Path,
    source_patterns: list[str] | None = None,
) -> list[BackreferenceInfo]:
    """Scan source files for backreference comments.

    Finds all `# Chunk:`, `# Narrative:`, and `# Subsystem:` comments
    in source files and returns counts per file.

    Args:
        project_dir: Path to the project directory.
        source_patterns: List of glob patterns to search (default: ["src/**/*.py"]).

    Returns:
        List of BackreferenceInfo for files containing backreferences.
    """
    if source_patterns is None:
        source_patterns = ["src/**/*.py"]

    results: list[BackreferenceInfo] = []

    for pattern in source_patterns:
        for file_path in project_dir.glob(pattern):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text()
            except Exception:
                continue

            # Extract all backreferences
            chunk_refs = CHUNK_BACKREF_PATTERN.findall(content)
            narrative_refs = NARRATIVE_BACKREF_PATTERN.findall(content)
            subsystem_refs = SUBSYSTEM_BACKREF_PATTERN.findall(content)

            # Only include files with at least one chunk reference
            if chunk_refs:
                results.append(BackreferenceInfo(
                    file_path=file_path,
                    chunk_refs=chunk_refs,
                    narrative_refs=narrative_refs,
                    subsystem_refs=subsystem_refs,
                ))

    # Sort by unique chunk count descending
    results.sort(key=lambda r: r.unique_chunk_count, reverse=True)

    return results


@dataclass
class ConsolidationResult:
    """Result of chunk consolidation into a narrative."""

    narrative_id: str  # Created narrative directory name
    chunks_updated: list[str]  # Chunk IDs whose frontmatter was updated
    files_to_update: dict[str, tuple[list[str], str]]  # file -> (old_chunk_ids, new_narrative_ref)


@dataclass
class ClusterResult:
    """Result of chunk clustering analysis."""

    clusters: list[list[str]]  # Groups of related chunk IDs
    unclustered: list[str]  # Chunks that don't fit clusters
    cluster_themes: list[str]  # Inferred theme for each cluster


def cluster_chunks(
    project_dir: pathlib.Path,
    chunk_ids: list[str] | None = None,
    min_similarity: float = 0.3,
    min_cluster_size: int = 2,
) -> ClusterResult:
    """Cluster chunks by content similarity using TF-IDF.

    Groups related chunks for potential consolidation into narratives.
    Uses agglomerative clustering with cosine similarity.

    Args:
        project_dir: Path to the project directory.
        chunk_ids: Specific chunk IDs to cluster (default: all ACTIVE chunks).
        min_similarity: Minimum similarity to cluster together (default: 0.3).
        min_cluster_size: Minimum chunks per cluster (default: 2).

    Returns:
        ClusterResult with clusters, unclustered chunks, and inferred themes.
    """
    from collections import Counter

    from sklearn.cluster import AgglomerativeClustering
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    chunks_manager = Chunks(project_dir)

    # Get chunk IDs to cluster
    if chunk_ids is None:
        # Default: all ACTIVE chunks
        all_chunks = chunks_manager.enumerate_chunks()
        chunk_ids = []
        for chunk_name in all_chunks:
            fm = chunks_manager.parse_chunk_frontmatter(chunk_name)
            if fm and fm.status == ChunkStatus.ACTIVE:
                chunk_ids.append(chunk_name)

    if len(chunk_ids) < min_cluster_size:
        return ClusterResult(
            clusters=[],
            unclustered=chunk_ids,
            cluster_themes=[],
        )

    # Extract text from each chunk's GOAL.md
    texts = []
    valid_chunk_ids = []
    for chunk_id in chunk_ids:
        goal_path = chunks_manager.get_chunk_goal_path(chunk_id)
        if goal_path is None:
            continue
        text = extract_goal_text(goal_path)
        if text.strip():
            texts.append(text)
            valid_chunk_ids.append(chunk_id)

    if len(valid_chunk_ids) < min_cluster_size:
        return ClusterResult(
            clusters=[],
            unclustered=valid_chunk_ids,
            cluster_themes=[],
        )

    # Build TF-IDF vectors
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=500,
        ngram_range=(1, 2),
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        # All documents empty after stop word removal
        return ClusterResult(
            clusters=[],
            unclustered=valid_chunk_ids,
            cluster_themes=[],
        )

    # Compute similarity matrix
    similarity_matrix = cosine_similarity(tfidf_matrix)

    # Convert similarity to distance (1 - similarity)
    # Clip to avoid negative distances due to floating point errors
    distance_matrix = 1 - similarity_matrix
    distance_matrix = distance_matrix.clip(min=0)

    # Agglomerative clustering with distance threshold
    # threshold = 1 - min_similarity (e.g., 0.3 similarity = 0.7 distance)
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=1 - min_similarity,
        metric="precomputed",
        linkage="average",
    )

    labels = clustering.fit_predict(distance_matrix)

    # Group chunks by cluster label
    cluster_groups: dict[int, list[str]] = {}
    for idx, label in enumerate(labels):
        if label not in cluster_groups:
            cluster_groups[label] = []
        cluster_groups[label].append(valid_chunk_ids[idx])

    # Separate into clusters (>= min_cluster_size) and unclustered
    clusters: list[list[str]] = []
    unclustered: list[str] = []

    for label, members in cluster_groups.items():
        if len(members) >= min_cluster_size:
            clusters.append(sorted(members))
        else:
            unclustered.extend(members)

    # Infer themes from common prefixes in each cluster
    cluster_themes: list[str] = []
    for cluster in clusters:
        prefixes = [get_chunk_prefix(name) for name in cluster]
        prefix_counts = Counter(prefixes)
        most_common_prefix, count = prefix_counts.most_common(1)[0]

        if count > len(prefixes) / 2:
            # Majority share a prefix
            cluster_themes.append(f"{most_common_prefix} ({count}/{len(prefixes)} share prefix)")
        else:
            # No dominant prefix, use chunk names
            cluster_themes.append(f"mixed ({len(cluster)} chunks)")

    # Sort clusters by size (largest first)
    sorted_pairs = sorted(zip(clusters, cluster_themes), key=lambda x: -len(x[0]))
    clusters = [c for c, _ in sorted_pairs]
    cluster_themes = [t for _, t in sorted_pairs]

    return ClusterResult(
        clusters=clusters,
        unclustered=sorted(unclustered),
        cluster_themes=cluster_themes,
    )


def consolidate_chunks(
    project_dir: pathlib.Path,
    chunk_ids: list[str],
    narrative_name: str,
    narrative_description: str,
) -> ConsolidationResult:
    """Consolidate multiple chunks into a narrative.

    Creates a new narrative synthesizing the given chunks, updates chunk
    frontmatter to reference the narrative, and returns information needed
    to update code backreferences.

    Args:
        project_dir: Path to the project directory.
        chunk_ids: List of chunk IDs to consolidate.
        narrative_name: Short name for the narrative (e.g., "chunk_lifecycle").
        narrative_description: Human-readable description for the narrative.

    Returns:
        ConsolidationResult with:
        - narrative_id: Created narrative directory name
        - chunks_updated: List of chunk IDs whose frontmatter was updated
        - files_to_update: Dict mapping file paths to (old_refs, new_ref) tuples

    Raises:
        ValueError: If any chunk doesn't exist or isn't ACTIVE.
    """
    from task_utils import update_frontmatter_field

    # Import here to avoid circular import
    from narratives import Narratives

    chunks_manager = Chunks(project_dir)
    narratives = Narratives(project_dir)

    # Validate all chunks exist and are ACTIVE
    for chunk_id in chunk_ids:
        resolved = chunks_manager.resolve_chunk_id(chunk_id)
        if resolved is None:
            raise ValueError(f"Chunk '{chunk_id}' not found")

        fm = chunks_manager.parse_chunk_frontmatter(resolved)
        if fm is None:
            raise ValueError(f"Could not parse frontmatter for chunk '{chunk_id}'")

        if fm.status != ChunkStatus.ACTIVE:
            raise ValueError(
                f"Chunk '{chunk_id}' has status '{fm.status.value}', must be ACTIVE to consolidate"
            )

    # Create the narrative
    narrative_path = narratives.create_narrative(narrative_name)

    # Build proposed_chunks entries for the narrative
    # This links the narrative to the consolidated chunks
    proposed_chunks = []
    for chunk_id in chunk_ids:
        resolved = chunks_manager.resolve_chunk_id(chunk_id)
        proposed_chunks.append({
            "prompt": f"Originally: {chunk_id}",
            "chunk_directory": resolved,
        })

    # Update narrative OVERVIEW.md with consolidated chunks info
    overview_path = narrative_path / "OVERVIEW.md"
    overview_content = overview_path.read_text()

    # Update proposed_chunks in frontmatter
    import yaml as yaml_lib
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", overview_content, re.DOTALL)
    if match:
        frontmatter = yaml_lib.safe_load(match.group(1)) or {}
        frontmatter["proposed_chunks"] = proposed_chunks
        body = match.group(2)
        new_frontmatter = yaml_lib.dump(frontmatter, default_flow_style=False, sort_keys=False)
        overview_path.write_text(f"---\n{new_frontmatter}---\n{body}")

    # Update each chunk's frontmatter with narrative reference
    chunks_updated = []
    for chunk_id in chunk_ids:
        resolved = chunks_manager.resolve_chunk_id(chunk_id)
        goal_path = chunks_manager.get_chunk_goal_path(resolved)
        if goal_path:
            update_frontmatter_field(goal_path, "narrative", narrative_name)
            chunks_updated.append(resolved)

    # Find files that reference these chunks
    files_to_update: dict[str, tuple[list[str], str]] = {}
    backref_results = count_backreferences(project_dir)
    for info in backref_results:
        # Find which chunk refs from this file are being consolidated
        matching_refs = [
            ref for ref in set(info.chunk_refs)
            if ref in chunk_ids or chunks_manager.resolve_chunk_id(ref) in chunks_updated
        ]
        if matching_refs:
            rel_path = str(info.file_path.relative_to(project_dir))
            files_to_update[rel_path] = (
                matching_refs,
                f"# Narrative: docs/narratives/{narrative_name} - {narrative_description}",
            )

    return ConsolidationResult(
        narrative_id=narrative_name,
        chunks_updated=chunks_updated,
        files_to_update=files_to_update,
    )


def update_backreferences(
    project_dir: pathlib.Path,
    file_path: pathlib.Path,
    chunk_ids_to_replace: list[str],
    narrative_id: str,
    narrative_description: str,
    dry_run: bool = False,
) -> int:
    """Replace chunk backreferences with narrative backreference.

    Finds all `# Chunk: docs/chunks/{id}` comments where id is in
    chunk_ids_to_replace and replaces them with a single
    `# Narrative: docs/narratives/{narrative_id} - {description}` comment.

    Args:
        project_dir: Path to the project directory.
        file_path: Path to the source file to update.
        chunk_ids_to_replace: Chunk IDs whose references should be replaced.
        narrative_id: Narrative directory to reference.
        narrative_description: Description for the narrative backreference.
        dry_run: If True, don't modify the file, just return count.

    Returns:
        Number of backreferences replaced.
    """
    if not file_path.exists():
        return 0

    content = file_path.read_text()
    lines = content.split("\n")
    new_lines: list[str] = []
    replaced_count = 0
    narrative_line_added = False

    # Build pattern to match chunk refs we want to replace
    chunk_ids_set = set(chunk_ids_to_replace)

    for line in lines:
        match = CHUNK_BACKREF_PATTERN.match(line)
        if match:
            chunk_id = match.group(1)
            if chunk_id in chunk_ids_set:
                replaced_count += 1
                # Add narrative reference only once
                if not narrative_line_added:
                    new_lines.append(
                        f"# Narrative: docs/narratives/{narrative_id} - {narrative_description}"
                    )
                    narrative_line_added = True
                # Skip this chunk line (don't add to new_lines)
                continue

        new_lines.append(line)

    if not dry_run and replaced_count > 0:
        file_path.write_text("\n".join(new_lines))

    return replaced_count


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


def get_chunk_prefix(chunk_name: str) -> str:
    """Get alphabetical prefix (first word before underscore).

    Args:
        chunk_name: The chunk directory name.

    Returns:
        The first underscore-delimited word, or the full name if no underscore.
    """
    return chunk_name.split("_")[0]


def suggest_prefix(
    project_dir: pathlib.Path,
    chunk_id: str,
    threshold: float = 0.4,
    top_k: int = 5,
) -> SuggestPrefixResult:
    """Suggest a prefix for a chunk based on TF-IDF similarity to existing chunks.

    Context determines corpus:
    - Task directory: aggregates chunks from external repo + all project repos
    - Project directory: uses only local project chunks

    Args:
        project_dir: Path to the project or task directory.
        chunk_id: The chunk ID to analyze.
        threshold: Minimum similarity score to consider (default 0.4).
        top_k: Number of most similar chunks to consider (default 5).

    Returns:
        SuggestPrefixResult containing:
        - suggested_prefix: str or None if no strong suggestion
        - similar_chunks: list of (chunk_name, similarity_score) tuples
        - reason: str explaining why the suggestion was or wasn't made
    """
    from collections import Counter
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from task_utils import is_task_directory, load_task_config, resolve_repo_directory

    project_dir = pathlib.Path(project_dir)

    # Build corpus based on context
    corpus_chunks: list[tuple[str, pathlib.Path]] = []  # (chunk_name, goal_path)

    if is_task_directory(project_dir):
        # Task context: aggregate from external repo + all projects
        config = load_task_config(project_dir)

        # Add chunks from external repo
        try:
            external_path = resolve_repo_directory(project_dir, config.external_artifact_repo)
            external_chunks = Chunks(external_path)
            for name in external_chunks.enumerate_chunks():
                goal_path = external_chunks.get_chunk_goal_path(name)
                if goal_path and goal_path.exists():
                    corpus_chunks.append((name, goal_path))
        except FileNotFoundError:
            pass

        # Add chunks from each project
        for project_ref in config.projects:
            try:
                proj_path = resolve_repo_directory(project_dir, project_ref)
                proj_chunks = Chunks(proj_path)
                for name in proj_chunks.enumerate_chunks():
                    goal_path = proj_chunks.get_chunk_goal_path(name)
                    if goal_path and goal_path.exists():
                        corpus_chunks.append((name, goal_path))
            except FileNotFoundError:
                pass
    else:
        # Project context: use only local chunks
        chunks = Chunks(project_dir)
        for name in chunks.enumerate_chunks():
            goal_path = chunks.get_chunk_goal_path(name)
            if goal_path and goal_path.exists():
                corpus_chunks.append((name, goal_path))

    # Find target chunk in corpus
    target_idx = None
    for i, (name, _) in enumerate(corpus_chunks):
        if name == chunk_id:
            target_idx = i
            break

    if target_idx is None:
        # Try resolving chunk_id
        local_chunks = Chunks(project_dir)
        resolved = local_chunks.resolve_chunk_id(chunk_id)
        if resolved:
            for i, (name, _) in enumerate(corpus_chunks):
                if name == resolved:
                    target_idx = i
                    break

    if target_idx is None:
        return SuggestPrefixResult(
            suggested_prefix=None,
            similar_chunks=[],
            reason=f"Chunk '{chunk_id}' not found in corpus",
        )

    # Check minimum corpus size (need at least 2 other chunks)
    other_count = len(corpus_chunks) - 1
    if other_count < 2:
        return SuggestPrefixResult(
            suggested_prefix=None,
            similar_chunks=[],
            reason=f"Too few chunks for meaningful similarity (need at least 3 total, have {len(corpus_chunks)})",
        )

    # Extract text from all chunks
    texts = []
    for _, goal_path in corpus_chunks:
        text = extract_goal_text(goal_path)
        texts.append(text if text else " ")  # Empty text causes TF-IDF issues

    # Build TF-IDF vectors
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=500,
        ngram_range=(1, 2),
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        # Can happen if all documents are empty after stop word removal
        return SuggestPrefixResult(
            suggested_prefix=None,
            similar_chunks=[],
            reason="Could not build similarity model (insufficient text content)",
        )

    # Compute similarity between target and all others
    target_vec = tfidf_matrix[target_idx]
    similarities = cosine_similarity(target_vec, tfidf_matrix)[0]

    # Find top-k similar chunks (excluding self)
    indexed_sims = []
    for i, sim in enumerate(similarities):
        if i != target_idx:
            indexed_sims.append((i, sim))

    indexed_sims.sort(key=lambda x: -x[1])  # Sort by similarity descending
    top_similar = indexed_sims[:top_k]

    # Filter by threshold
    above_threshold = [(i, sim) for i, sim in top_similar if sim >= threshold]

    if not above_threshold:
        # Return the top similar chunks even if below threshold
        similar_chunks = [(corpus_chunks[i][0], sim) for i, sim in top_similar]
        return SuggestPrefixResult(
            suggested_prefix=None,
            similar_chunks=similar_chunks,
            reason=f"No chunks above similarity threshold ({threshold}). May be a new cluster seed.",
        )

    # Get similar chunk names and their prefixes
    similar_chunks = [(corpus_chunks[i][0], sim) for i, sim in above_threshold]
    prefixes = [get_chunk_prefix(name) for name, _ in similar_chunks]

    # Count prefix occurrences
    prefix_counts = Counter(prefixes)
    most_common_prefix, count = prefix_counts.most_common(1)[0]

    # Check if majority share the prefix
    if count > len(prefixes) / 2:
        return SuggestPrefixResult(
            suggested_prefix=most_common_prefix,
            similar_chunks=similar_chunks,
            reason=f"Majority of similar chunks ({count}/{len(prefixes)}) share prefix '{most_common_prefix}'",
        )
    else:
        return SuggestPrefixResult(
            suggested_prefix=None,
            similar_chunks=similar_chunks,
            reason=f"Similar chunks have different prefixes (no common majority): {dict(prefix_counts)}",
        )
