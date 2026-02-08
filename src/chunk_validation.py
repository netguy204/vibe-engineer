"""Chunk validation module - validation logic for chunk completion and injection.

# Chunk: docs/chunks/chunk_validator_extract - Chunk validation logic extraction

This module contains validation functions extracted from src/chunks.py:
- ValidationResult: Structured error reporting for validation outcomes
- validate_chunk_complete: Validates chunk is ready for completion
- validate_chunk_injectable: Validates chunk is ready for orchestrator injection
- plan_has_content: Checks if PLAN.md has actual content beyond template
- _validate_symbol_exists: Verifies symbolic references point to existing symbols
- _validate_symbol_exists_with_context: Cross-project code reference validation

All functions that require Chunks instance access take it as the first parameter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import pathlib
import re
from typing import TYPE_CHECKING

from models import ChunkStatus
from symbols import parse_reference, extract_symbols, qualify_ref

if TYPE_CHECKING:
    from chunks import Chunks


# Chunk: docs/chunks/chunk_validate - Structured error reporting for validation
@dataclass
class ValidationResult:
    """Result of chunk completion validation."""

    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    chunk_name: str | None = None


# Chunk: docs/chunks/orch_inject_validate - Detect populated vs template-only PLAN.md
# Chunk: docs/chunks/validation_error_surface - Specific exception handling
def plan_has_content(plan_path: pathlib.Path) -> bool:
    """Check if PLAN.md has actual content beyond the template.

    Looks for content in the '## Approach' section that isn't just the
    template's HTML comment block.

    Args:
        plan_path: Path to the PLAN.md file

    Returns:
        True if the plan has actual content, False if:
        - File doesn't exist
        - File cannot be read due to permissions
        - File is just a template without content

    Note:
        Other exceptions (e.g., encoding errors) will propagate to the caller.
    """
    try:
        content = plan_path.read_text()
    except FileNotFoundError:
        return False
    except PermissionError:
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


# Chunk: docs/chunks/chunk_validate - Symbol existence verification for code references
def _validate_symbol_exists(project_dir: pathlib.Path, ref: str) -> list[str]:
    """Validate that a symbolic reference points to an existing symbol.

    Args:
        project_dir: The project root directory to resolve paths against.
        ref: Symbolic reference string (e.g., "src/foo.py#Bar::baz")

    Returns:
        List of warning messages (empty if valid).
    """
    # Qualify the ref with local project context before parsing
    qualified_ref = qualify_ref(ref, ".")
    _, file_path, symbol_path = parse_reference(qualified_ref)

    # Check if file exists
    full_path = project_dir / file_path
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


# Chunk: docs/chunks/task_chunk_validation - Cross-project code reference validation
def _validate_symbol_exists_with_context(
    project_dir: pathlib.Path,
    ref: str,
    task_dir: pathlib.Path | None = None,
    chunk_project: pathlib.Path | None = None,
) -> list[str]:
    """Validate a symbolic reference with task context for cross-project refs.

    For non-qualified references (no project::), validates against chunk_project.
    For project-qualified references (project::file), resolves the project
    via task context and validates against that project.

    Args:
        project_dir: The project root directory (fallback for chunk_project).
        ref: Symbolic reference string (may be project-qualified).
        task_dir: Optional task directory for resolving cross-project refs.
        chunk_project: Project directory where the chunk lives (default: project_dir).

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
        effective_project_dir = chunk_project if chunk_project else project_dir

        # Use local project context
        qualified_ref = qualify_ref(ref, ".")
        _, file_path, symbol_path = parse_reference(qualified_ref)

        full_path = effective_project_dir / file_path
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


# Chunk: docs/chunks/chunk_validate - Status, code_references, subsystem, investigation, and narrative validation
# Chunk: docs/chunks/bidirectional_refs - Extended to include subsystem reference validation
# Chunk: docs/chunks/chunk_frontmatter_model - Uses typed ChunkStatus and frontmatter.code_references
# Chunk: docs/chunks/task_chunk_validation - Task-context awareness for validation
# Chunk: docs/chunks/investigation_chunk_refs - Integration of investigation validation into chunk completion
def validate_chunk_complete(
    chunks: Chunks,
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
        chunks: The Chunks instance to use for resolution and validation.
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
        chunk_id = chunks.get_latest_chunk()
        if chunk_id is None:
            return ValidationResult(
                success=False,
                errors=["No chunks found"],
            )

    # Use resolve_chunk_location to handle external chunks
    location = chunks.resolve_chunk_location(chunk_id, task_dir)

    if location is None:
        return ValidationResult(
            success=False,
            errors=[f"Chunk '{chunk_id}' not found"],
        )

    # Handle cache-based resolution (external chunk without task context)
    if location.cached_content is not None:
        # Parse frontmatter from cached content
        frontmatter = chunks._parse_frontmatter_from_content(location.cached_content)
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
    # Import here to avoid circular import at module level
    from chunks import Chunks as ChunksClass

    if location.is_external:
        validation_chunks = ChunksClass(location.project_dir)
        chunk_name_to_validate = location.chunk_name
    else:
        validation_chunks = chunks
        # Fall back to resolve_chunk_id for local chunks (handles short names)
        chunk_name_to_validate = chunks.resolve_chunk_id(chunk_id)
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
            symbol_warnings = _validate_symbol_exists_with_context(
                validation_chunks.project_dir,
                ref.ref,
                task_dir=task_dir,
                chunk_project=location.project_dir,
            )
            warnings.extend(symbol_warnings)

    # Validate subsystem references
    # Chunk: docs/chunks/integrity_deprecate_standalone - Routes through IntegrityValidator
    subsystem_errors = validation_chunks.validate_subsystem_refs(chunk_name_to_validate)
    errors.extend(subsystem_errors)

    # Chunk: docs/chunks/integrity_deprecate_standalone - Routes through IntegrityValidator
    investigation_errors = validation_chunks.validate_investigation_ref(chunk_name_to_validate)
    errors.extend(investigation_errors)

    # Chunk: docs/chunks/integrity_deprecate_standalone - Routes through IntegrityValidator
    narrative_errors = validation_chunks.validate_narrative_ref(chunk_name_to_validate)
    errors.extend(narrative_errors)

    # Subsystem: docs/subsystems/friction_tracking - Friction log management
    # Chunk: docs/chunks/friction_chunk_linking - Integration of friction entry validation into chunk completion validation
    # Chunk: docs/chunks/integrity_deprecate_standalone - Routes through IntegrityValidator
    friction_errors = validation_chunks.validate_friction_entries_ref(chunk_name_to_validate)
    errors.extend(friction_errors)

    return ValidationResult(
        success=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        chunk_name=chunk_name_to_validate,
    )


# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_inject_validate - Injection-time chunk validation
def validate_chunk_injectable(chunks: Chunks, chunk_id: str) -> ValidationResult:
    """Validate that a chunk is ready for injection into the orchestrator work pool.

    This validation is called before creating a work unit. It checks:
    1. Chunk exists
    2. Status-content consistency:
       - IMPLEMENTING/ACTIVE status requires populated PLAN.md (not just template)
       - FUTURE status is allowed to have empty PLAN.md (it hasn't been planned yet)

    Args:
        chunks: The Chunks instance to use for resolution.
        chunk_id: The chunk ID to validate.

    Returns:
        ValidationResult with success status, errors, and warnings.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Resolve chunk_id
    chunk_name = chunks.resolve_chunk_id(chunk_id)
    if chunk_name is None:
        return ValidationResult(
            success=False,
            errors=[f"Chunk '{chunk_id}' not found"],
        )

    # Parse frontmatter
    frontmatter = chunks.parse_chunk_frontmatter(chunk_name)
    if frontmatter is None:
        return ValidationResult(
            success=False,
            errors=[f"Could not parse frontmatter for chunk '{chunk_id}'"],
            chunk_name=chunk_name,
        )

    # Get PLAN.md path
    plan_path = chunks.chunk_dir / chunk_name / "PLAN.md"

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
