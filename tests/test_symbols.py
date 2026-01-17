"""Tests for symbol extraction and reference parsing utilities."""

from pathlib import Path

import pytest

from symbols import extract_symbols, parse_reference, is_parent_of, qualify_ref


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
            assert "TaskConfig::validate_external_artifact_repo" in symbols


class TestParseReference:
    """Tests for parse_reference function with current_project."""

    def test_file_only_reference(self):
        """File-only reference with current_project returns (project, file_path, None)."""
        project, file_path, symbol_path = parse_reference("src/foo.py", current_project="local/proj")
        assert project == "local/proj"
        assert file_path == "src/foo.py"
        assert symbol_path is None

    def test_class_reference(self):
        """Class reference with current_project returns (project, file_path, class_name)."""
        project, file_path, symbol_path = parse_reference("src/foo.py#Bar", current_project="local/proj")
        assert project == "local/proj"
        assert file_path == "src/foo.py"
        assert symbol_path == "Bar"

    def test_method_reference(self):
        """Method reference with current_project returns (project, file_path, class::method)."""
        project, file_path, symbol_path = parse_reference("src/foo.py#Bar::baz", current_project="local/proj")
        assert project == "local/proj"
        assert file_path == "src/foo.py"
        assert symbol_path == "Bar::baz"

    def test_deeply_nested_reference(self):
        """Deeply nested reference parses correctly."""
        project, file_path, symbol_path = parse_reference("src/foo.py#A::B::C::D", current_project="local/proj")
        assert project == "local/proj"
        assert file_path == "src/foo.py"
        assert symbol_path == "A::B::C::D"

    def test_standalone_function_reference(self):
        """Standalone function reference parses correctly."""
        project, file_path, symbol_path = parse_reference("src/utils.py#validate_input", current_project="local/proj")
        assert project == "local/proj"
        assert file_path == "src/utils.py"
        assert symbol_path == "validate_input"

    def test_raises_without_current_project(self):
        """Non-qualified reference without current_project raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_reference("src/foo.py")
        assert "current_project was not provided" in str(exc_info.value)


class TestIsParentOf:
    """Tests for is_parent_of function with qualified refs."""

    def test_file_is_parent_of_class(self):
        """File reference is parent of class in that file."""
        assert is_parent_of("local/proj::src/foo.py", "local/proj::src/foo.py#Bar") is True

    def test_file_is_parent_of_method(self):
        """File reference is parent of method in that file."""
        assert is_parent_of("local/proj::src/foo.py", "local/proj::src/foo.py#Bar::baz") is True

    def test_class_is_parent_of_method(self):
        """Class reference is parent of method in that class."""
        assert is_parent_of("local/proj::src/foo.py#Bar", "local/proj::src/foo.py#Bar::baz") is True

    def test_class_is_parent_of_nested_class(self):
        """Class is parent of nested class."""
        assert is_parent_of("local/proj::src/foo.py#Outer", "local/proj::src/foo.py#Outer::Inner") is True

    def test_nested_class_is_parent_of_deeper_nested(self):
        """Nested class is parent of deeper nested symbol."""
        assert is_parent_of("local/proj::src/foo.py#A::B", "local/proj::src/foo.py#A::B::C") is True

    def test_different_classes_not_parent(self):
        """Different classes in same file are not parent/child."""
        assert is_parent_of("local/proj::src/foo.py#Bar", "local/proj::src/foo.py#Qux") is False

    def test_different_files_not_parent(self):
        """References to different files are never parent/child."""
        assert is_parent_of("local/proj::src/foo.py#Bar", "local/proj::src/baz.py#Bar") is False
        assert is_parent_of("local/proj::src/foo.py", "local/proj::src/baz.py") is False

    def test_sibling_methods_not_parent(self):
        """Sibling methods are not parent/child."""
        assert is_parent_of("local/proj::src/foo.py#Bar::method1", "local/proj::src/foo.py#Bar::method2") is False

    def test_child_is_not_parent_of_parent(self):
        """Child reference is not parent of its own parent."""
        assert is_parent_of("local/proj::src/foo.py#Bar::baz", "local/proj::src/foo.py#Bar") is False

    def test_same_reference_is_parent_of_itself(self):
        """Same reference is considered parent of itself (containment)."""
        assert is_parent_of("local/proj::src/foo.py#Bar", "local/proj::src/foo.py#Bar") is True
        assert is_parent_of("local/proj::src/foo.py", "local/proj::src/foo.py") is True

    def test_unqualified_ref_raises_error(self):
        """Unqualified ref raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            is_parent_of("src/foo.py", "src/foo.py#Bar")
        assert "current_project was not provided" in str(exc_info.value)


# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
class TestParseReferenceWithProjectQualification:
    """Tests for parse_reference with project-qualified paths."""

    def test_project_qualified_file_only(self):
        """Project-qualified file reference returns (project, file_path, None)."""
        project, file_path, symbol_path = parse_reference("acme/proj::src/foo.py")
        assert project == "acme/proj"
        assert file_path == "src/foo.py"
        assert symbol_path is None

    def test_project_qualified_with_class(self):
        """Project-qualified class reference returns all three parts."""
        project, file_path, symbol_path = parse_reference("acme/proj::src/foo.py#Bar")
        assert project == "acme/proj"
        assert file_path == "src/foo.py"
        assert symbol_path == "Bar"

    def test_project_qualified_with_nested_symbol(self):
        """Project-qualified nested symbol reference parses correctly."""
        project, file_path, symbol_path = parse_reference("acme/proj::src/foo.py#Bar::baz")
        assert project == "acme/proj"
        assert file_path == "src/foo.py"
        assert symbol_path == "Bar::baz"

    def test_non_qualified_requires_current_project(self):
        """Non-qualified reference without current_project raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_reference("src/foo.py#Bar")
        assert "current_project was not provided" in str(exc_info.value)

    def test_non_qualified_file_only_requires_current_project(self):
        """Non-qualified file-only reference without current_project raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_reference("src/foo.py")
        assert "current_project was not provided" in str(exc_info.value)

    def test_current_project_inference(self):
        """When current_project is passed, it's used for non-qualified references."""
        project, file_path, symbol_path = parse_reference("src/foo.py#Bar", current_project="acme/proj")
        assert project == "acme/proj"
        assert file_path == "src/foo.py"
        assert symbol_path == "Bar"

    def test_explicit_project_overrides_current_project(self):
        """Explicit project qualifier takes precedence over current_project."""
        project, file_path, symbol_path = parse_reference("other/repo::src/foo.py#Bar", current_project="acme/proj")
        assert project == "other/repo"
        assert file_path == "src/foo.py"
        assert symbol_path == "Bar"

    def test_current_project_with_file_only(self):
        """current_project works with file-only references."""
        project, file_path, symbol_path = parse_reference("src/foo.py", current_project="acme/proj")
        assert project == "acme/proj"
        assert file_path == "src/foo.py"
        assert symbol_path is None


class TestIsParentOfWithProjectContext:
    """Tests for is_parent_of with project-qualified references."""

    def test_same_project_hierarchical_true(self):
        """Same project + hierarchical relationship returns True."""
        assert is_parent_of("acme/proj::src/foo.py#Bar", "acme/proj::src/foo.py#Bar::baz") is True

    def test_same_project_file_parent_of_symbol(self):
        """File reference is parent of symbols in same project."""
        assert is_parent_of("acme/proj::src/foo.py", "acme/proj::src/foo.py#Bar") is True

    def test_different_projects_same_path_false(self):
        """Different projects with same file path are never parent/child."""
        assert is_parent_of("acme/a::src/foo.py#Bar", "acme/b::src/foo.py#Bar") is False

    def test_different_projects_never_overlap(self):
        """Different projects never have parent/child relationship."""
        assert is_parent_of("acme/a::src/foo.py", "acme/b::src/foo.py") is False
        assert is_parent_of("acme/a::src/foo.py#Bar", "acme/b::src/foo.py#Bar::baz") is False

    def test_non_qualified_raises_error(self):
        """Non-qualified refs raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            is_parent_of("src/foo.py#Bar", "src/foo.py#Bar::baz")
        assert "current_project was not provided" in str(exc_info.value)

    def test_qualify_ref_then_compare(self):
        """Use qualify_ref to prepare refs, then compare."""
        # Qualify refs first, then pass to is_parent_of
        ref_a = qualify_ref("src/foo.py#Bar", "acme/proj")
        ref_b = qualify_ref("src/foo.py#Bar::baz", "acme/proj")
        assert is_parent_of(ref_a, ref_b) is True

        ref_c = qualify_ref("src/foo.py", "acme/proj")
        ref_d = qualify_ref("src/foo.py#Bar", "acme/proj")
        assert is_parent_of(ref_c, ref_d) is True

    def test_mixed_qualified_and_unqualified_via_qualify_ref(self):
        """Mixed refs can be compared by qualifying the unqualified one."""
        # Explicit qualified ref
        explicit_ref = "acme/proj::src/foo.py#Bar"
        # Unqualified ref - qualify it to same project
        unqualified_ref = qualify_ref("src/foo.py#Bar::baz", "acme/proj")
        assert is_parent_of(explicit_ref, unqualified_ref) is True

    def test_qualify_ref_preserves_explicit_project(self):
        """qualify_ref preserves explicit project even with different current project."""
        # Explicit project stays, different current project has no effect
        ref = qualify_ref("other/repo::src/foo.py#Bar", "acme/proj")
        assert ref == "other/repo::src/foo.py#Bar"
        # These should not overlap (different projects)
        ref_b = qualify_ref("src/foo.py#Bar::baz", "acme/proj")
        assert is_parent_of(ref, ref_b) is False

    def test_same_project_self_containment(self):
        """Same reference in same project is parent of itself."""
        assert is_parent_of("acme/proj::src/foo.py#Bar", "acme/proj::src/foo.py#Bar") is True


class TestOverlapDetectionAcrossProjects:
    """Integration tests for overlap detection with project-qualified references."""

    def test_refs_from_same_project_overlap(self):
        """Two refs from same project correctly detect overlap."""
        # Same project, hierarchical relationship
        assert is_parent_of("acme/proj::src/foo.py#Bar", "acme/proj::src/foo.py#Bar::baz") is True
        assert is_parent_of("acme/proj::src/foo.py", "acme/proj::src/foo.py#Bar") is True

    def test_refs_from_different_projects_never_overlap(self):
        """Two refs from different projects never overlap, even with identical paths."""
        # Same file path and symbol but different projects
        assert is_parent_of("acme/a::src/foo.py#Bar", "acme/b::src/foo.py#Bar") is False
        assert is_parent_of("acme/a::src/foo.py#Bar", "acme/b::src/foo.py#Bar::baz") is False
        assert is_parent_of("acme/a::src/foo.py", "acme/b::src/foo.py#Bar") is False

    def test_mixed_qualified_and_unqualified_via_qualify_ref(self):
        """Mixed refs can be compared by qualifying the unqualified one."""
        # Unqualified ref qualified to same project - should overlap
        qualified_parent = "acme/proj::src/foo.py#Bar"
        qualified_child = qualify_ref("src/foo.py#Bar::baz", "acme/proj")
        assert is_parent_of(qualified_parent, qualified_child) is True

        # Different projects still don't overlap
        other_parent = "other/repo::src/foo.py#Bar"
        same_child = qualify_ref("src/foo.py#Bar::baz", "acme/proj")
        assert is_parent_of(other_parent, same_child) is False

    def test_both_unqualified_via_qualify_ref(self):
        """Two unqualified refs qualified to same project behave correctly."""
        # Both get qualified to same project, should overlap
        ref_a = qualify_ref("src/foo.py#Bar", "acme/proj")
        ref_b = qualify_ref("src/foo.py#Bar::baz", "acme/proj")
        assert is_parent_of(ref_a, ref_b) is True

    def test_unqualified_refs_raise_error(self):
        """Unqualified refs raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            is_parent_of("src/foo.py#Bar", "src/foo.py#Bar::baz")
        assert "current_project was not provided" in str(exc_info.value)

    def test_no_cross_project_overlap_complex_symbols(self):
        """Complex symbol paths don't overlap across different projects."""
        # Deeply nested symbols in different projects
        assert is_parent_of(
            "org/proj-a::src/module/handler.py#Handler::process::inner",
            "org/proj-b::src/module/handler.py#Handler::process::inner"
        ) is False

    def test_file_level_cross_project_no_overlap(self):
        """File-level references don't overlap across projects."""
        # File reference doesn't contain symbols from different project
        assert is_parent_of("org/a::src/foo.py", "org/b::src/foo.py#Bar") is False
