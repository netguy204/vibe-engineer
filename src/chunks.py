"""Chunks module - business logic for chunk management."""
# Chunk: docs/chunks/implement_chunk_start - Initial chunk management
# Chunk: docs/chunks/chunk_list_command - List and latest chunk operations
# Chunk: docs/chunks/chunk_overlap_command - Overlap detection
# Chunk: docs/chunks/chunk_validate - Validation framework
# Chunk: docs/chunks/symbolic_code_refs - Symbolic reference support
# Chunk: docs/chunks/future_chunk_creation - Current/activate chunk operations
# Chunk: docs/chunks/bidirectional_refs - Subsystem validation
# Chunk: docs/chunks/proposed_chunks_frontmatter - List proposed chunks

from __future__ import annotations

from dataclasses import dataclass, field
import pathlib
import re
from typing import TYPE_CHECKING

from pydantic import ValidationError
import yaml

from artifact_ordering import ArtifactIndex, ArtifactType
from models import (
    CodeReference,
    SymbolicReference,
    SubsystemRelationship,
    CHUNK_ID_PATTERN,
    ChunkFrontmatter,
    ChunkStatus,
    extract_short_name,
)
from symbols import is_parent_of, parse_reference, extract_symbols
from template_system import ActiveChunk, TemplateContext, render_to_directory

if TYPE_CHECKING:
    from investigations import Investigations
    from narratives import Narratives
    from subsystems import Subsystems


# Chunk: docs/chunks/chunk_validate - Validation result dataclass
@dataclass
class ValidationResult:
    """Result of chunk completion validation."""

    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    chunk_name: str | None = None


# Chunk: docs/chunks/implement_chunk_start - Core chunk class
# Subsystem: docs/subsystems/template_system - Uses template rendering
class Chunks:
    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.chunk_dir = project_dir / "docs" / "chunks"
        self.chunk_dir.mkdir(parents=True, exist_ok=True)

    # Chunk: docs/chunks/implement_chunk_start - List chunk directories
    def enumerate_chunks(self):
        return [f.name for f in self.chunk_dir.iterdir() if f.is_dir()]

    # Chunk: docs/chunks/implement_chunk_start - Count of chunks
    @property
    def num_chunks(self):
        return len(self.enumerate_chunks())

    # Chunk: docs/chunks/implement_chunk_start - Detect duplicate chunk names
    # Chunk: docs/chunks/remove_sequence_prefix - Collision detection by short_name
    def find_duplicates(self, short_name: str, ticket_id: str | None) -> list[str]:
        """Find existing chunks with the same short_name.

        Detects collisions by extracting the short_name from existing directory
        names (handling both legacy {NNNN}-{name} and new {name} formats).

        Args:
            short_name: The short name to check for collisions.
            ticket_id: Optional ticket ID (included in short_name matching).

        Returns:
            List of existing chunk directory names that would collide.
        """
        # Build the target short_name (with optional ticket suffix)
        if ticket_id:
            target_short = f"{short_name}-{ticket_id}"
        else:
            target_short = short_name

        duplicates = []
        for name in self.enumerate_chunks():
            # Extract short_name from existing directory (handles both patterns)
            existing_short = extract_short_name(name)
            if existing_short == target_short:
                duplicates.append(name)
        return duplicates

    # Chunk: docs/chunks/chunk_list_command - Sorted chunk listing
    # Chunk: docs/chunks/artifact_list_ordering - Use ArtifactIndex for causal ordering
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

    # Chunk: docs/chunks/chunk_list_command - Get highest-numbered chunk
    # Chunk: docs/chunks/artifact_list_ordering - Updated for new list_chunks signature
    def get_latest_chunk(self) -> str | None:
        """Return the first chunk in causal order (newest).

        Returns:
            The chunk directory name if chunks exist, None otherwise.
        """
        chunks = self.list_chunks()
        if chunks:
            return chunks[0]
        return None

    # Chunk: docs/chunks/future_chunk_creation - Get active IMPLEMENTING chunk
    # Chunk: docs/chunks/chunk_frontmatter_model - Use typed status comparison
    # Chunk: docs/chunks/artifact_list_ordering - Updated for new list_chunks signature
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

    # Chunk: docs/chunks/future_chunk_creation - Activate FUTURE chunks
    # Chunk: docs/chunks/chunk_frontmatter_model - Use typed status comparison
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
        frontmatter = self.parse_chunk_frontmatter(chunk_name)
        if frontmatter is None:
            raise ValueError(f"Could not parse frontmatter for chunk '{chunk_id}'")

        if frontmatter.status != ChunkStatus.FUTURE:
            raise ValueError(
                f"Cannot activate: chunk '{chunk_name}' has status '{frontmatter.status.value}', "
                f"expected 'FUTURE'"
            )

        # Update status to IMPLEMENTING
        goal_path = self.get_chunk_goal_path(chunk_name)
        update_frontmatter_field(goal_path, "status", "IMPLEMENTING")

        return chunk_name

    # Chunk: docs/chunks/implement_chunk_start - Create chunk directories
    # Chunk: docs/chunks/chunk_template_expansion - Template context
    # Chunk: docs/chunks/migrate_chunks_template - Template system integration
    # Chunk: docs/chunks/populate_created_after - Populate created_after from tips
    # Chunk: docs/chunks/remove_sequence_prefix - Use short_name only (no sequence prefix)
    # Subsystem: docs/subsystems/template_system - Uses render_to_directory
    def create_chunk(
        self, ticket_id: str | None, short_name: str, status: str = "IMPLEMENTING"
    ):
        """Instantiate the chunk templates for the given ticket and short name.

        Args:
            ticket_id: Optional ticket ID to include in chunk directory name.
            short_name: Short name for the chunk.
            status: Initial status for the chunk (default: "IMPLEMENTING").

        Raises:
            ValueError: If a chunk with the same short_name already exists.
        """
        # Check for collisions before creating
        duplicates = self.find_duplicates(short_name, ticket_id)
        if duplicates:
            raise ValueError(
                f"Chunk with short_name '{short_name}' already exists: {duplicates[0]}"
            )

        # Get current chunk tips for created_after field
        artifact_index = ArtifactIndex(self.project_dir)
        tips = artifact_index.find_tips(ArtifactType.CHUNK)

        # Build directory name using short_name only (no sequence prefix)
        if ticket_id:
            chunk_path = self.chunk_dir / f"{short_name}-{ticket_id}"
        else:
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
        )
        return chunk_path

    # Chunk: docs/chunks/chunk_overlap_command - Resolve chunk ID to name
    # Chunk: docs/chunks/remove_sequence_prefix - Handle both legacy and new patterns
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

    # Chunk: docs/chunks/chunk_overlap_command - Get path to GOAL.md
    def get_chunk_goal_path(self, chunk_id: str) -> pathlib.Path | None:
        """Resolve chunk ID to GOAL.md path.

        Returns:
            Path to GOAL.md, or None if chunk not found.
        """
        chunk_name = self.resolve_chunk_id(chunk_id)
        if chunk_name is None:
            return None
        return self.chunk_dir / chunk_name / "GOAL.md"

    # Chunk: docs/chunks/chunk_overlap_command - Parse YAML frontmatter
    # Chunk: docs/chunks/chunk_frontmatter_model - Return typed ChunkFrontmatter
    def parse_chunk_frontmatter(self, chunk_id: str) -> ChunkFrontmatter | None:
        """Parse YAML frontmatter from a chunk's GOAL.md.

        Returns:
            ChunkFrontmatter if valid, or None if chunk not found or frontmatter invalid.
        """
        goal_path = self.get_chunk_goal_path(chunk_id)
        if goal_path is None or not goal_path.exists():
            return None

        content = goal_path.read_text()
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

    # Chunk: docs/chunks/chunk_overlap_command - Parse line-based code refs
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

    # Chunk: docs/chunks/symbolic_code_refs - Extract symbolic refs
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

    # Chunk: docs/chunks/symbolic_code_refs - Detect reference format
    def _is_symbolic_format(self, code_refs: list) -> bool:
        """Check if code_references use symbolic format (has 'ref' key)."""
        return any("ref" in ref for ref in code_refs)

    # Chunk: docs/chunks/chunk_overlap_command - Find overlapping chunks
    # Chunk: docs/chunks/symbolic_code_refs - Added symbolic overlap support
    # Chunk: docs/chunks/chunk_frontmatter_model - Use typed frontmatter access
    # Chunk: docs/chunks/remove_sequence_prefix - Use causal ordering instead of numeric IDs
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
            if target_is_symbolic and candidate_is_symbolic:
                # Both symbolic: use compute_symbolic_overlap
                candidate_refs = self._extract_symbolic_refs(candidate_refs_raw)
                if compute_symbolic_overlap(target_refs, candidate_refs):
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
                # For symbolic refs, extract just the file path portion
                if target_is_symbolic:
                    target_files = {parse_reference(r)[0] for r in target_refs}
                    candidate_files = set(self.parse_code_references(candidate_refs_raw).keys())
                else:
                    target_files = set(target_refs_dict.keys())
                    candidate_refs = self._extract_symbolic_refs(candidate_refs_raw)
                    candidate_files = {parse_reference(r)[0] for r in candidate_refs}

                # Any shared file means potential overlap
                if target_files & candidate_files:
                    affected.append(name)

        return sorted(affected)

    # Chunk: docs/chunks/chunk_validate - Validate chunk for completion
    # Chunk: docs/chunks/symbolic_code_refs - Added symbolic ref validation
    # Chunk: docs/chunks/chunk_frontmatter_model - Use typed frontmatter access
    def validate_chunk_complete(self, chunk_id: str | None = None) -> ValidationResult:
        """Validate that a chunk is ready for completion.

        Checks:
        1. Chunk exists
        2. Status is IMPLEMENTING or ACTIVE
        3. code_references conforms to schema and is non-empty
        4. (For symbolic refs) Referenced symbols exist (produces warnings, not errors)
        5. Subsystem references are valid and exist

        Supports both old line-based format and new symbolic format.

        Args:
            chunk_id: The chunk ID to validate. Defaults to latest chunk.

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

        chunk_name = self.resolve_chunk_id(chunk_id)
        if chunk_name is None:
            return ValidationResult(
                success=False,
                errors=[f"Chunk '{chunk_id}' not found"],
            )

        # Parse frontmatter
        frontmatter = self.parse_chunk_frontmatter(chunk_id)
        if frontmatter is None:
            return ValidationResult(
                success=False,
                errors=[f"Could not parse frontmatter for chunk '{chunk_id}'"],
                chunk_name=chunk_name,
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
            for ref in frontmatter.code_references:
                symbol_warnings = self._validate_symbol_exists(ref.ref)
                warnings.extend(symbol_warnings)

        # Validate subsystem references
        subsystem_errors = self.validate_subsystem_refs(chunk_name)
        errors.extend(subsystem_errors)

        return ValidationResult(
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            chunk_name=chunk_name,
        )

    # Chunk: docs/chunks/symbolic_code_refs - Validate symbol existence
    def _validate_symbol_exists(self, ref: str) -> list[str]:
        """Validate that a symbolic reference points to an existing symbol.

        Args:
            ref: Symbolic reference string (e.g., "src/foo.py#Bar::baz")

        Returns:
            List of warning messages (empty if valid).
        """
        file_path, symbol_path = parse_reference(ref)

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

    # Chunk: docs/chunks/proposed_chunks_frontmatter - List proposed chunks
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

    # Chunk: docs/chunks/valid_transitions - State transition validation
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

    # Chunk: docs/chunks/valid_transitions - State transition validation
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

    # Chunk: docs/chunks/bidirectional_refs - Validate subsystem references
    # Chunk: docs/chunks/chunk_frontmatter_model - Use typed frontmatter access
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


# Chunk: docs/chunks/symbolic_code_refs - Symbolic reference overlap logic
def compute_symbolic_overlap(refs_a: list[str], refs_b: list[str]) -> bool:
    """Determine if two lists of symbolic references have any overlap.

    Overlap occurs when any reference in refs_a is a parent of, child of,
    or equal to any reference in refs_b.

    Args:
        refs_a: List of symbolic reference strings.
        refs_b: List of symbolic reference strings.

    Returns:
        True if any overlap exists, False otherwise.
    """
    if not refs_a or not refs_b:
        return False

    for ref_a in refs_a:
        for ref_b in refs_b:
            # Check both directions since is_parent_of is not symmetric
            if is_parent_of(ref_a, ref_b) or is_parent_of(ref_b, ref_a):
                return True
    return False
