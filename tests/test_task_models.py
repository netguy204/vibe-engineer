"""Tests for cross-repository chunk management models."""

import pytest
from pydantic import ValidationError

from models import TaskConfig, ExternalChunkRef, ChunkDependent


class TestTaskConfig:
    """Tests for the TaskConfig schema."""

    def test_task_config_valid_minimal(self):
        """Accepts minimal valid configuration."""
        config = TaskConfig(
            external_chunk_repo="chunks",
            projects=["repo1"],
        )
        assert config.external_chunk_repo == "chunks"
        assert config.projects == ["repo1"]

    def test_task_config_valid_multiple_projects(self):
        """Accepts multiple projects in list."""
        config = TaskConfig(
            external_chunk_repo="chunks",
            projects=["repo1", "repo2", "repo3"],
        )
        assert len(config.projects) == 3

    def test_task_config_rejects_empty_projects(self):
        """Rejects empty projects list."""
        with pytest.raises(ValidationError):
            TaskConfig(
                external_chunk_repo="chunks",
                projects=[],
            )

    def test_task_config_rejects_invalid_dir_chars(self):
        """Rejects directory names with spaces or special characters."""
        with pytest.raises(ValidationError):
            TaskConfig(
                external_chunk_repo="my chunks",
                projects=["repo1"],
            )

        with pytest.raises(ValidationError):
            TaskConfig(
                external_chunk_repo="chunks",
                projects=["repo@name"],
            )

    def test_task_config_rejects_long_dir_name(self):
        """Rejects directory names >= 32 characters."""
        long_name = "a" * 32
        with pytest.raises(ValidationError):
            TaskConfig(
                external_chunk_repo=long_name,
                projects=["repo1"],
            )

        with pytest.raises(ValidationError):
            TaskConfig(
                external_chunk_repo="chunks",
                projects=[long_name],
            )


class TestExternalChunkRef:
    """Tests for the ExternalChunkRef schema."""

    def test_external_chunk_ref_valid(self):
        """Accepts valid external chunk reference."""
        ref = ExternalChunkRef(
            project="myproject",
            chunk="0001-feature",
        )
        assert ref.project == "myproject"
        assert ref.chunk == "0001-feature"

    def test_external_chunk_ref_rejects_invalid_project(self):
        """Rejects invalid project directory name."""
        with pytest.raises(ValidationError):
            ExternalChunkRef(
                project="my project",
                chunk="0001-feature",
            )

    def test_external_chunk_ref_rejects_invalid_chunk(self):
        """Rejects invalid chunk directory name."""
        with pytest.raises(ValidationError):
            ExternalChunkRef(
                project="myproject",
                chunk="chunk with spaces",
            )

    def test_external_chunk_ref_rejects_long_names(self):
        """Rejects names >= 32 characters."""
        long_name = "a" * 32
        with pytest.raises(ValidationError):
            ExternalChunkRef(
                project=long_name,
                chunk="0001-feature",
            )


class TestChunkDependent:
    """Tests for the ChunkDependent schema (chunk GOAL.md frontmatter)."""

    def test_chunk_dependent_valid_single(self):
        """Accepts single dependent."""
        dep = ChunkDependent(
            dependents=[
                ExternalChunkRef(project="repo1", chunk="0001-feature"),
            ]
        )
        assert len(dep.dependents) == 1

    def test_chunk_dependent_valid_multiple(self):
        """Accepts multiple dependents."""
        dep = ChunkDependent(
            dependents=[
                ExternalChunkRef(project="repo1", chunk="0001-feature"),
                ExternalChunkRef(project="repo2", chunk="0002-bugfix"),
            ]
        )
        assert len(dep.dependents) == 2

    def test_chunk_dependent_accepts_empty_list(self):
        """Accepts empty dependents list (optional field)."""
        dep = ChunkDependent(dependents=[])
        assert dep.dependents == []

    def test_chunk_dependent_accepts_dict_syntax(self):
        """Accepts dict syntax for dependents (Pydantic coercion)."""
        dep = ChunkDependent(
            dependents=[
                {"project": "repo1", "chunk": "0001-feature"},
            ]
        )
        assert dep.dependents[0].project == "repo1"

    def test_chunk_dependent_rejects_invalid_nested_ref(self):
        """Rejects invalid ExternalChunkRef within dependents."""
        with pytest.raises(ValidationError):
            ChunkDependent(
                dependents=[
                    {"project": "invalid project", "chunk": "0001-feature"},
                ]
            )
