"""Tests for error surfacing in artifact frontmatter parsers.

# Chunk: docs/chunks/validation_error_surface - Test error surfacing methods
"""

import pytest
from pathlib import Path
from pydantic import BaseModel
from enum import StrEnum

from artifact_manager import ArtifactManager


# Test fixtures - minimal concrete implementation for testing
# Prefix with underscore to avoid pytest collection warnings
class _ArtifactStatus(StrEnum):
    """Status values for test artifacts."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"


VALID_TEST_TRANSITIONS: dict[_ArtifactStatus, set[_ArtifactStatus]] = {
    _ArtifactStatus.DRAFT: {_ArtifactStatus.ACTIVE},
    _ArtifactStatus.ACTIVE: set(),
}


class _ArtifactFrontmatter(BaseModel):
    """Test frontmatter model."""
    status: _ArtifactStatus
    title: str | None = None
    count: int = 0


class ConcreteTestManager(ArtifactManager[_ArtifactFrontmatter, _ArtifactStatus]):
    """Concrete implementation for testing ArtifactManager."""

    @property
    def artifact_dir_name(self) -> str:
        return "test_artifacts"

    @property
    def main_filename(self) -> str:
        return "OVERVIEW.md"

    @property
    def frontmatter_model_class(self) -> type[_ArtifactFrontmatter]:
        return _ArtifactFrontmatter

    @property
    def status_enum(self) -> type[_ArtifactStatus]:
        return _ArtifactStatus

    @property
    def transition_map(self) -> dict[_ArtifactStatus, set[_ArtifactStatus]]:
        return VALID_TEST_TRANSITIONS


class TestParseFrontmatterWithErrors:
    """Tests for ArtifactManager.parse_frontmatter_with_errors()."""

    def test_returns_errors_for_missing_artifact(self, tmp_path: Path):
        """Error message mentions artifact name when artifact doesn't exist."""
        manager = ConcreteTestManager(tmp_path)
        result, errors = manager.parse_frontmatter_with_errors("nonexistent")

        assert result is None
        assert len(errors) == 1
        assert "nonexistent" in errors[0]
        # Should include human-readable artifact type name
        assert "Test_artifact" in errors[0]

    def test_returns_errors_for_invalid_yaml(self, tmp_path: Path):
        """YAML parsing error is reported."""
        manager = ConcreteTestManager(tmp_path)
        artifact_dir = tmp_path / "docs" / "test_artifacts" / "my_artifact"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "OVERVIEW.md").write_text("""---
status: [unclosed
---

# Content
""")

        result, errors = manager.parse_frontmatter_with_errors("my_artifact")

        assert result is None
        assert len(errors) == 1
        assert "YAML" in errors[0] or "yaml" in errors[0].lower()

    def test_returns_field_errors_for_validation_failure(self, tmp_path: Path):
        """Pydantic field errors are formatted with field names."""
        manager = ConcreteTestManager(tmp_path)
        artifact_dir = tmp_path / "docs" / "test_artifacts" / "my_artifact"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "OVERVIEW.md").write_text("""---
status: INVALID_STATUS
count: not_a_number
---

# Content
""")

        result, errors = manager.parse_frontmatter_with_errors("my_artifact")

        assert result is None
        assert len(errors) >= 1
        # Should include field names in errors
        error_text = " ".join(errors).lower()
        assert "status" in error_text or "count" in error_text

    def test_returns_empty_errors_on_success(self, tmp_path: Path):
        """Successful parse returns (model, [])."""
        manager = ConcreteTestManager(tmp_path)
        artifact_dir = tmp_path / "docs" / "test_artifacts" / "my_artifact"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "OVERVIEW.md").write_text("""---
status: DRAFT
title: Test Title
---

# Content
""")

        result, errors = manager.parse_frontmatter_with_errors("my_artifact")

        assert result is not None
        assert result.status == _ArtifactStatus.DRAFT
        assert result.title == "Test Title"
        assert errors == []

    def test_returns_errors_for_missing_frontmatter_markers(self, tmp_path: Path):
        """Missing frontmatter markers are reported."""
        manager = ConcreteTestManager(tmp_path)
        artifact_dir = tmp_path / "docs" / "test_artifacts" / "my_artifact"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "OVERVIEW.md").write_text("# No frontmatter here")

        result, errors = manager.parse_frontmatter_with_errors("my_artifact")

        assert result is None
        assert len(errors) == 1
        assert "---" in errors[0] or "frontmatter" in errors[0].lower()


class TestNarrativeFrontmatterWithErrors:
    """Tests for Narratives.parse_narrative_frontmatter_with_errors()."""

    def test_handles_legacy_chunks_field(self, tmp_path: Path):
        """Legacy 'chunks' field works with error surfacing."""
        from narratives import Narratives

        narratives = Narratives(tmp_path)
        narrative_dir = tmp_path / "docs" / "narratives" / "my_narrative"
        narrative_dir.mkdir(parents=True)
        # Use legacy 'chunks' field instead of 'proposed_chunks'
        (narrative_dir / "OVERVIEW.md").write_text("""---
status: DRAFTING
chunks:
  - prompt: First chunk
    chunk_directory: null
  - prompt: Second chunk
    chunk_directory: null
created_after: []
---

# Overview
""")

        result, errors = narratives.parse_narrative_frontmatter_with_errors("my_narrative")

        assert result is not None
        assert errors == []
        assert len(result.proposed_chunks) == 2

    def test_returns_errors_for_missing_narrative(self, tmp_path: Path):
        """Error message mentions narrative name when not found."""
        from narratives import Narratives

        narratives = Narratives(tmp_path)
        result, errors = narratives.parse_narrative_frontmatter_with_errors("nonexistent")

        assert result is None
        assert len(errors) == 1
        assert "nonexistent" in errors[0]
        assert "Narrative" in errors[0]

    def test_returns_validation_errors(self, tmp_path: Path):
        """Validation errors are formatted and returned."""
        from narratives import Narratives

        narratives = Narratives(tmp_path)
        narrative_dir = tmp_path / "docs" / "narratives" / "my_narrative"
        narrative_dir.mkdir(parents=True)
        (narrative_dir / "OVERVIEW.md").write_text("""---
status: INVALID_STATUS
---

# Overview
""")

        result, errors = narratives.parse_narrative_frontmatter_with_errors("my_narrative")

        assert result is None
        assert len(errors) >= 1


class TestInvestigationFrontmatterWithErrors:
    """Tests for Investigations.parse_investigation_frontmatter_with_errors()."""

    def test_returns_errors_for_missing_investigation(self, tmp_path: Path):
        """Error message mentions investigation name when not found."""
        from investigations import Investigations

        investigations = Investigations(tmp_path)
        result, errors = investigations.parse_investigation_frontmatter_with_errors("nonexistent")

        assert result is None
        assert len(errors) == 1
        assert "nonexistent" in errors[0]
        assert "Investigation" in errors[0]

    def test_returns_empty_errors_on_success(self, tmp_path: Path):
        """Successful parse returns (model, [])."""
        from investigations import Investigations

        investigations = Investigations(tmp_path)
        investigation_dir = tmp_path / "docs" / "investigations" / "my_investigation"
        investigation_dir.mkdir(parents=True)
        (investigation_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
proposed_chunks: []
created_after: []
---

# Overview
""")

        result, errors = investigations.parse_investigation_frontmatter_with_errors("my_investigation")

        assert result is not None
        assert errors == []


class TestSubsystemFrontmatterWithErrors:
    """Tests for Subsystems.parse_subsystem_frontmatter_with_errors()."""

    def test_returns_errors_for_missing_subsystem(self, tmp_path: Path):
        """Error message mentions subsystem name when not found."""
        from subsystems import Subsystems

        subsystems = Subsystems(tmp_path)
        result, errors = subsystems.parse_subsystem_frontmatter_with_errors("nonexistent")

        assert result is None
        assert len(errors) == 1
        assert "nonexistent" in errors[0]
        assert "Subsystem" in errors[0]

    def test_returns_empty_errors_on_success(self, tmp_path: Path):
        """Successful parse returns (model, [])."""
        from subsystems import Subsystems

        subsystems = Subsystems(tmp_path)
        subsystem_dir = tmp_path / "docs" / "subsystems" / "my_subsystem"
        subsystem_dir.mkdir(parents=True)
        (subsystem_dir / "OVERVIEW.md").write_text("""---
status: DISCOVERING
chunks: []
code_references: []
created_after: []
---

# Overview
""")

        result, errors = subsystems.parse_subsystem_frontmatter_with_errors("my_subsystem")

        assert result is not None
        assert errors == []


class TestPlanHasContentExceptionHandling:
    """Tests for plan_has_content exception handling."""

    def test_returns_false_for_missing_file(self, tmp_path: Path):
        """FileNotFoundError returns False."""
        from chunks import plan_has_content

        plan_path = tmp_path / "NONEXISTENT.md"
        assert plan_has_content(plan_path) is False

    def test_returns_false_for_permission_error(self, tmp_path: Path):
        """PermissionError returns False."""
        import os
        from chunks import plan_has_content

        plan_path = tmp_path / "PLAN.md"
        plan_path.write_text("""# Plan

## Approach

Content here.
""")
        # Remove read permissions
        os.chmod(plan_path, 0o000)

        try:
            assert plan_has_content(plan_path) is False
        finally:
            # Restore permissions so cleanup works
            os.chmod(plan_path, 0o644)

    def test_propagates_unexpected_errors(self, tmp_path: Path):
        """Unexpected errors propagate to caller.

        We verify this by creating a file with invalid UTF-8 encoding,
        which should raise UnicodeDecodeError since plan_has_content
        no longer catches all exceptions.
        """
        from chunks import plan_has_content

        plan_path = tmp_path / "PLAN.md"
        # Write invalid UTF-8 bytes directly
        plan_path.write_bytes(b"# Plan\n\n## Approach\n\nContent \xff\xfe here.\n")

        # Should raise UnicodeDecodeError since we're not catching it anymore
        with pytest.raises(UnicodeDecodeError):
            plan_has_content(plan_path)


class TestBackwardCompatibility:
    """Tests ensuring backward compatibility of regular parsers."""

    def test_parse_frontmatter_still_returns_none_on_failure(self, tmp_path: Path):
        """Regular parse_frontmatter() continues to return None on failure."""
        manager = ConcreteTestManager(tmp_path)
        result = manager.parse_frontmatter("nonexistent")
        assert result is None

    def test_parse_narrative_frontmatter_still_returns_none_on_failure(self, tmp_path: Path):
        """Regular parse_narrative_frontmatter() continues to return None on failure."""
        from narratives import Narratives

        narratives = Narratives(tmp_path)
        result = narratives.parse_narrative_frontmatter("nonexistent")
        assert result is None

    def test_parse_investigation_frontmatter_still_returns_none_on_failure(self, tmp_path: Path):
        """Regular parse_investigation_frontmatter() continues to return None on failure."""
        from investigations import Investigations

        investigations = Investigations(tmp_path)
        result = investigations.parse_investigation_frontmatter("nonexistent")
        assert result is None

    def test_parse_subsystem_frontmatter_still_returns_none_on_failure(self, tmp_path: Path):
        """Regular parse_subsystem_frontmatter() continues to return None on failure."""
        from subsystems import Subsystems

        subsystems = Subsystems(tmp_path)
        result = subsystems.parse_subsystem_frontmatter("nonexistent")
        assert result is None
