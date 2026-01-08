"""Tests for cross-repository chunk management models."""

import pytest
from pydantic import ValidationError

from models import TaskConfig, ExternalChunkRef, ChunkDependent


class TestTaskConfig:
    """Tests for the TaskConfig schema."""

    def test_task_config_valid_minimal(self):
        """Accepts minimal valid configuration with org/repo format."""
        config = TaskConfig(
            external_chunk_repo="acme/chunks",
            projects=["acme/repo1"],
        )
        assert config.external_chunk_repo == "acme/chunks"
        assert config.projects == ["acme/repo1"]

    def test_task_config_valid_multiple_projects(self):
        """Accepts multiple projects in list."""
        config = TaskConfig(
            external_chunk_repo="acme/chunks",
            projects=["acme/repo1", "acme/repo2", "other-org/repo3"],
        )
        assert len(config.projects) == 3

    def test_task_config_rejects_empty_projects(self):
        """Rejects empty projects list."""
        with pytest.raises(ValidationError):
            TaskConfig(
                external_chunk_repo="acme/chunks",
                projects=[],
            )

    def test_task_config_rejects_missing_org(self):
        """Rejects repo references without org/repo format."""
        with pytest.raises(ValidationError):
            TaskConfig(
                external_chunk_repo="chunks",  # Missing org/
                projects=["acme/repo1"],
            )

        with pytest.raises(ValidationError):
            TaskConfig(
                external_chunk_repo="acme/chunks",
                projects=["repo1"],  # Missing org/
            )

    def test_task_config_rejects_invalid_chars(self):
        """Rejects org or repo names with spaces or special characters."""
        with pytest.raises(ValidationError):
            TaskConfig(
                external_chunk_repo="my org/chunks",  # Space in org
                projects=["acme/repo1"],
            )

        with pytest.raises(ValidationError):
            TaskConfig(
                external_chunk_repo="acme/chunks",
                projects=["acme/repo@name"],  # @ in repo
            )

    def test_task_config_rejects_multiple_slashes(self):
        """Rejects references with multiple slashes."""
        with pytest.raises(ValidationError):
            TaskConfig(
                external_chunk_repo="acme/sub/chunks",
                projects=["acme/repo1"],
            )


class TestExternalChunkRef:
    """Tests for the ExternalChunkRef schema."""

    def test_external_chunk_ref_valid_minimal(self):
        """Accepts valid external chunk reference with org/repo format."""
        ref = ExternalChunkRef(
            repo="acme/myproject",
            chunk="0001-feature",
        )
        assert ref.repo == "acme/myproject"
        assert ref.chunk == "0001-feature"
        assert ref.track is None
        assert ref.pinned is None

    def test_external_chunk_ref_valid_with_versioning(self):
        """Accepts external chunk reference with track and pinned."""
        ref = ExternalChunkRef(
            repo="acme/chunks",
            chunk="0001-feature",
            track="main",
            pinned="a" * 40,
        )
        assert ref.repo == "acme/chunks"
        assert ref.chunk == "0001-feature"
        assert ref.track == "main"
        assert ref.pinned == "a" * 40

    def test_external_chunk_ref_rejects_missing_org(self):
        """Rejects repo without org/repo format."""
        with pytest.raises(ValidationError):
            ExternalChunkRef(
                repo="myproject",  # Missing org/
                chunk="0001-feature",
            )

    def test_external_chunk_ref_rejects_invalid_repo_chars(self):
        """Rejects repo with spaces or special characters."""
        with pytest.raises(ValidationError):
            ExternalChunkRef(
                repo="my org/project",  # Space in org
                chunk="0001-feature",
            )

    def test_external_chunk_ref_rejects_invalid_chunk(self):
        """Rejects invalid chunk directory name."""
        with pytest.raises(ValidationError):
            ExternalChunkRef(
                repo="acme/myproject",
                chunk="chunk with spaces",
            )

    def test_external_chunk_ref_rejects_invalid_pinned(self):
        """Rejects pinned SHA that isn't 40 hex characters."""
        with pytest.raises(ValidationError):
            ExternalChunkRef(
                repo="acme/myproject",
                chunk="0001-feature",
                pinned="abc123",  # Too short
            )

        with pytest.raises(ValidationError):
            ExternalChunkRef(
                repo="acme/myproject",
                chunk="0001-feature",
                pinned="G" * 40,  # Invalid hex character
            )

    def test_external_chunk_ref_accepts_valid_pinned(self):
        """Accepts valid 40-character hex SHA."""
        ref = ExternalChunkRef(
            repo="acme/myproject",
            chunk="0001-feature",
            pinned="0123456789abcdef0123456789abcdef01234567",
        )
        assert ref.pinned == "0123456789abcdef0123456789abcdef01234567"


class TestChunkDependent:
    """Tests for the ChunkDependent schema (chunk GOAL.md frontmatter)."""

    def test_chunk_dependent_valid_single(self):
        """Accepts single dependent."""
        dep = ChunkDependent(
            dependents=[
                ExternalChunkRef(repo="acme/repo1", chunk="0001-feature"),
            ]
        )
        assert len(dep.dependents) == 1

    def test_chunk_dependent_valid_multiple(self):
        """Accepts multiple dependents."""
        dep = ChunkDependent(
            dependents=[
                ExternalChunkRef(repo="acme/repo1", chunk="0001-feature"),
                ExternalChunkRef(repo="acme/repo2", chunk="0002-bugfix"),
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
                {"repo": "acme/repo1", "chunk": "0001-feature"},
            ]
        )
        assert dep.dependents[0].repo == "acme/repo1"

    def test_chunk_dependent_rejects_invalid_nested_ref(self):
        """Rejects invalid ExternalChunkRef within dependents."""
        with pytest.raises(ValidationError):
            ChunkDependent(
                dependents=[
                    {"repo": "invalid repo", "chunk": "0001-feature"},
                ]
            )
