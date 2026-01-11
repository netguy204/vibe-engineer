"""Tests for task utility functions."""

import pytest
from pydantic import ValidationError

from task_utils import (
    is_task_directory,
    is_external_chunk,
    load_task_config,
    load_external_ref,
    resolve_repo_directory,
    resolve_project_ref,
    get_next_chunk_id,
    create_external_yaml,
    add_dependents_to_chunk,
    update_frontmatter_field,
)
from models import TaskConfig, ExternalArtifactRef, ArtifactType


class TestIsTaskDirectory:
    """Tests for is_task_directory detection."""

    def test_is_task_directory_true(self, tmp_path):
        """Returns True when .ve-task.yaml exists."""
        (tmp_path / ".ve-task.yaml").write_text("external_artifact_repo: acme/chunks\n")
        assert is_task_directory(tmp_path) is True

    def test_is_task_directory_false(self, tmp_path):
        """Returns False when .ve-task.yaml absent."""
        assert is_task_directory(tmp_path) is False


class TestIsExternalChunk:
    """Tests for is_external_chunk detection."""

    def test_is_external_chunk_true(self, tmp_path):
        """Returns True when external.yaml exists (and no GOAL.md)."""
        (tmp_path / "external.yaml").write_text("repo: acme/other\nchunk: 0001-feature\n")
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
            "external_artifact_repo: acme/chunks\n"
            "projects:\n"
            "  - acme/repo1\n"
            "  - acme/repo2\n"
        )
        config = load_task_config(tmp_path)
        assert isinstance(config, TaskConfig)
        assert config.external_artifact_repo == "acme/chunks"
        assert config.projects == ["acme/repo1", "acme/repo2"]

    def test_load_task_config_invalid(self, tmp_path):
        """Raises ValidationError for invalid YAML."""
        config_file = tmp_path / ".ve-task.yaml"
        config_file.write_text(
            "external_artifact_repo: acme/chunks\n"
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
        """Loads and returns ExternalArtifactRef from valid YAML."""
        ref_file = tmp_path / "external.yaml"
        ref_file.write_text(
            "artifact_type: chunk\n"
            "artifact_id: my_feature\n"
            "repo: acme/other-project\n"
        )
        ref = load_external_ref(tmp_path)
        assert isinstance(ref, ExternalArtifactRef)
        assert ref.repo == "acme/other-project"
        assert ref.artifact_id == "my_feature"
        assert ref.artifact_type == ArtifactType.CHUNK

    def test_load_external_ref_with_versioning(self, tmp_path):
        """Loads external ref with track and pinned fields."""
        ref_file = tmp_path / "external.yaml"
        ref_file.write_text(
            "artifact_type: chunk\n"
            "artifact_id: my_feature\n"
            "repo: acme/chunks\n"
            "track: main\n"
            "pinned: " + "a" * 40 + "\n"
        )
        ref = load_external_ref(tmp_path)
        assert ref.track == "main"
        assert ref.pinned == "a" * 40

    def test_load_external_ref_invalid(self, tmp_path):
        """Raises ValidationError for invalid YAML."""
        ref_file = tmp_path / "external.yaml"
        ref_file.write_text(
            "artifact_type: chunk\n"
            "artifact_id: my_feature\n"
            "repo: invalid repo/project\n"  # Space is invalid
        )
        with pytest.raises(ValidationError):
            load_external_ref(tmp_path)


# Chunk: docs/chunks/accept_full_artifact_paths - Tests for flexible project resolution
class TestResolveProjectRef:
    """Tests for resolve_project_ref."""

    def test_full_org_repo_found(self):
        """cloudcapitalco/dotter -> cloudcapitalco/dotter."""
        available = ["cloudcapitalco/dotter", "acme/service-a"]
        result = resolve_project_ref("cloudcapitalco/dotter", available)
        assert result == "cloudcapitalco/dotter"

    def test_just_repo_name_resolved(self):
        """dotter -> cloudcapitalco/dotter (when only one match)."""
        available = ["cloudcapitalco/dotter", "acme/service-a"]
        result = resolve_project_ref("dotter", available)
        assert result == "cloudcapitalco/dotter"

    def test_repo_name_ambiguous_error(self):
        """repo when acme/repo and other/repo exist -> error listing both."""
        available = ["acme/repo", "other/repo", "third/service"]

        with pytest.raises(ValueError) as exc_info:
            resolve_project_ref("repo", available)

        assert "ambiguous" in str(exc_info.value).lower()
        assert "acme/repo" in str(exc_info.value)
        assert "other/repo" in str(exc_info.value)

    def test_full_org_repo_not_found_error(self):
        """acme/unknown -> error listing available projects."""
        available = ["cloudcapitalco/dotter", "acme/service-a"]

        with pytest.raises(ValueError) as exc_info:
            resolve_project_ref("acme/unknown", available)

        assert "not found" in str(exc_info.value).lower()
        assert "available" in str(exc_info.value).lower()

    def test_repo_name_not_found_error(self):
        """unknown -> error listing available projects."""
        available = ["cloudcapitalco/dotter", "acme/service-a"]

        with pytest.raises(ValueError) as exc_info:
            resolve_project_ref("unknown", available)

        assert "not found" in str(exc_info.value).lower()

    def test_single_project_matches(self):
        """Works with single project in list."""
        available = ["acme/myproject"]
        result = resolve_project_ref("myproject", available)
        assert result == "acme/myproject"

    def test_exact_match_with_similar_names(self):
        """Doesn't match partial names - only exact suffix match."""
        available = ["acme/service-a", "acme/service-ab"]

        # "service-a" should match exactly, not "service-ab"
        result = resolve_project_ref("service-a", available)
        assert result == "acme/service-a"

        # "service-ab" should also match exactly
        result = resolve_project_ref("service-ab", available)
        assert result == "acme/service-ab"


class TestResolveRepoDirectory:
    """Tests for resolve_repo_directory."""

    def test_resolves_simple_repo_name(self, tmp_path):
        """Resolves org/repo to task_dir/repo when it exists."""
        (tmp_path / "service-a").mkdir()
        result = resolve_repo_directory(tmp_path, "acme/service-a")
        assert result == tmp_path / "service-a"

    def test_resolves_nested_repo_path(self, tmp_path):
        """Resolves org/repo to task_dir/org/repo when nested exists."""
        (tmp_path / "acme" / "service-a").mkdir(parents=True)
        result = resolve_repo_directory(tmp_path, "acme/service-a")
        assert result == tmp_path / "acme" / "service-a"

    def test_prefers_simple_over_nested(self, tmp_path):
        """Prefers simple path when both exist."""
        (tmp_path / "service-a").mkdir()
        (tmp_path / "acme" / "service-a").mkdir(parents=True)
        result = resolve_repo_directory(tmp_path, "acme/service-a")
        assert result == tmp_path / "service-a"

    def test_raises_when_not_found(self, tmp_path):
        """Raises FileNotFoundError when neither path exists."""
        with pytest.raises(FileNotFoundError) as exc_info:
            resolve_repo_directory(tmp_path, "acme/missing")
        assert "acme/missing" in str(exc_info.value)

    def test_raises_for_invalid_format(self, tmp_path):
        """Raises ValueError for non org/repo format."""
        with pytest.raises(ValueError) as exc_info:
            resolve_repo_directory(tmp_path, "noslash")
        assert "org/repo" in str(exc_info.value)


class TestGetNextChunkId:
    """Tests for get_next_chunk_id."""

    def test_returns_0001_for_empty_chunks(self, tmp_path):
        """Returns '0001' when no chunks exist."""
        (tmp_path / "docs" / "chunks").mkdir(parents=True)
        result = get_next_chunk_id(tmp_path)
        assert result == "0001"

    def test_returns_next_id_after_existing(self, tmp_path):
        """Returns next sequential ID after existing chunks."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "0001-first").mkdir()
        (chunks_dir / "0002-second").mkdir()
        (chunks_dir / "0003-third").mkdir()

        result = get_next_chunk_id(tmp_path)
        assert result == "0004"

    def test_handles_gaps_in_sequence(self, tmp_path):
        """Returns next ID after highest, even with gaps."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "0001-first").mkdir()
        (chunks_dir / "0005-fifth").mkdir()  # Gap from 2-4

        result = get_next_chunk_id(tmp_path)
        assert result == "0006"

    def test_zero_pads_result(self, tmp_path):
        """Result is always 4-digit zero-padded."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "0001-first").mkdir()

        result = get_next_chunk_id(tmp_path)
        assert result == "0002"
        assert len(result) == 4


class TestCreateExternalYaml:
    """Tests for create_external_yaml.

    # Chunk: docs/chunks/remove_sequence_prefix - Updated for short_name only format
    # Chunk: docs/chunks/consolidate_ext_refs - Updated for ExternalArtifactRef format
    """

    def test_creates_external_yaml_file(self, tmp_path):
        """Creates external.yaml file in correct location."""
        (tmp_path / "docs" / "chunks").mkdir(parents=True)

        result = create_external_yaml(
            project_path=tmp_path,
            short_name="auth_token",
            external_repo_ref="acme/chunks",
            external_artifact_id="auth_token",
            pinned_sha="a" * 40,
            artifact_type=ArtifactType.CHUNK,
        )

        assert result.exists()
        assert result == tmp_path / "docs" / "chunks" / "auth_token" / "external.yaml"

    def test_creates_chunk_directory(self, tmp_path):
        """Creates chunk directory if it doesn't exist."""
        (tmp_path / "docs" / "chunks").mkdir(parents=True)

        create_external_yaml(
            project_path=tmp_path,
            short_name="auth_token",
            external_repo_ref="acme/chunks",
            external_artifact_id="auth_token",
            pinned_sha="a" * 40,
            artifact_type=ArtifactType.CHUNK,
        )

        chunk_dir = tmp_path / "docs" / "chunks" / "auth_token"
        assert chunk_dir.exists()
        assert chunk_dir.is_dir()

    def test_yaml_contains_correct_content(self, tmp_path):
        """Created YAML has all required fields."""
        (tmp_path / "docs" / "chunks").mkdir(parents=True)

        result = create_external_yaml(
            project_path=tmp_path,
            short_name="auth_token",
            external_repo_ref="acme/chunks",
            external_artifact_id="auth_token",
            pinned_sha="abcd1234" * 5,
            artifact_type=ArtifactType.CHUNK,
            track="develop",
        )

        # Load and verify via load_external_ref
        chunk_dir = result.parent
        ref = load_external_ref(chunk_dir)
        assert ref.repo == "acme/chunks"
        assert ref.artifact_id == "auth_token"
        assert ref.artifact_type == ArtifactType.CHUNK
        assert ref.track == "develop"
        assert ref.pinned == "abcd1234" * 5

    def test_defaults_track_to_main(self, tmp_path):
        """Track defaults to 'main' if not specified."""
        (tmp_path / "docs" / "chunks").mkdir(parents=True)

        result = create_external_yaml(
            project_path=tmp_path,
            short_name="auth_token",
            external_repo_ref="acme/chunks",
            external_artifact_id="auth_token",
            pinned_sha="a" * 40,
            artifact_type=ArtifactType.CHUNK,
        )

        ref = load_external_ref(result.parent)
        assert ref.track == "main"

    def test_creates_narrative_external_yaml(self, tmp_path):
        """Creates external.yaml file for narrative in correct location."""
        (tmp_path / "docs" / "narratives").mkdir(parents=True)

        result = create_external_yaml(
            project_path=tmp_path,
            short_name="user_auth_narrative",
            external_repo_ref="acme/narratives",
            external_artifact_id="user_auth_narrative",
            pinned_sha="a" * 40,
            artifact_type=ArtifactType.NARRATIVE,
        )

        assert result.exists()
        assert result == tmp_path / "docs" / "narratives" / "user_auth_narrative" / "external.yaml"
        ref = load_external_ref(result.parent)
        assert ref.artifact_type == ArtifactType.NARRATIVE


class TestAddDependentsToChunk:
    """Tests for add_dependents_to_chunk.

    # Chunk: docs/chunks/consolidate_ext_refs - Updated for ExternalArtifactRef format
    """

    def test_adds_dependents_to_frontmatter(self, tmp_path):
        """Adds dependents field to GOAL.md frontmatter."""
        chunk_path = tmp_path / "my_feature"
        chunk_path.mkdir(parents=True)
        goal_path = chunk_path / "GOAL.md"
        goal_path.write_text(
            "---\n"
            "status: IMPLEMENTING\n"
            "ticket: null\n"
            "---\n"
            "# Goal\n"
            "Some content here.\n"
        )

        add_dependents_to_chunk(
            chunk_path,
            [{"artifact_type": "chunk", "artifact_id": "my_feature", "repo": "acme/service-a"}],
        )

        content = goal_path.read_text()
        assert "dependents:" in content
        assert "acme/service-a" in content
        assert "my_feature" in content

    def test_preserves_existing_frontmatter(self, tmp_path):
        """Preserves existing frontmatter fields."""
        chunk_path = tmp_path / "my_feature"
        chunk_path.mkdir(parents=True)
        goal_path = chunk_path / "GOAL.md"
        goal_path.write_text(
            "---\n"
            "status: IMPLEMENTING\n"
            "ticket: ABC-123\n"
            "parent_chunk: null\n"
            "---\n"
            "# Goal\n"
        )

        add_dependents_to_chunk(
            chunk_path,
            [{"artifact_type": "chunk", "artifact_id": "my_feature", "repo": "acme/service-a"}],
        )

        content = goal_path.read_text()
        assert "status: IMPLEMENTING" in content
        assert "ticket: ABC-123" in content
        assert "parent_chunk:" in content

    def test_preserves_body_content(self, tmp_path):
        """Preserves content after frontmatter."""
        chunk_path = tmp_path / "my_feature"
        chunk_path.mkdir(parents=True)
        goal_path = chunk_path / "GOAL.md"
        goal_path.write_text(
            "---\n"
            "status: IMPLEMENTING\n"
            "---\n"
            "# Goal\n"
            "\n"
            "This is important content.\n"
            "\n"
            "## Success Criteria\n"
            "- Criterion 1\n"
        )

        add_dependents_to_chunk(
            chunk_path,
            [{"artifact_type": "chunk", "artifact_id": "my_feature", "repo": "acme/service-a"}],
        )

        content = goal_path.read_text()
        assert "This is important content." in content
        assert "## Success Criteria" in content
        assert "- Criterion 1" in content

    def test_handles_multiple_dependents(self, tmp_path):
        """Handles multiple dependents correctly."""
        chunk_path = tmp_path / "my_feature"
        chunk_path.mkdir(parents=True)
        goal_path = chunk_path / "GOAL.md"
        goal_path.write_text("---\nstatus: IMPLEMENTING\n---\n# Goal\n")

        add_dependents_to_chunk(
            chunk_path,
            [
                {"artifact_type": "chunk", "artifact_id": "feature_a", "repo": "acme/service-a"},
                {"artifact_type": "chunk", "artifact_id": "feature_b", "repo": "acme/service-b"},
            ],
        )

        content = goal_path.read_text()
        assert "acme/service-a" in content
        assert "acme/service-b" in content
        assert "feature_a" in content
        assert "feature_b" in content

    def test_raises_when_goal_missing(self, tmp_path):
        """Raises FileNotFoundError when GOAL.md doesn't exist."""
        chunk_path = tmp_path / "my_feature"
        chunk_path.mkdir(parents=True)

        with pytest.raises(FileNotFoundError):
            add_dependents_to_chunk(
                chunk_path,
                [{"artifact_type": "chunk", "artifact_id": "my_feature", "repo": "acme/service-a"}],
            )


class TestUpdateFrontmatterField:
    """Tests for update_frontmatter_field utility."""

    def test_updates_string_field(self, tmp_path):
        """Updates a string field in frontmatter."""
        goal_path = tmp_path / "GOAL.md"
        goal_path.write_text(
            "---\n"
            "status: FUTURE\n"
            "ticket: null\n"
            "---\n"
            "# Goal\n"
        )

        update_frontmatter_field(goal_path, "status", "IMPLEMENTING")

        content = goal_path.read_text()
        assert "status: IMPLEMENTING" in content
        assert "status: FUTURE" not in content

    def test_preserves_other_fields(self, tmp_path):
        """Preserves all other frontmatter fields when updating one."""
        goal_path = tmp_path / "GOAL.md"
        goal_path.write_text(
            "---\n"
            "status: FUTURE\n"
            "ticket: ABC-123\n"
            "parent_chunk: null\n"
            "---\n"
            "# Goal\n"
        )

        update_frontmatter_field(goal_path, "status", "IMPLEMENTING")

        content = goal_path.read_text()
        assert "ticket: ABC-123" in content
        assert "parent_chunk:" in content

    def test_preserves_body_content(self, tmp_path):
        """Preserves content after frontmatter."""
        goal_path = tmp_path / "GOAL.md"
        goal_path.write_text(
            "---\n"
            "status: FUTURE\n"
            "---\n"
            "# Goal\n"
            "\n"
            "Important content here.\n"
            "\n"
            "## Success Criteria\n"
        )

        update_frontmatter_field(goal_path, "status", "IMPLEMENTING")

        content = goal_path.read_text()
        assert "Important content here." in content
        assert "## Success Criteria" in content

    def test_adds_new_field_if_not_exists(self, tmp_path):
        """Adds new field if it doesn't exist in frontmatter."""
        goal_path = tmp_path / "GOAL.md"
        goal_path.write_text(
            "---\n"
            "status: IMPLEMENTING\n"
            "---\n"
            "# Goal\n"
        )

        update_frontmatter_field(goal_path, "ticket", "VE-001")

        content = goal_path.read_text()
        assert "ticket: VE-001" in content

    def test_raises_when_file_missing(self, tmp_path):
        """Raises FileNotFoundError when file doesn't exist."""
        goal_path = tmp_path / "GOAL.md"

        with pytest.raises(FileNotFoundError):
            update_frontmatter_field(goal_path, "status", "IMPLEMENTING")

    def test_raises_when_no_frontmatter(self, tmp_path):
        """Raises ValueError when file has no frontmatter."""
        goal_path = tmp_path / "GOAL.md"
        goal_path.write_text("# Goal\nNo frontmatter here.\n")

        with pytest.raises(ValueError):
            update_frontmatter_field(goal_path, "status", "IMPLEMENTING")


# Chunk: docs/chunks/external_chunk_causal - Tests for created_after in external.yaml
# Chunk: docs/chunks/consolidate_ext_refs - Updated for ExternalArtifactRef format
class TestCreateExternalYamlCreatedAfter:
    """Tests for create_external_yaml created_after parameter."""

    def test_create_external_yaml_with_created_after(self, tmp_path):
        """create_external_yaml includes created_after when provided."""
        (tmp_path / "docs" / "chunks").mkdir(parents=True)

        result = create_external_yaml(
            project_path=tmp_path,
            short_name="test_chunk",
            external_repo_ref="org/repo",
            external_artifact_id="ext_chunk",
            pinned_sha="a" * 40,
            artifact_type=ArtifactType.CHUNK,
            created_after=["previous_chunk"],
        )

        ref = load_external_ref(result.parent)
        assert ref.created_after == ["previous_chunk"]

    def test_create_external_yaml_with_multiple_created_after(self, tmp_path):
        """create_external_yaml handles multiple created_after entries."""
        (tmp_path / "docs" / "chunks").mkdir(parents=True)

        result = create_external_yaml(
            project_path=tmp_path,
            short_name="test_chunk",
            external_repo_ref="org/repo",
            external_artifact_id="ext_chunk",
            pinned_sha="a" * 40,
            artifact_type=ArtifactType.CHUNK,
            created_after=["chunk_a", "chunk_b", "chunk_c"],
        )

        ref = load_external_ref(result.parent)
        assert ref.created_after == ["chunk_a", "chunk_b", "chunk_c"]

    def test_create_external_yaml_without_created_after(self, tmp_path):
        """create_external_yaml omits created_after when not provided."""
        import yaml

        (tmp_path / "docs" / "chunks").mkdir(parents=True)

        result = create_external_yaml(
            project_path=tmp_path,
            short_name="test_chunk",
            external_repo_ref="org/repo",
            external_artifact_id="ext_chunk",
            pinned_sha="a" * 40,
            artifact_type=ArtifactType.CHUNK,
        )

        # Read raw YAML to verify created_after is not present
        with open(result) as f:
            data = yaml.safe_load(f)

        assert "created_after" not in data

    def test_create_external_yaml_with_empty_created_after(self, tmp_path):
        """create_external_yaml omits created_after when empty list provided."""
        import yaml

        (tmp_path / "docs" / "chunks").mkdir(parents=True)

        result = create_external_yaml(
            project_path=tmp_path,
            short_name="test_chunk",
            external_repo_ref="org/repo",
            external_artifact_id="ext_chunk",
            pinned_sha="a" * 40,
            artifact_type=ArtifactType.CHUNK,
            created_after=[],
        )

        # Read raw YAML to verify created_after is not present (empty list is falsy)
        with open(result) as f:
            data = yaml.safe_load(f)

        assert "created_after" not in data
