"""Tests for cross-repository chunk management models."""
# Chunk: docs/chunks/cross_repo_schemas - Validation tests for TaskConfig, ChunkDependent
# Chunk: docs/chunks/consolidate_ext_refs - Validation tests for ExternalArtifactRef

import pytest
from pydantic import ValidationError

from models import TaskConfig, ChunkDependent, ExternalArtifactRef, ArtifactType


class TestTaskConfig:
    """Tests for the TaskConfig schema."""

    def test_task_config_rejects_empty_projects(self):
        """Rejects empty projects list."""
        with pytest.raises(ValidationError):
            TaskConfig(
                external_artifact_repo="acme/chunks",
                projects=[],
            )

    def test_task_config_rejects_missing_org(self):
        """Rejects repo references without org/repo format."""
        with pytest.raises(ValidationError):
            TaskConfig(
                external_artifact_repo="chunks",  # Missing org/
                projects=["acme/repo1"],
            )

        with pytest.raises(ValidationError):
            TaskConfig(
                external_artifact_repo="acme/chunks",
                projects=["repo1"],  # Missing org/
            )

    def test_task_config_rejects_invalid_chars(self):
        """Rejects org or repo names with spaces or special characters."""
        with pytest.raises(ValidationError):
            TaskConfig(
                external_artifact_repo="my org/chunks",  # Space in org
                projects=["acme/repo1"],
            )

        with pytest.raises(ValidationError):
            TaskConfig(
                external_artifact_repo="acme/chunks",
                projects=["acme/repo@name"],  # @ in repo
            )

    def test_task_config_rejects_multiple_slashes(self):
        """Rejects references with multiple slashes."""
        with pytest.raises(ValidationError):
            TaskConfig(
                external_artifact_repo="acme/sub/chunks",
                projects=["acme/repo1"],
            )


class TestChunkDependent:
    """Tests for the ChunkDependent schema (chunk GOAL.md frontmatter)."""

    def test_chunk_dependent_rejects_invalid_nested_ref(self):
        """Rejects invalid ExternalArtifactRef within dependents."""
        with pytest.raises(ValidationError):
            ChunkDependent(
                dependents=[
                    {"artifact_type": "chunk", "repo": "invalid repo", "artifact_id": "my_feature"},
                ]
            )

    def test_chunk_dependent_accepts_valid_ref(self):
        """Accepts valid ExternalArtifactRef within dependents."""
        dependent = ChunkDependent(
            dependents=[
                {"artifact_type": "chunk", "repo": "acme/project", "artifact_id": "my_feature"},
            ]
        )
        assert len(dependent.dependents) == 1
        assert dependent.dependents[0].artifact_type == ArtifactType.CHUNK
        assert dependent.dependents[0].artifact_id == "my_feature"


# Chunk: docs/chunks/consolidate_ext_refs - Tests for ExternalArtifactRef model
class TestExternalArtifactRef:
    """Tests for the ExternalArtifactRef schema."""

    def test_external_artifact_ref_requires_artifact_type(self):
        """Rejects missing artifact_type."""
        with pytest.raises(ValidationError):
            ExternalArtifactRef(
                repo="acme/myproject",
                artifact_id="my_feature",
            )

    def test_external_artifact_ref_rejects_invalid_artifact_type(self):
        """Rejects unknown artifact type."""
        with pytest.raises(ValidationError):
            ExternalArtifactRef(
                artifact_type="invalid_type",
                repo="acme/myproject",
                artifact_id="my_feature",
            )

    def test_external_artifact_ref_requires_artifact_id(self):
        """Rejects missing artifact_id."""
        with pytest.raises(ValidationError):
            ExternalArtifactRef(
                artifact_type=ArtifactType.CHUNK,
                repo="acme/myproject",
            )

    def test_external_artifact_ref_rejects_invalid_artifact_id(self):
        """Rejects invalid artifact_id format."""
        with pytest.raises(ValidationError):
            ExternalArtifactRef(
                artifact_type=ArtifactType.CHUNK,
                repo="acme/myproject",
                artifact_id="invalid artifact id",  # Spaces not allowed
            )

    def test_external_artifact_ref_valid_chunk(self):
        """Accepts valid chunk reference."""
        ref = ExternalArtifactRef(
            artifact_type=ArtifactType.CHUNK,
            repo="acme/myproject",
            artifact_id="my_feature",
        )
        assert ref.artifact_type == ArtifactType.CHUNK
        assert ref.artifact_id == "my_feature"
        assert ref.repo == "acme/myproject"

    def test_external_artifact_ref_valid_narrative(self):
        """Accepts valid narrative reference."""
        ref = ExternalArtifactRef(
            artifact_type=ArtifactType.NARRATIVE,
            repo="acme/myproject",
            artifact_id="user_auth_narrative",
        )
        assert ref.artifact_type == ArtifactType.NARRATIVE
        assert ref.artifact_id == "user_auth_narrative"

    def test_external_artifact_ref_valid_investigation(self):
        """Accepts valid investigation reference."""
        ref = ExternalArtifactRef(
            artifact_type=ArtifactType.INVESTIGATION,
            repo="acme/myproject",
            artifact_id="memory_leak_investigation",
        )
        assert ref.artifact_type == ArtifactType.INVESTIGATION

    def test_external_artifact_ref_valid_subsystem(self):
        """Accepts valid subsystem reference."""
        ref = ExternalArtifactRef(
            artifact_type=ArtifactType.SUBSYSTEM,
            repo="acme/myproject",
            artifact_id="auth_subsystem",
        )
        assert ref.artifact_type == ArtifactType.SUBSYSTEM

    def test_external_artifact_ref_rejects_invalid_repo(self):
        """Rejects repo without org/repo format."""
        with pytest.raises(ValidationError):
            ExternalArtifactRef(
                artifact_type=ArtifactType.CHUNK,
                repo="myproject",  # Missing org/
                artifact_id="my_feature",
            )

    def test_external_artifact_ref_rejects_invalid_pinned(self):
        """Rejects pinned SHA that isn't 40 hex characters."""
        with pytest.raises(ValidationError):
            ExternalArtifactRef(
                artifact_type=ArtifactType.CHUNK,
                repo="acme/myproject",
                artifact_id="my_feature",
                pinned="abc123",  # Too short
            )

    def test_external_artifact_ref_with_all_fields(self):
        """Accepts reference with all optional fields."""
        ref = ExternalArtifactRef(
            artifact_type=ArtifactType.CHUNK,
            repo="acme/myproject",
            artifact_id="my_feature",
            track="main",
            pinned="a" * 40,
            created_after=["previous_chunk"],
        )
        assert ref.track == "main"
        assert ref.pinned == "a" * 40
        assert ref.created_after == ["previous_chunk"]

    def test_external_artifact_ref_accepts_legacy_chunk_id_format(self):
        """Accepts legacy NNNN-short_name format for artifact_id."""
        ref = ExternalArtifactRef(
            artifact_type=ArtifactType.CHUNK,
            repo="acme/myproject",
            artifact_id="0001-my_feature",
        )
        assert ref.artifact_id == "0001-my_feature"
