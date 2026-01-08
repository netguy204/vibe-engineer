"""Tests for task utility functions."""

import pytest
from pydantic import ValidationError

from task_utils import (
    is_task_directory,
    is_external_chunk,
    load_task_config,
    load_external_ref,
)
from models import TaskConfig, ExternalChunkRef


class TestIsTaskDirectory:
    """Tests for is_task_directory detection."""

    def test_is_task_directory_true(self, tmp_path):
        """Returns True when .ve-task.yaml exists."""
        (tmp_path / ".ve-task.yaml").write_text("external_chunk_repo: chunks\n")
        assert is_task_directory(tmp_path) is True

    def test_is_task_directory_false(self, tmp_path):
        """Returns False when .ve-task.yaml absent."""
        assert is_task_directory(tmp_path) is False


class TestIsExternalChunk:
    """Tests for is_external_chunk detection."""

    def test_is_external_chunk_true(self, tmp_path):
        """Returns True when external.yaml exists (and no GOAL.md)."""
        (tmp_path / "external.yaml").write_text("project: other\nchunk: 0001-feature\n")
        assert is_external_chunk(tmp_path) is True

    def test_is_external_chunk_false_normal_chunk(self, tmp_path):
        """Returns False when GOAL.md exists."""
        (tmp_path / "GOAL.md").write_text("# Goal\n")
        assert is_external_chunk(tmp_path) is False

    def test_is_external_chunk_false_empty(self, tmp_path):
        """Returns False when neither exists."""
        assert is_external_chunk(tmp_path) is False


class TestLoadTaskConfig:
    """Tests for load_task_config."""

    def test_load_task_config_valid(self, tmp_path):
        """Loads and returns TaskConfig from valid YAML."""
        config_file = tmp_path / ".ve-task.yaml"
        config_file.write_text(
            "external_chunk_repo: chunks\n"
            "projects:\n"
            "  - repo1\n"
            "  - repo2\n"
        )
        config = load_task_config(tmp_path)
        assert isinstance(config, TaskConfig)
        assert config.external_chunk_repo == "chunks"
        assert config.projects == ["repo1", "repo2"]

    def test_load_task_config_invalid(self, tmp_path):
        """Raises ValidationError for invalid YAML."""
        config_file = tmp_path / ".ve-task.yaml"
        config_file.write_text(
            "external_chunk_repo: chunks\n"
            "projects: []\n"  # Empty projects list is invalid
        )
        with pytest.raises(ValidationError):
            load_task_config(tmp_path)

    def test_load_task_config_missing(self, tmp_path):
        """Raises FileNotFoundError when file missing."""
        with pytest.raises(FileNotFoundError):
            load_task_config(tmp_path)


class TestLoadExternalRef:
    """Tests for load_external_ref."""

    def test_load_external_ref_valid(self, tmp_path):
        """Loads and returns ExternalChunkRef from valid YAML."""
        ref_file = tmp_path / "external.yaml"
        ref_file.write_text(
            "project: other-project\n"
            "chunk: 0001-feature\n"
        )
        ref = load_external_ref(tmp_path)
        assert isinstance(ref, ExternalChunkRef)
        assert ref.project == "other-project"
        assert ref.chunk == "0001-feature"

    def test_load_external_ref_invalid(self, tmp_path):
        """Raises ValidationError for invalid YAML."""
        ref_file = tmp_path / "external.yaml"
        ref_file.write_text(
            "project: invalid project\n"  # Space is invalid
            "chunk: 0001-feature\n"
        )
        with pytest.raises(ValidationError):
            load_external_ref(tmp_path)
