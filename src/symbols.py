"""Symbol extraction and reference parsing utilities.

This module provides utilities for extracting symbol definitions from Python
source files using the ast module, and for parsing/manipulating symbolic
references in the {file_path}#{symbol_path} format.
"""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle

import ast
import re
from pathlib import Path


# Chunk: docs/chunks/symbolic_code_refs - AST-based symbol extraction from source files
def extract_symbols(file_path: Path) -> set[str]:
    """Extract all symbol definitions from a Python source file.

    Returns symbol paths using :: as the nesting separator.

    Examples of returned symbols:
        - validate_short_name (function)
        - Chunks (class)
        - Chunks::__init__ (method)
        - Chunks::create_chunk (method)
        - Outer::Inner (nested class)
        - Outer::Inner::method (method in nested class)

    Args:
        file_path: Path to the Python source file.

    Returns:
        Set of symbol paths found in the file.
        Returns empty set for non-Python files, syntax errors, or missing files.
    """
    # Only process Python files
    if not str(file_path).endswith(".py"):
        return set()

    # Handle missing files
    if not file_path.exists():
        return set()

    try:
        source = file_path.read_text()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return set()

    symbols: set[str] = set()
    _extract_from_node(tree, [], symbols)
    return symbols


def _extract_from_node(node: ast.AST, prefix: list[str], symbols: set[str]) -> None:
    """Recursively extract symbols from an AST node.

    Args:
        node: The AST node to process.
        prefix: List of parent symbol names forming the path prefix.
        symbols: Set to add discovered symbols to.
    """
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
            symbol_name = child.name
            if prefix:
                full_path = "::".join(prefix + [symbol_name])
            else:
                full_path = symbol_name
            symbols.add(full_path)
            # Functions can contain nested classes
            _extract_from_node(child, prefix + [symbol_name], symbols)

        elif isinstance(child, ast.ClassDef):
            class_name = child.name
            if prefix:
                full_path = "::".join(prefix + [class_name])
            else:
                full_path = class_name
            symbols.add(full_path)
            # Recurse into class body for methods and nested classes
            _extract_from_node(child, prefix + [class_name], symbols)


# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/symbolic_code_refs - Parse symbolic reference into file path and symbol
def parse_reference(
    ref: str, *, current_project: str | None = None
) -> tuple[str, str, str | None]:
    """Parse a symbolic reference into project, file path, and symbol path.

    Supports project-qualified references in the format:
        org/repo::file_path#symbol_path

    The result always includes a project - either from an explicit qualifier
    in the reference, or from the current_project parameter.

    Args:
        ref: Reference string in formats:
            - file_path (requires current_project)
            - file_path#symbol_path (requires current_project)
            - org/repo::file_path (project-qualified)
            - org/repo::file_path#symbol_path (project-qualified)
        current_project: Project context for non-qualified references. Required
            when the reference has no explicit project qualifier.

    Returns:
        Tuple of (project, file_path, symbol_path) where:
        - project is always a string (explicit qualifier or current_project)
        - file_path is the path to the file
        - symbol_path is the symbol path (None for file-only references)

    Raises:
        ValueError: If the reference has no explicit project qualifier and
            current_project is not provided.
    """
    project: str | None = None
    file_and_symbol = ref

    # Check for project qualifier (::) - must come before # if present
    # The :: in symbol paths (e.g., Bar::baz) comes after # so we only
    # check for :: before the first #
    hash_pos = ref.find("#")
    if hash_pos == -1:
        # No symbol delimiter, check whole string for ::
        double_colon_pos = ref.find("::")
    else:
        # Only check for :: before the # symbol delimiter
        double_colon_pos = ref[:hash_pos].find("::")

    if double_colon_pos != -1:
        # Split on first :: only (which must be before any #)
        project = ref[:double_colon_pos]
        file_and_symbol = ref[double_colon_pos + 2:]

    # If no explicit project, use current_project
    if project is None:
        project = current_project

    # Project must be known
    if project is None:
        raise ValueError(
            f"Reference '{ref}' has no project qualifier and current_project was not provided"
        )

    # Parse file path and symbol
    if "#" in file_and_symbol:
        file_path, symbol_path = file_and_symbol.split("#", 1)
        return project, file_path, symbol_path

    return project, file_and_symbol, None


# Chunk: docs/chunks/crossref_glob_refs - Glob patterns in reference file parts
_GLOB_MAGIC = re.compile(r"[*?\[]")


def is_glob_pattern(file_part: str) -> bool:
    """Return True when a reference file part is a glob pattern.

    A file part containing glob magic (``*``, ``?``, ``[``) declares a
    *shape* of paths ("this applies uniformly across everything matching
    this pattern") rather than one literal path.
    """
    return bool(_GLOB_MAGIC.search(file_part))


# Chunk: docs/chunks/crossref_glob_refs - Shared glob expansion for path validators
def expand_glob(root: Path, pattern: str) -> list[Path]:
    """Expand a glob pattern against a project root.

    Returns the sorted matches. Malformed patterns (absolute paths, bad
    bracket syntax) degrade to an empty list — every validator treats an
    empty expansion as an error naming the pattern, which points the
    operator at the bad pattern instead of crashing the validator.
    """
    try:
        return sorted(root.glob(pattern))
    except (ValueError, NotImplementedError, IndexError, re.error):
        return []


# Chunk: docs/chunks/crossref_generator_verify - Shared reference-existence check
# Chunk: docs/chunks/crossref_glob_refs - Glob file parts: error only on empty expansion
def check_reference_target(
    project_dir: Path, ref: str
) -> tuple[str | None, str | None]:
    """Check a local (non-project-qualified) symbolic reference against a project.

    This is the single existence check shared by chunk validation, the chunk
    completion gate, and subsystem code_references validation, so every
    reference-emitting flow agrees on what "absent" means.

    Args:
        project_dir: Project root to resolve the file part against.
        ref: Reference in {file_path} or {file_path}#{symbol_path} form.

    Returns:
        Tuple of (error, warning):
        - error: the target is provably absent — the file does not exist, or
          the symbol is neither defined nor mentioned in a parseable Python
          file.
        - warning: the target is uncheckable — a Python file that could not
          be parsed, or a name that occurs in the file without being a
          def/class definition (module-level constants are legitimate
          reference targets that AST extraction does not index).
        - (None, None): verified, or not symbol-checkable (non-Python file
          symbol anchors are skipped; honest UNCHECKED reporting for those
          belongs to crossref_unchecked_anchors).

    Glob file parts (``packages/tasks/*/Dockerfile``) are patterns, not
    literal paths: an empty expansion is an error, a non-empty expansion is
    verified, and a symbol anchor on a pattern is uncheckable (warning).
    """
    qualified_ref = qualify_ref(ref, ".")
    _, file_path, symbol_path = parse_reference(qualified_ref)

    if is_glob_pattern(file_path):
        if not expand_glob(project_dir, file_path):
            return (
                f"Glob pattern matches nothing: {file_path} (ref: {ref})",
                None,
            )
        if symbol_path is not None:
            return (
                None,
                f"Symbol anchor '{symbol_path}' on glob pattern {file_path} "
                f"is not checked across expansions (ref: {ref})",
            )
        return (None, None)

    full_path = project_dir / file_path
    if not full_path.exists():
        return (f"File not found: {file_path} (ref: {ref})", None)

    if symbol_path is None:
        return (None, None)

    symbols = extract_symbols(full_path)
    if not symbols:
        if str(file_path).endswith(".py"):
            return (
                None,
                f"Could not extract symbols from {file_path} (ref: {ref})",
            )
        # Non-Python files can't have symbol validation
        return (None, None)

    if symbol_path not in symbols:
        # AST extraction only indexes functions and classes. A reference to a
        # module-level constant is legitimate, so before declaring provable
        # absence, check whether the name occurs as a whole word anywhere in
        # the file. Present-but-not-a-definition is uncheckable (warning);
        # absent entirely is an invented or deleted name (error).
        leaf = symbol_path.rsplit("::", 1)[-1]
        try:
            content = full_path.read_text()
        except (OSError, UnicodeDecodeError):
            content = ""
        if re.search(rf"\b{re.escape(leaf)}\b", content):
            return (
                None,
                f"Symbol {symbol_path} is not a def/class definition in "
                f"{file_path}; the name occurs but cannot be verified (ref: {ref})",
            )
        return (
            f"Symbol not found: {symbol_path} in {file_path} (ref: {ref})",
            None,
        )

    return (None, None)


def qualify_ref(ref: str, project: str) -> str:
    """Ensure a reference string is project-qualified.

    If the reference already has a project qualifier, returns it unchanged.
    Otherwise, prepends the project qualifier.

    Args:
        ref: Reference string (may or may not be qualified).
        project: Project to use if ref is not already qualified.

    Returns:
        Project-qualified reference string.
    """
    # Check for :: before # (project delimiter must come before symbol delimiter)
    hash_pos = ref.find("#")
    if hash_pos == -1:
        check_portion = ref
    else:
        check_portion = ref[:hash_pos]

    if "::" in check_portion:
        return ref  # Already qualified
    return f"{project}::{ref}"


# Chunk: docs/chunks/symbolic_code_refs - Hierarchical containment check for overlap detection
def is_parent_of(parent: str, child: str) -> bool:
    """Check if parent reference hierarchically contains child reference.

    Both references must be project-qualified (contain ::). Use qualify_ref()
    to ensure refs are qualified before calling this function.

    A reference is a parent of another if:
    - Same project
    - Same file and parent has no symbol (file contains all symbols)
    - Same file and symbol, and parent's symbol is a prefix of child's symbol

    Args:
        parent: Potential parent reference (must be project-qualified).
        child: Potential child reference (must be project-qualified).

    Returns:
        True if parent contains child, False otherwise.

    Raises:
        ValueError: If either reference is not project-qualified.
    """
    parent_project, parent_file, parent_symbol = parse_reference(parent)
    child_project, child_file, child_symbol = parse_reference(child)

    # Different projects are never in a parent-child relationship
    if parent_project != child_project:
        return False

    # Different files are never in a parent-child relationship
    if parent_file != child_file:
        return False

    # File-only reference (no symbol) is parent of everything in that file
    if parent_symbol is None:
        return True

    # If child has no symbol but parent does, parent cannot contain child
    if child_symbol is None:
        return False

    # Same symbol means containment (self-containment)
    if parent_symbol == child_symbol:
        return True

    # Check if child's symbol starts with parent's symbol followed by ::
    # e.g., "Bar::baz" starts with "Bar::" making "Bar" a parent of "Bar::baz"
    return child_symbol.startswith(parent_symbol + "::")
