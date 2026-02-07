"""Tests for ArtifactManager abstract base class."""
# Chunk: docs/chunks/artifact_manager_base - ArtifactManager base class tests

import pytest
from pathlib import Path
from pydantic import BaseModel
from enum import StrEnum

from artifact_manager import ArtifactManager


# Test fixtures - minimal concrete implementation for testing
class TestStatus(StrEnum):
    """Status values for test artifacts."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


VALID_TEST_TRANSITIONS: dict[TestStatus, set[TestStatus]] = {
    TestStatus.DRAFT: {TestStatus.ACTIVE},
    TestStatus.ACTIVE: {TestStatus.ARCHIVED},
    TestStatus.ARCHIVED: set(),  # Terminal state
}


class TestFrontmatter(BaseModel):
    """Test frontmatter model."""
    status: TestStatus
    title: str | None = None


class ConcreteTestManager(ArtifactManager[TestFrontmatter, TestStatus]):
    """Concrete implementation for testing ArtifactManager."""

    @property
    def artifact_dir_name(self) -> str:
        return "test_artifacts"

    @property
    def main_filename(self) -> str:
        return "OVERVIEW.md"

    @property
    def frontmatter_model_class(self) -> type[TestFrontmatter]:
        return TestFrontmatter

    @property
    def status_enum(self) -> type[TestStatus]:
        return TestStatus

    @property
    def transition_map(self) -> dict[TestStatus, set[TestStatus]]:
        return VALID_TEST_TRANSITIONS


class TestArtifactManagerBase:
    """Tests for ArtifactManager base class."""

    def test_artifact_dir_property(self, tmp_path):
        """artifact_dir returns correct path."""
        manager = ConcreteTestManager(tmp_path)
        assert manager.artifact_dir == tmp_path / "docs" / "test_artifacts"

    def test_enumerate_artifacts_empty(self, tmp_path):
        """enumerate_artifacts returns empty list when no artifacts exist."""
        manager = ConcreteTestManager(tmp_path)
        assert manager.enumerate_artifacts() == []

    def test_enumerate_artifacts_finds_directories(self, tmp_path):
        """enumerate_artifacts finds artifact directories."""
        manager = ConcreteTestManager(tmp_path)
        artifacts_dir = tmp_path / "docs" / "test_artifacts"
        artifacts_dir.mkdir(parents=True)
        (artifacts_dir / "artifact_one").mkdir()
        (artifacts_dir / "artifact_two").mkdir()
        # Files should not be included
        (artifacts_dir / "not_a_dir.txt").write_text("file")

        result = manager.enumerate_artifacts()
        assert sorted(result) == ["artifact_one", "artifact_two"]

    def test_get_artifact_path(self, tmp_path):
        """get_artifact_path returns correct path."""
        manager = ConcreteTestManager(tmp_path)
        path = manager.get_artifact_path("my_artifact")
        assert path == tmp_path / "docs" / "test_artifacts" / "my_artifact"

    def test_get_main_file_path(self, tmp_path):
        """get_main_file_path returns correct path."""
        manager = ConcreteTestManager(tmp_path)
        path = manager.get_main_file_path("my_artifact")
        assert path == tmp_path / "docs" / "test_artifacts" / "my_artifact" / "OVERVIEW.md"

    def test_parse_frontmatter_valid(self, tmp_path):
        """parse_frontmatter parses valid frontmatter."""
        manager = ConcreteTestManager(tmp_path)
        artifact_dir = tmp_path / "docs" / "test_artifacts" / "my_artifact"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "OVERVIEW.md").write_text(
            "---\nstatus: DRAFT\ntitle: Test\n---\n\n# Content"
        )

        result = manager.parse_frontmatter("my_artifact")
        assert result is not None
        assert result.status == TestStatus.DRAFT
        assert result.title == "Test"

    def test_parse_frontmatter_missing_file(self, tmp_path):
        """parse_frontmatter returns None for missing file."""
        manager = ConcreteTestManager(tmp_path)
        result = manager.parse_frontmatter("nonexistent")
        assert result is None

    def test_get_status_returns_status(self, tmp_path):
        """get_status returns the current status."""
        manager = ConcreteTestManager(tmp_path)
        artifact_dir = tmp_path / "docs" / "test_artifacts" / "my_artifact"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "OVERVIEW.md").write_text("---\nstatus: ACTIVE\n---\n")

        status = manager.get_status("my_artifact")
        assert status == TestStatus.ACTIVE

    def test_get_status_raises_for_missing(self, tmp_path):
        """get_status raises ValueError for missing artifact."""
        manager = ConcreteTestManager(tmp_path)
        with pytest.raises(ValueError) as exc_info:
            manager.get_status("nonexistent")
        # Uses artifact_type_name for human-readable error (Test_artifact)
        assert "Test_artifact 'nonexistent' not found" in str(exc_info.value)

    def test_update_status_valid_transition(self, tmp_path):
        """update_status updates status on valid transition."""
        manager = ConcreteTestManager(tmp_path)
        artifact_dir = tmp_path / "docs" / "test_artifacts" / "my_artifact"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "OVERVIEW.md").write_text("---\nstatus: DRAFT\n---\n\n# Body")

        old, new = manager.update_status("my_artifact", TestStatus.ACTIVE)
        assert old == TestStatus.DRAFT
        assert new == TestStatus.ACTIVE

        # Verify the file was updated
        new_status = manager.get_status("my_artifact")
        assert new_status == TestStatus.ACTIVE

    def test_update_status_invalid_transition_raises(self, tmp_path):
        """update_status raises ValueError on invalid transition."""
        manager = ConcreteTestManager(tmp_path)
        artifact_dir = tmp_path / "docs" / "test_artifacts" / "my_artifact"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "OVERVIEW.md").write_text("---\nstatus: DRAFT\n---\n")

        with pytest.raises(ValueError) as exc_info:
            # DRAFT -> ARCHIVED is not valid
            manager.update_status("my_artifact", TestStatus.ARCHIVED)
        assert "Cannot transition from DRAFT to ARCHIVED" in str(exc_info.value)

    def test_update_status_terminal_state_raises(self, tmp_path):
        """update_status raises for transition from terminal state."""
        manager = ConcreteTestManager(tmp_path)
        artifact_dir = tmp_path / "docs" / "test_artifacts" / "my_artifact"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "OVERVIEW.md").write_text("---\nstatus: ARCHIVED\n---\n")

        with pytest.raises(ValueError) as exc_info:
            manager.update_status("my_artifact", TestStatus.ACTIVE)
        assert "terminal state" in str(exc_info.value).lower()

    def test_update_frontmatter_updates_field(self, tmp_path):
        """_update_frontmatter updates a single field correctly."""
        manager = ConcreteTestManager(tmp_path)
        artifact_dir = tmp_path / "docs" / "test_artifacts" / "my_artifact"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "OVERVIEW.md").write_text(
            "---\nstatus: DRAFT\ntitle: Old Title\n---\n\n# Body"
        )

        manager._update_frontmatter("my_artifact", "title", "New Title")

        result = manager.parse_frontmatter("my_artifact")
        assert result is not None
        assert result.title == "New Title"
        assert result.status == TestStatus.DRAFT  # Unchanged
