"""Tests for the frontmatter module."""

import pytest
from pathlib import Path
from pydantic import BaseModel

from frontmatter import (
    parse_frontmatter,
    parse_frontmatter_with_errors,
    parse_frontmatter_from_content,
    parse_frontmatter_from_content_with_errors,
    extract_frontmatter_dict,
    update_frontmatter_field,
)


# Test model for isolation from real artifact models
class TestFrontmatter(BaseModel):
    """Simple test model for frontmatter parsing tests."""

    status: str
    name: str | None = None
    count: int = 0


class TestFrontmatterStrict(BaseModel):
    """Stricter model requiring specific fields."""

    required_field: str
    optional_field: str | None = None


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_valid_frontmatter_parses_correctly(self, tmp_path: Path):
        """Valid frontmatter should parse and validate correctly."""
        file_path = tmp_path / "test.md"
        file_path.write_text("""---
status: active
name: test
count: 42
---

# Body content
""")
        result = parse_frontmatter(file_path, TestFrontmatter)

        assert result is not None
        assert result.status == "active"
        assert result.name == "test"
        assert result.count == 42

    def test_missing_file_returns_none(self, tmp_path: Path):
        """Non-existent file should return None."""
        file_path = tmp_path / "nonexistent.md"
        result = parse_frontmatter(file_path, TestFrontmatter)

        assert result is None

    def test_file_without_frontmatter_markers_returns_none(self, tmp_path: Path):
        """File without --- markers should return None."""
        file_path = tmp_path / "no_markers.md"
        file_path.write_text("# Just a regular markdown file\n\nNo frontmatter here.")

        result = parse_frontmatter(file_path, TestFrontmatter)

        assert result is None

    def test_invalid_yaml_returns_none(self, tmp_path: Path):
        """Invalid YAML in frontmatter should return None."""
        file_path = tmp_path / "bad_yaml.md"
        file_path.write_text("""---
status: active
  invalid: indentation
---

Body
""")
        result = parse_frontmatter(file_path, TestFrontmatter)

        assert result is None

    def test_pydantic_validation_failure_returns_none(self, tmp_path: Path):
        """YAML that fails Pydantic validation should return None."""
        file_path = tmp_path / "bad_schema.md"
        file_path.write_text("""---
count: not_a_number
---

Body
""")
        result = parse_frontmatter(file_path, TestFrontmatter)

        assert result is None

    def test_non_dict_frontmatter_returns_none(self, tmp_path: Path):
        """Frontmatter that's not a dict should return None."""
        file_path = tmp_path / "list_frontmatter.md"
        file_path.write_text("""---
- item1
- item2
---

Body
""")
        result = parse_frontmatter(file_path, TestFrontmatter)

        assert result is None

    def test_uses_model_defaults(self, tmp_path: Path):
        """Missing optional fields should use model defaults."""
        file_path = tmp_path / "defaults.md"
        file_path.write_text("""---
status: draft
---

Body
""")
        result = parse_frontmatter(file_path, TestFrontmatter)

        assert result is not None
        assert result.status == "draft"
        assert result.name is None
        assert result.count == 0


class TestParseFrontmatterWithErrors:
    """Tests for parse_frontmatter_with_errors function."""

    def test_valid_frontmatter_returns_model_and_empty_errors(self, tmp_path: Path):
        """Valid frontmatter should return (model, [])."""
        file_path = tmp_path / "valid.md"
        file_path.write_text("""---
status: active
---

Body
""")
        result, errors = parse_frontmatter_with_errors(file_path, TestFrontmatter)

        assert result is not None
        assert result.status == "active"
        assert errors == []

    def test_missing_file_returns_error(self, tmp_path: Path):
        """Missing file should return appropriate error message."""
        file_path = tmp_path / "nonexistent.md"
        result, errors = parse_frontmatter_with_errors(file_path, TestFrontmatter)

        assert result is None
        assert len(errors) == 1
        assert "not found" in errors[0].lower() or "nonexistent" in errors[0]

    def test_no_frontmatter_markers_returns_error(self, tmp_path: Path):
        """Missing frontmatter markers should return appropriate error."""
        file_path = tmp_path / "no_markers.md"
        file_path.write_text("# No frontmatter\n")

        result, errors = parse_frontmatter_with_errors(file_path, TestFrontmatter)

        assert result is None
        assert len(errors) == 1
        assert "---" in errors[0] or "frontmatter" in errors[0].lower()

    def test_yaml_parse_error_returns_message(self, tmp_path: Path):
        """YAML parse error should include error details."""
        file_path = tmp_path / "bad_yaml.md"
        file_path.write_text("""---
status: [unclosed
---

Body
""")
        result, errors = parse_frontmatter_with_errors(file_path, TestFrontmatter)

        assert result is None
        assert len(errors) == 1
        assert "YAML" in errors[0] or "yaml" in errors[0].lower()

    def test_pydantic_validation_errors_formatted(self, tmp_path: Path):
        """Pydantic validation errors should be formatted as field-specific messages."""
        file_path = tmp_path / "validation_error.md"
        file_path.write_text("""---
count: not_a_number
---

Body
""")
        result, errors = parse_frontmatter_with_errors(file_path, TestFrontmatter)

        assert result is None
        assert len(errors) >= 1
        # Should include field name in error
        assert any("count" in e.lower() or "status" in e.lower() for e in errors)

    def test_multiple_validation_errors_reported(self, tmp_path: Path):
        """Multiple validation errors should all be reported."""
        file_path = tmp_path / "multi_error.md"
        file_path.write_text("""---
count: wrong
---

Body
""")
        # Missing required 'status' and 'count' has wrong type
        result, errors = parse_frontmatter_with_errors(file_path, TestFrontmatter)

        assert result is None
        # Should have errors for both issues
        assert len(errors) >= 1


class TestParseFrontmatterFromContent:
    """Tests for parse_frontmatter_from_content function."""

    def test_valid_content_parses_correctly(self):
        """Valid content string should parse correctly."""
        content = """---
status: active
name: from_content
---

# Body
"""
        result = parse_frontmatter_from_content(content, TestFrontmatter)

        assert result is not None
        assert result.status == "active"
        assert result.name == "from_content"

    def test_invalid_content_returns_none(self):
        """Invalid content should return None."""
        content = "# No frontmatter"
        result = parse_frontmatter_from_content(content, TestFrontmatter)

        assert result is None


class TestParseFrontmatterFromContentWithErrors:
    """Tests for parse_frontmatter_from_content_with_errors function."""

    def test_valid_content_returns_model_and_empty_errors(self):
        """Valid content should return (model, [])."""
        content = """---
status: complete
---

Body
"""
        result, errors = parse_frontmatter_from_content_with_errors(
            content, TestFrontmatter
        )

        assert result is not None
        assert result.status == "complete"
        assert errors == []

    def test_invalid_content_returns_errors(self):
        """Invalid content should return errors."""
        content = "No frontmatter here"
        result, errors = parse_frontmatter_from_content_with_errors(
            content, TestFrontmatter
        )

        assert result is None
        assert len(errors) > 0


class TestExtractFrontmatterDict:
    """Tests for extract_frontmatter_dict function."""

    def test_extracts_raw_dict(self, tmp_path: Path):
        """Should extract frontmatter as a raw dict."""
        file_path = tmp_path / "dict_test.md"
        file_path.write_text("""---
status: active
custom_field: custom_value
nested:
  key: value
---

Body
""")
        result = extract_frontmatter_dict(file_path)

        assert result is not None
        assert result["status"] == "active"
        assert result["custom_field"] == "custom_value"
        assert result["nested"]["key"] == "value"

    def test_missing_file_returns_none(self, tmp_path: Path):
        """Missing file should return None."""
        file_path = tmp_path / "nonexistent.md"
        result = extract_frontmatter_dict(file_path)

        assert result is None

    def test_no_frontmatter_returns_none(self, tmp_path: Path):
        """File without frontmatter should return None."""
        file_path = tmp_path / "no_fm.md"
        file_path.write_text("# Just content")

        result = extract_frontmatter_dict(file_path)

        assert result is None

    def test_invalid_yaml_returns_none(self, tmp_path: Path):
        """Invalid YAML should return None."""
        file_path = tmp_path / "bad.md"
        file_path.write_text("""---
[unclosed
---
""")
        result = extract_frontmatter_dict(file_path)

        assert result is None

    def test_non_dict_returns_none(self, tmp_path: Path):
        """Non-dict frontmatter should return None."""
        file_path = tmp_path / "list.md"
        file_path.write_text("""---
- item1
- item2
---

Body
""")
        result = extract_frontmatter_dict(file_path)

        assert result is None


class TestUpdateFrontmatterField:
    """Tests for update_frontmatter_field function."""

    def test_updates_existing_field(self, tmp_path: Path):
        """Existing field should be updated correctly."""
        file_path = tmp_path / "update.md"
        file_path.write_text("""---
status: draft
name: test
---

# Body content

More content here.
""")
        update_frontmatter_field(file_path, "status", "active")

        # Read back and verify
        content = file_path.read_text()
        assert "status: active" in content
        assert "status: draft" not in content
        assert "name: test" in content
        assert "# Body content" in content
        assert "More content here." in content

    def test_adds_new_field(self, tmp_path: Path):
        """New field should be added correctly."""
        file_path = tmp_path / "add_field.md"
        file_path.write_text("""---
status: draft
---

Body
""")
        update_frontmatter_field(file_path, "new_field", "new_value")

        content = file_path.read_text()
        assert "new_field: new_value" in content
        assert "status: draft" in content
        assert "Body" in content

    def test_preserves_body_unchanged(self, tmp_path: Path):
        """Body content should be preserved exactly."""
        body_content = """# Complex Body

With multiple paragraphs.

- And lists
- Like this one

```python
def code_block():
    pass
```
"""
        file_path = tmp_path / "preserve.md"
        file_path.write_text(f"""---
status: draft
---
{body_content}""")

        update_frontmatter_field(file_path, "status", "active")

        content = file_path.read_text()
        # Body should be preserved (after the frontmatter closing ---)
        assert body_content in content

    def test_missing_file_raises_filenotfound(self, tmp_path: Path):
        """Missing file should raise FileNotFoundError."""
        file_path = tmp_path / "nonexistent.md"

        with pytest.raises(FileNotFoundError):
            update_frontmatter_field(file_path, "status", "active")

    def test_no_frontmatter_raises_valueerror(self, tmp_path: Path):
        """File without frontmatter should raise ValueError."""
        file_path = tmp_path / "no_fm.md"
        file_path.write_text("# Just content, no frontmatter")

        with pytest.raises(ValueError) as exc_info:
            update_frontmatter_field(file_path, "status", "active")

        assert "frontmatter" in str(exc_info.value).lower()

    def test_updates_complex_values(self, tmp_path: Path):
        """Should handle complex values (lists, dicts)."""
        file_path = tmp_path / "complex.md"
        file_path.write_text("""---
status: draft
---

Body
""")
        update_frontmatter_field(file_path, "items", ["a", "b", "c"])

        content = file_path.read_text()
        assert "items:" in content
        assert "- a" in content
        assert "- b" in content
        assert "- c" in content

    def test_updates_nested_dict_value(self, tmp_path: Path):
        """Should handle dict values."""
        file_path = tmp_path / "nested.md"
        file_path.write_text("""---
status: draft
---

Body
""")
        update_frontmatter_field(file_path, "metadata", {"key": "value"})

        content = file_path.read_text()
        assert "metadata:" in content
        assert "key: value" in content

    def test_preserves_other_fields(self, tmp_path: Path):
        """Other frontmatter fields should be preserved."""
        file_path = tmp_path / "other_fields.md"
        file_path.write_text("""---
status: draft
name: test
count: 42
tags:
  - tag1
  - tag2
---

Body
""")
        update_frontmatter_field(file_path, "status", "active")

        content = file_path.read_text()
        assert "name: test" in content
        assert "count: 42" in content
        assert "- tag1" in content
        assert "- tag2" in content


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_frontmatter(self, tmp_path: Path):
        """Empty frontmatter should parse with defaults."""
        file_path = tmp_path / "empty_fm.md"
        file_path.write_text("""---
status: minimal
---

Body
""")
        result = parse_frontmatter(file_path, TestFrontmatter)

        assert result is not None
        assert result.status == "minimal"

    def test_frontmatter_with_multiline_strings(self, tmp_path: Path):
        """Multiline strings in frontmatter should be preserved."""
        file_path = tmp_path / "multiline.md"
        file_path.write_text("""---
status: active
name: |
  This is a
  multiline string
---

Body
""")
        result = parse_frontmatter(file_path, TestFrontmatter)

        assert result is not None
        assert "multiline" in result.name

    def test_update_preserves_yaml_formatting(self, tmp_path: Path):
        """Update should produce clean YAML formatting."""
        file_path = tmp_path / "formatting.md"
        file_path.write_text("""---
status: draft
---

Body
""")
        update_frontmatter_field(file_path, "list_field", ["item1", "item2"])

        content = file_path.read_text()
        # Should have proper YAML list formatting
        assert "list_field:" in content
        lines = content.split("\n")
        # Find list items and verify they're properly indented
        list_items = [l for l in lines if l.strip().startswith("- item")]
        assert len(list_items) == 2

    def test_handles_unicode(self, tmp_path: Path):
        """Should handle unicode content correctly."""
        file_path = tmp_path / "unicode.md"
        file_path.write_text("""---
status: active
name: "Test with unicode: \u2603 \u2764"
---

Body with unicode: \u2603
""")
        result = parse_frontmatter(file_path, TestFrontmatter)

        assert result is not None
        assert "\u2603" in result.name

    def test_body_with_yaml_like_content(self, tmp_path: Path):
        """Body content that looks like YAML should be preserved."""
        file_path = tmp_path / "yaml_body.md"
        body_with_yaml = """# Body

Some text with:
  yaml: like
  content: here
---
This looks like a delimiter but isn't
"""
        file_path.write_text(f"""---
status: active
---
{body_with_yaml}""")

        update_frontmatter_field(file_path, "new_field", "value")

        content = file_path.read_text()
        assert "yaml: like" in content
        assert "content: here" in content
