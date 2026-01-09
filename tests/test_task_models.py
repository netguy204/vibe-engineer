"""Tests for cross-repository chunk management models."""

import pytest
from pydantic import ValidationError

from models import TaskConfig, ExternalChunkRef, ChunkDependent


class TestTaskConfig:
    """Tests for the TaskConfig schema."""

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


class TestChunkDependent:
    """Tests for the ChunkDependent schema (chunk GOAL.md frontmatter)."""

    def test_chunk_dependent_rejects_invalid_nested_ref(self):
        """Rejects invalid ExternalChunkRef within dependents."""
        with pytest.raises(ValidationError):
            ChunkDependent(
                dependents=[
                    {"repo": "invalid repo", "chunk": "0001-feature"},
                ]
            )
