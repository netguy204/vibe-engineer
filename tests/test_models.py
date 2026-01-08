"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from models import SymbolicReference


class TestSymbolicReference:
    """Tests for SymbolicReference model."""

    def test_valid_file_only_reference(self):
        """Reference with file path only is valid."""
        ref = SymbolicReference(ref="src/chunks.py", implements="Core chunk logic")
        assert ref.ref == "src/chunks.py"
        assert ref.implements == "Core chunk logic"

    def test_valid_class_reference(self):
        """Reference to a class is valid."""
        ref = SymbolicReference(ref="src/chunks.py#Chunks", implements="Chunk manager")
        assert ref.ref == "src/chunks.py#Chunks"

    def test_valid_method_reference(self):
        """Reference to a method with :: separator is valid."""
        ref = SymbolicReference(
            ref="src/chunks.py#Chunks::create_chunk",
            implements="Chunk creation logic",
        )
        assert ref.ref == "src/chunks.py#Chunks::create_chunk"

    def test_valid_nested_class_reference(self):
        """Reference to nested class is valid."""
        ref = SymbolicReference(
            ref="src/models.py#Outer::Inner::method",
            implements="Nested method",
        )
        assert ref.ref == "src/models.py#Outer::Inner::method"

    def test_valid_standalone_function(self):
        """Reference to standalone function is valid."""
        ref = SymbolicReference(
            ref="src/ve.py#validate_short_name",
            implements="Input validation",
        )
        assert ref.ref == "src/ve.py#validate_short_name"

    def test_invalid_empty_ref(self):
        """Empty ref string is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="", implements="Something")
        assert "ref cannot be empty" in str(exc_info.value)

    def test_invalid_missing_file_path(self):
        """Reference starting with # (missing file path) is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="#SomeClass", implements="Something")
        assert "must start with a file path" in str(exc_info.value)

    def test_invalid_empty_symbol_after_hash(self):
        """Reference with empty symbol after # is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="src/foo.py#", implements="Something")
        assert "symbol path cannot be empty" in str(exc_info.value)

    def test_invalid_empty_implements(self):
        """Empty implements field is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="src/foo.py", implements="")
        assert "implements" in str(exc_info.value).lower()

    def test_invalid_missing_implements(self):
        """Missing implements field is rejected."""
        with pytest.raises(ValidationError):
            SymbolicReference(ref="src/foo.py")

    def test_multiple_hashes_rejected(self):
        """Reference with multiple # characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="src/foo.py#Bar#baz", implements="Something")
        assert "cannot contain multiple #" in str(exc_info.value)

    def test_symbol_with_empty_part_rejected(self):
        """Symbol path with empty part (::Foo or Foo::) is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="src/foo.py#::Foo", implements="Something")
        assert "empty component" in str(exc_info.value).lower()

        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="src/foo.py#Foo::", implements="Something")
        assert "empty component" in str(exc_info.value).lower()
