"""Chunks module - business logic for chunk management."""
# Chunk: docs/chunks/0001-implement_chunk_start - Initial chunk management
# Chunk: docs/chunks/0002-chunk_list_command - List and latest chunk operations
# Chunk: docs/chunks/0004-chunk_overlap_command - Overlap detection
# Chunk: docs/chunks/0005-chunk_validate - Validation framework
# Chunk: docs/chunks/0012-symbolic_code_refs - Symbolic reference support
# Chunk: docs/chunks/0013-future_chunk_creation - Current/activate chunk operations
# Chunk: docs/chunks/0018-bidirectional_refs - Subsystem validation
# Chunk: docs/chunks/0032-proposed_chunks_frontmatter - List proposed chunks

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
)
from symbols import is_parent_of, parse_reference, extract_symbols
from template_system import ActiveChunk, TemplateContext, render_to_directory

if TYPE_CHECKING:
    from investigations import Investigations
    from narratives import Narratives
    from subsystems import Subsystems


# Chunk: docs/chunks/0005-chunk_validate - Validation result dataclass
@dataclass
class ValidationResult:
    """Result of chunk completion validation."""

    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    chunk_name: str | None = None


# Chunk: docs/chunks/0001-implement_chunk_start - Core chunk class
# Subsystem: docs/subsystems/0001-template_system - Uses template rendering
class Chunks:
    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.chunk_dir = project_dir / "docs" / "chunks"
        self.chunk_dir.mkdir(parents=True, exist_ok=True)

    # Chunk: docs/chunks/0001-implement_chunk_start - List chunk directories
    def enumerate_chunks(self):
        return [f.name for f in self.chunk_dir.iterdir() if f.is_dir()]

    # Chunk: docs/chunks/0001-implement_chunk_start - Count of chunks
    @property
    def num_chunks(self):
        return len(self.enumerate_chunks())

    # Chunk: docs/chunks/0001-implement_chunk_start - Detect duplicate chunk names
    def find_duplicates(self, short_name: str, ticket_id: str | None) -> list[str]:
        """Find existing chunks with the same short_name and ticket_id."""
        if ticket_id:
            suffix = f"-{short_name}-{ticket_id}"
        else:
            suffix = f"-{short_name}"
        return [name for name in self.enumerate_chunks() if name.endswith(suffix)]

    # Chunk: docs/chunks/0002-chunk_list_command - Sorted chunk listing
    # Chunk: docs/chunks/0041-artifact_list_ordering - Use ArtifactIndex for causal ordering
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

    # Chunk: docs/chunks/0002-chunk_list_command - Get highest-numbered chunk
    # Chunk: docs/chunks/0041-artifact_list_ordering - Updated for new list_chunks signature
    def get_latest_chunk(self) -> str | None:
        """Return the first chunk in causal order (newest).

        Returns:
            The chunk directory name if chunks exist, None otherwise.
        """
        chunks = self.list_chunks()
        if chunks:
            return chunks[0]
        return None

    # Chunk: docs/chunks/0013-future_chunk_creation - Get active IMPLEMENTING chunk
    # Chunk: docs/chunks/0036-chunk_frontmatter_model - Use typed status comparison
    # Chunk: docs/chunks/0041-artifact_list_ordering - Updated for new list_chunks signature
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

    # Chunk: docs/chunks/0013-future_chunk_creation - Activate FUTURE chunks
    # Chunk: docs/chunks/0036-chunk_frontmatter_model - Use typed status comparison
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

    # Chunk: docs/chunks/0001-implement_chunk_start - Create chunk directories
    # Chunk: docs/chunks/0011-chunk_template_expansion - Template context
    # Chunk: docs/chunks/0025-migrate_chunks_template - Template system integration
    # Chunk: docs/chunks/0039-populate_created_after - Populate created_after from tips
    # Subsystem: docs/subsystems/0001-template_system - Uses render_to_directory
    def create_chunk(
        self, ticket_id: str | None, short_name: str, status: str = "IMPLEMENTING"
    ):
        """Instantiate the chunk templates for the given ticket and short name.

        Args:
            ticket_id: Optional ticket ID to include in chunk directory name.
            short_name: Short name for the chunk.
            status: Initial status for the chunk (default: "IMPLEMENTING").
        """
        # Get current chunk tips for created_after field
        artifact_index = ArtifactIndex(self.project_dir)
        tips = artifact_index.find_tips(ArtifactType.CHUNK)

        next_chunk_id = self.num_chunks + 1
        next_chunk_id_str = f"{next_chunk_id:04d}"
        if ticket_id:
            chunk_path = self.chunk_dir / f"{next_chunk_id_str}-{short_name}-{ticket_id}"
        else:
            chunk_path = self.chunk_dir / f"{next_chunk_id_str}-{short_name}"
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

    # Chunk: docs/chunks/0004-chunk_overlap_command - Resolve chunk ID to name
    def resolve_chunk_id(self, chunk_id: str) -> str | None:
        """Resolve a chunk ID (4-digit or full name) to its directory name.

        Returns:
            The full chunk directory name, or None if not found.
        """
        chunks = self.enumerate_chunks()
        # Exact match
        if chunk_id in chunks:
            return chunk_id
        # Prefix match (e.g., "0003" matches "0003-feature")
        for name in chunks:
            if name.startswith(f"{chunk_id}-"):
                return name
        return None

    # Chunk: docs/chunks/0004-chunk_overlap_command - Get path to GOAL.md
    def get_chunk_goal_path(self, chunk_id: str) -> pathlib.Path | None:
        """Resolve chunk ID to GOAL.md path.

        Returns:
            Path to GOAL.md, or None if chunk not found.
        """
        chunk_name = self.resolve_chunk_id(chunk_id)
        if chunk_name is None:
            return None
        return self.chunk_dir / chunk_name / "GOAL.md"

    # Chunk: docs/chunks/0004-chunk_overlap_command - Parse YAML frontmatter
    # Chunk: docs/chunks/0036-chunk_frontmatter_model - Return typed ChunkFrontmatter
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

    # Chunk: docs/chunks/0004-chunk_overlap_command - Parse line-based code refs
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

    # Chunk: docs/chunks/0012-symbolic_code_refs - Extract symbolic refs
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

    # Chunk: docs/chunks/0012-symbolic_code_refs - Detect reference format
    def _is_symbolic_format(self, code_refs: list) -> bool:
        """Check if code_references use symbolic format (has 'ref' key)."""
        return any("ref" in ref for ref in code_refs)

    # Chunk: docs/chunks/0004-chunk_overlap_command - Find overlapping chunks
    # Chunk: docs/chunks/0012-symbolic_code_refs - Added symbolic overlap support
    # Chunk: docs/chunks/0036-chunk_frontmatter_model - Use typed frontmatter access
    def find_overlapping_chunks(self, chunk_id: str) -> list[str]:
        """Find ACTIVE chunks with lower IDs that have overlapping code references.

        Supports both symbolic references (new format) and line-based references
        (old format). Symbolic refs use hierarchical containment for overlap;
        line-based refs use line number comparison.

        Args:
            chunk_id: The chunk ID to check (4-digit or full name).

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

        # Extract numeric ID of target chunk
        target_match = re.match(r'^(\d{4})-', chunk_name)
        if not target_match:
            return []
        target_num = int(target_match.group(1))

        # Find all ACTIVE chunks with lower IDs
        affected = []
        for name in self.enumerate_chunks():
            # Parse chunk number
            num_match = re.match(r'^(\d{4})-', name)
            if not num_match:
                continue
            chunk_num = int(num_match.group(1))

            # Only check chunks with lower IDs
            if chunk_num >= target_num:
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

    # Chunk: docs/chunks/0005-chunk_validate - Validate chunk for completion
    # Chunk: docs/chunks/0012-symbolic_code_refs - Added symbolic ref validation
    # Chunk: docs/chunks/0036-chunk_frontmatter_model - Use typed frontmatter access
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

    # Chunk: docs/chunks/0012-symbolic_code_refs - Validate symbol existence
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

    # Chunk: docs/chunks/0032-proposed_chunks_frontmatter - List proposed chunks
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

    # Chunk: docs/chunks/0018-bidirectional_refs - Validate subsystem references
    # Chunk: docs/chunks/0036-chunk_frontmatter_model - Use typed frontmatter access
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


# Chunk: docs/chunks/0012-symbolic_code_refs - Symbolic reference overlap logic
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
