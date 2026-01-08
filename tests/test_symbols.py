"""Tests for symbol extraction and reference parsing utilities."""

from pathlib import Path

import pytest

from symbols import extract_symbols, parse_reference, is_parent_of


class TestExtractSymbols:
    """Tests for extract_symbols function."""

    def test_extracts_top_level_function(self, tmp_path: Path):
        """Extracts top-level function names."""
        file = tmp_path / "test.py"
        file.write_text("def my_function():\n    pass\n")
        symbols = extract_symbols(file)
        assert "my_function" in symbols

    def test_extracts_multiple_functions(self, tmp_path: Path):
        """Extracts multiple top-level functions."""
        file = tmp_path / "test.py"
        file.write_text(
            "def func_one():\n    pass\n\n"
            "def func_two():\n    pass\n"
        )
        symbols = extract_symbols(file)
        assert "func_one" in symbols
        assert "func_two" in symbols

    def test_extracts_class_names(self, tmp_path: Path):
        """Extracts class names."""
        file = tmp_path / "test.py"
        file.write_text("class MyClass:\n    pass\n")
        symbols = extract_symbols(file)
        assert "MyClass" in symbols

    def test_extracts_class_methods(self, tmp_path: Path):
        """Extracts class methods with :: separator."""
        file = tmp_path / "test.py"
        file.write_text(
            "class MyClass:\n"
            "    def __init__(self):\n"
            "        pass\n\n"
            "    def do_thing(self):\n"
            "        pass\n"
        )
        symbols = extract_symbols(file)
        assert "MyClass" in symbols
        assert "MyClass::__init__" in symbols
        assert "MyClass::do_thing" in symbols

    def test_extracts_nested_classes(self, tmp_path: Path):
        """Nested classes produce paths like Outer::Inner."""
        file = tmp_path / "test.py"
        file.write_text(
            "class Outer:\n"
            "    class Inner:\n"
            "        def method(self):\n"
            "            pass\n"
        )
        symbols = extract_symbols(file)
        assert "Outer" in symbols
        assert "Outer::Inner" in symbols
        assert "Outer::Inner::method" in symbols

    def test_empty_file_returns_empty_set(self, tmp_path: Path):
        """Empty file returns empty set."""
        file = tmp_path / "test.py"
        file.write_text("")
        symbols = extract_symbols(file)
        assert symbols == set()

    def test_file_with_only_imports_returns_empty_set(self, tmp_path: Path):
        """File with only imports returns empty set."""
        file = tmp_path / "test.py"
        file.write_text("import os\nfrom pathlib import Path\n")
        symbols = extract_symbols(file)
        assert symbols == set()

    def test_syntax_error_returns_empty_set(self, tmp_path: Path):
        """File with syntax errors returns empty set gracefully."""
        file = tmp_path / "test.py"
        file.write_text("def broken(\n")  # Invalid syntax
        symbols = extract_symbols(file)
        assert symbols == set()

    def test_nonexistent_file_returns_empty_set(self, tmp_path: Path):
        """Nonexistent file returns empty set."""
        file = tmp_path / "nonexistent.py"
        symbols = extract_symbols(file)
        assert symbols == set()

    def test_non_python_file_returns_empty_set(self, tmp_path: Path):
        """Non-Python file returns empty set."""
        file = tmp_path / "test.rs"
        file.write_text("fn main() {}")
        symbols = extract_symbols(file)
        assert symbols == set()

    def test_real_file_extraction(self):
        """Test against a real file in the codebase."""
        # This tests against an actual file to ensure integration works
        models_path = Path("src/models.py")
        if models_path.exists():
            symbols = extract_symbols(models_path)
            # Should find classes we know exist
            assert "SymbolicReference" in symbols
            assert "TaskConfig" in symbols
            # Should find methods
            assert "TaskConfig::validate_external_chunk_repo" in symbols


class TestParseReference:
    """Tests for parse_reference function."""

    def test_file_only_reference(self):
        """File-only reference returns (file_path, None)."""
        file_path, symbol_path = parse_reference("src/foo.py")
        assert file_path == "src/foo.py"
        assert symbol_path is None

    def test_class_reference(self):
        """Class reference returns (file_path, class_name)."""
        file_path, symbol_path = parse_reference("src/foo.py#Bar")
        assert file_path == "src/foo.py"
        assert symbol_path == "Bar"

    def test_method_reference(self):
        """Method reference returns (file_path, class::method)."""
        file_path, symbol_path = parse_reference("src/foo.py#Bar::baz")
        assert file_path == "src/foo.py"
        assert symbol_path == "Bar::baz"

    def test_deeply_nested_reference(self):
        """Deeply nested reference parses correctly."""
        file_path, symbol_path = parse_reference("src/foo.py#A::B::C::D")
        assert file_path == "src/foo.py"
        assert symbol_path == "A::B::C::D"

    def test_standalone_function_reference(self):
        """Standalone function reference parses correctly."""
        file_path, symbol_path = parse_reference("src/utils.py#validate_input")
        assert file_path == "src/utils.py"
        assert symbol_path == "validate_input"


class TestIsParentOf:
    """Tests for is_parent_of function."""

    def test_file_is_parent_of_class(self):
        """File reference is parent of class in that file."""
        assert is_parent_of("src/foo.py", "src/foo.py#Bar") is True

    def test_file_is_parent_of_method(self):
        """File reference is parent of method in that file."""
        assert is_parent_of("src/foo.py", "src/foo.py#Bar::baz") is True

    def test_class_is_parent_of_method(self):
        """Class reference is parent of method in that class."""
        assert is_parent_of("src/foo.py#Bar", "src/foo.py#Bar::baz") is True

    def test_class_is_parent_of_nested_class(self):
        """Class is parent of nested class."""
        assert is_parent_of("src/foo.py#Outer", "src/foo.py#Outer::Inner") is True

    def test_nested_class_is_parent_of_deeper_nested(self):
        """Nested class is parent of deeper nested symbol."""
        assert is_parent_of("src/foo.py#A::B", "src/foo.py#A::B::C") is True

    def test_different_classes_not_parent(self):
        """Different classes in same file are not parent/child."""
        assert is_parent_of("src/foo.py#Bar", "src/foo.py#Qux") is False

    def test_different_files_not_parent(self):
        """References to different files are never parent/child."""
        assert is_parent_of("src/foo.py#Bar", "src/baz.py#Bar") is False
        assert is_parent_of("src/foo.py", "src/baz.py") is False

    def test_sibling_methods_not_parent(self):
        """Sibling methods are not parent/child."""
        assert is_parent_of("src/foo.py#Bar::method1", "src/foo.py#Bar::method2") is False

    def test_child_is_not_parent_of_parent(self):
        """Child reference is not parent of its own parent."""
        assert is_parent_of("src/foo.py#Bar::baz", "src/foo.py#Bar") is False

    def test_same_reference_is_parent_of_itself(self):
        """Same reference is considered parent of itself (containment)."""
        assert is_parent_of("src/foo.py#Bar", "src/foo.py#Bar") is True
        assert is_parent_of("src/foo.py", "src/foo.py") is True
