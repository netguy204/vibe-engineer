"""Chunks module - business logic for chunk management."""

from dataclasses import dataclass, field
import pathlib
import re

import jinja2
from pydantic import ValidationError
import yaml

from constants import template_dir
from models import CodeReference, SymbolicReference, SubsystemRelationship, CHUNK_ID_PATTERN
from symbols import is_parent_of, parse_reference, extract_symbols


@dataclass
class ValidationResult:
    """Result of chunk completion validation."""

    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    chunk_name: str | None = None


def render_template(template_name, **kwargs):
    template_path = template_dir / template_name
    with open(template_path, "r") as template_file:
        template = jinja2.Template(template_file.read())
        return template.render(**kwargs)


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
        """Find existing chunks with the same short_name and ticket_id."""
        if ticket_id:
            suffix = f"-{short_name}-{ticket_id}"
        else:
            suffix = f"-{short_name}"
        return [name for name in self.enumerate_chunks() if name.endswith(suffix)]

    def list_chunks(self) -> list[tuple[int, str]]:
        """List all chunks sorted by numeric prefix descending.

        Returns:
            List of (chunk_number, chunk_name) tuples, sorted by chunk_number
            descending. Returns empty list if no chunks exist.
        """
        chunks = []
        pattern = re.compile(r"^(\d{4})-")
        for name in self.enumerate_chunks():
            match = pattern.match(name)
            if match:
                chunk_number = int(match.group(1))
                chunks.append((chunk_number, name))
        chunks.sort(key=lambda x: x[0], reverse=True)
        return chunks

    def get_latest_chunk(self) -> str | None:
        """Return the highest-numbered chunk directory name.

        Returns:
            The chunk directory name if chunks exist, None otherwise.
        """
        chunks = self.list_chunks()
        if chunks:
            return chunks[0][1]
        return None

    def get_current_chunk(self) -> str | None:
        """Return the highest-numbered chunk with status IMPLEMENTING.

        This finds the "current" chunk that is actively being worked on,
        ignoring FUTURE, ACTIVE, SUPERSEDED, and HISTORICAL chunks.

        Returns:
            The chunk directory name if an IMPLEMENTING chunk exists, None otherwise.
        """
        chunks = self.list_chunks()
        for _, chunk_name in chunks:
            frontmatter = self.parse_chunk_frontmatter(chunk_name)
            if frontmatter and frontmatter.get("status") == "IMPLEMENTING":
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
        frontmatter = self.parse_chunk_frontmatter(chunk_name)
        if frontmatter is None:
            raise ValueError(f"Could not parse frontmatter for chunk '{chunk_id}'")

        status = frontmatter.get("status")
        if status != "FUTURE":
            raise ValueError(
                f"Cannot activate: chunk '{chunk_name}' has status '{status}', "
                f"expected 'FUTURE'"
            )

        # Update status to IMPLEMENTING
        goal_path = self.get_chunk_goal_path(chunk_name)
        update_frontmatter_field(goal_path, "status", "IMPLEMENTING")

        return chunk_name

    def create_chunk(
        self, ticket_id: str | None, short_name: str, status: str = "IMPLEMENTING"
    ):
        """Instantiate the chunk templates for the given ticket and short name.

        Args:
            ticket_id: Optional ticket ID to include in chunk directory name.
            short_name: Short name for the chunk.
            status: Initial status for the chunk (default: "IMPLEMENTING").
        """
        next_chunk_id = self.num_chunks + 1
        next_chunk_id_str = f"{next_chunk_id:04d}"
        if ticket_id:
            chunk_path = self.chunk_dir / f"{next_chunk_id_str}-{short_name}-{ticket_id}"
        else:
            chunk_path = self.chunk_dir / f"{next_chunk_id_str}-{short_name}"
        chunk_path.mkdir(parents=True, exist_ok=True)
        for chunk_template in template_dir.glob("chunk/*.md"):
            rendered_template = render_template(
                chunk_template.relative_to(template_dir),
                ticket_id=ticket_id,
                short_name=short_name,
                next_chunk_id=next_chunk_id_str,
                chunk_directory=chunk_path.name,
                status=status,
            )
            with open(chunk_path / chunk_template.name, "w") as chunk_file:
                chunk_file.write(rendered_template)
        return chunk_path

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

    def get_chunk_goal_path(self, chunk_id: str) -> pathlib.Path | None:
        """Resolve chunk ID to GOAL.md path.

        Returns:
            Path to GOAL.md, or None if chunk not found.
        """
        chunk_name = self.resolve_chunk_id(chunk_id)
        if chunk_name is None:
            return None
        return self.chunk_dir / chunk_name / "GOAL.md"

    def parse_chunk_frontmatter(self, chunk_id: str) -> dict | None:
        """Parse YAML frontmatter from a chunk's GOAL.md.

        Returns:
            Dictionary of frontmatter fields, or None if chunk not found.
            Returns empty dict if frontmatter is malformed or missing.
        """
        goal_path = self.get_chunk_goal_path(chunk_id)
        if goal_path is None or not goal_path.exists():
            return None

        content = goal_path.read_text()
        # Extract frontmatter between --- markers
        match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not match:
            return {}

        try:
            frontmatter = yaml.safe_load(match.group(1))
            return frontmatter if isinstance(frontmatter, dict) else {}
        except yaml.YAMLError:
            return {}

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

        code_refs = frontmatter.get("code_references", [])
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
            if fm is None or fm.get("status") != "ACTIVE":
                continue

            candidate_refs_raw = fm.get("code_references", [])
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
        status = frontmatter.get("status")
        valid_statuses = ("IMPLEMENTING", "ACTIVE")
        if status not in valid_statuses:
            errors.append(
                f"Status is '{status}', must be 'IMPLEMENTING' or 'ACTIVE' to complete"
            )

        # Validate code_references
        code_refs = frontmatter.get("code_references", [])

        if not code_refs:
            errors.append(
                "code_references is empty; at least one reference is required"
            )
        else:
            # Detect format: symbolic (has 'ref') or line-based (has 'file')
            is_symbolic = any("ref" in ref for ref in code_refs)

            if is_symbolic:
                # Validate symbolic references
                for i, ref in enumerate(code_refs):
                    try:
                        validated = SymbolicReference.model_validate(ref)
                        # Validate that referenced symbol exists
                        symbol_warnings = self._validate_symbol_exists(validated.ref)
                        warnings.extend(symbol_warnings)
                    except ValidationError as e:
                        for err in e.errors():
                            loc = ".".join(str(x) for x in err["loc"])
                            field_path = f"code_references[{i}].{loc}" if loc else f"code_references[{i}]"
                            msg = err["msg"]
                            errors.append(f"{field_path}: {msg}")
            else:
                # Validate old line-based format
                for i, ref in enumerate(code_refs):
                    try:
                        CodeReference.model_validate(ref)
                    except ValidationError as e:
                        for err in e.errors():
                            loc = ".".join(str(x) for x in err["loc"])
                            field_path = f"code_references[{i}].{loc}" if loc else f"code_references[{i}]"
                            msg = err["msg"]
                            errors.append(f"{field_path}: {msg}")

        # Validate subsystem references
        subsystem_errors = self.validate_subsystem_refs(chunk_name)
        errors.extend(subsystem_errors)

        return ValidationResult(
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            chunk_name=chunk_name,
        )

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

        # Get subsystems field (may not exist in older chunks)
        subsystems = frontmatter.get("subsystems", [])
        if not subsystems:
            return []

        # Subsystems directory path
        subsystems_dir = self.project_dir / "docs" / "subsystems"

        for entry in subsystems:
            subsystem_id = entry.get("subsystem_id", "")

            # Validate format using SubsystemRelationship model
            try:
                SubsystemRelationship.model_validate(entry)
            except ValidationError as e:
                for err in e.errors():
                    msg = err["msg"]
                    errors.append(f"Invalid subsystem reference '{subsystem_id}': {msg}")
                continue

            # Check if subsystem directory exists
            subsystem_path = subsystems_dir / subsystem_id
            if not subsystem_path.exists():
                errors.append(
                    f"Subsystem '{subsystem_id}' does not exist in docs/subsystems/"
                )

        return errors


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
