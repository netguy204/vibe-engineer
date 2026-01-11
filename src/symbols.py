"""Symbol extraction and reference parsing utilities.

This module provides utilities for extracting symbol definitions from Python
source files using the ast module, and for parsing/manipulating symbolic
references in the {file_path}#{symbol_path} format.
"""
# Chunk: docs/chunks/symbolic_code_refs - Symbol extraction and parsing

import ast
from pathlib import Path


# Chunk: docs/chunks/symbolic_code_refs - Extract symbols from Python files
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


# Chunk: docs/chunks/symbolic_code_refs - Recursive AST traversal
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


# Chunk: docs/chunks/symbolic_code_refs - Parse reference into components
# Chunk: docs/chunks/project_qualified_refs - Extended for project qualification
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


# Chunk: docs/chunks/project_qualified_refs - Qualify a reference string
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


# Chunk: docs/chunks/symbolic_code_refs - Hierarchical containment check
# Chunk: docs/chunks/project_qualified_refs - Requires qualified references
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
