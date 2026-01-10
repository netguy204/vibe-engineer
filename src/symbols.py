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
def parse_reference(ref: str) -> tuple[str, str | None]:
    """Parse a symbolic reference into file path and symbol path.

    Args:
        ref: Reference string in format {file_path} or {file_path}#{symbol_path}

    Returns:
        Tuple of (file_path, symbol_path) where symbol_path is None for
        file-only references.
    """
    if "#" in ref:
        file_path, symbol_path = ref.split("#", 1)
        return file_path, symbol_path
    return ref, None


# Chunk: docs/chunks/symbolic_code_refs - Hierarchical containment check
def is_parent_of(parent: str, child: str) -> bool:
    """Check if parent reference hierarchically contains child reference.

    A reference is a parent of another if:
    - Same file and parent has no symbol (file contains all symbols)
    - Same file and symbol, and parent's symbol is a prefix of child's symbol

    Args:
        parent: Potential parent reference.
        child: Potential child reference.

    Returns:
        True if parent contains child, False otherwise.
    """
    parent_file, parent_symbol = parse_reference(parent)
    child_file, child_symbol = parse_reference(child)

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
