"""Tests for external artifact reference utilities.

# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
"""

import pytest

from models import ArtifactType, ExternalArtifactRef


class TestIsExternalArtifact:
    """Tests for is_external_artifact detection."""

    def test_chunk_external_true(self, tmp_path):
        """Returns True when chunk has external.yaml but no GOAL.md."""
        from external_refs import is_external_artifact

        (tmp_path / "external.yaml").write_text(
            "artifact_type: chunk\n"
            "artifact_id: my_feature\n"
            "repo: acme/chunks\n"
        )
        assert is_external_artifact(tmp_path, ArtifactType.CHUNK) is True

    def test_chunk_local_false(self, tmp_path):
        """Returns False when chunk has GOAL.md (local artifact)."""
        from external_refs import is_external_artifact

        (tmp_path / "GOAL.md").write_text("---\nstatus: IMPLEMENTING\n---\n# Goal\n")
        assert is_external_artifact(tmp_path, ArtifactType.CHUNK) is False

    def test_chunk_both_files_false(self, tmp_path):
        """Returns False when chunk has both GOAL.md and external.yaml."""
        from external_refs import is_external_artifact

        (tmp_path / "GOAL.md").write_text("---\nstatus: IMPLEMENTING\n---\n# Goal\n")
        (tmp_path / "external.yaml").write_text("artifact_type: chunk\n")
        # Has the main file, so it's a local artifact
        assert is_external_artifact(tmp_path, ArtifactType.CHUNK) is False

    def test_narrative_external_true(self, tmp_path):
        """Returns True when narrative has external.yaml but no OVERVIEW.md."""
        from external_refs import is_external_artifact

        (tmp_path / "external.yaml").write_text(
            "artifact_type: narrative\n"
            "artifact_id: user_journey\n"
            "repo: acme/docs\n"
        )
        assert is_external_artifact(tmp_path, ArtifactType.NARRATIVE) is True

    def test_narrative_local_false(self, tmp_path):
        """Returns False when narrative has OVERVIEW.md (local artifact)."""
        from external_refs import is_external_artifact

        (tmp_path / "OVERVIEW.md").write_text("---\nstatus: ACTIVE\n---\n# Overview\n")
        assert is_external_artifact(tmp_path, ArtifactType.NARRATIVE) is False

    def test_investigation_external_true(self, tmp_path):
        """Returns True when investigation has external.yaml but no OVERVIEW.md."""
        from external_refs import is_external_artifact

        (tmp_path / "external.yaml").write_text(
            "artifact_type: investigation\n"
            "artifact_id: memory_leak\n"
            "repo: acme/research\n"
        )
        assert is_external_artifact(tmp_path, ArtifactType.INVESTIGATION) is True

    def test_investigation_local_false(self, tmp_path):
        """Returns False when investigation has OVERVIEW.md (local artifact)."""
        from external_refs import is_external_artifact

        (tmp_path / "OVERVIEW.md").write_text("---\nstatus: ONGOING\n---\n# Overview\n")
        assert is_external_artifact(tmp_path, ArtifactType.INVESTIGATION) is False

    def test_subsystem_external_true(self, tmp_path):
        """Returns True when subsystem has external.yaml but no OVERVIEW.md."""
        from external_refs import is_external_artifact

        (tmp_path / "external.yaml").write_text(
            "artifact_type: subsystem\n"
            "artifact_id: auth_system\n"
            "repo: acme/platform\n"
        )
        assert is_external_artifact(tmp_path, ArtifactType.SUBSYSTEM) is True

    def test_subsystem_local_false(self, tmp_path):
        """Returns False when subsystem has OVERVIEW.md (local artifact)."""
        from external_refs import is_external_artifact

        (tmp_path / "OVERVIEW.md").write_text("---\nstatus: DOCUMENTED\n---\n# Overview\n")
        assert is_external_artifact(tmp_path, ArtifactType.SUBSYSTEM) is False

    def test_empty_directory_false(self, tmp_path):
        """Returns False for empty directory (no files)."""
        from external_refs import is_external_artifact

        assert is_external_artifact(tmp_path, ArtifactType.CHUNK) is False
        assert is_external_artifact(tmp_path, ArtifactType.NARRATIVE) is False


class TestDetectArtifactTypeFromPath:
    """Tests for detect_artifact_type_from_path."""

    def test_detects_chunk_path(self, tmp_path):
        """Detects CHUNK from docs/chunks/ path."""
        from external_refs import detect_artifact_type_from_path

        chunk_path = tmp_path / "docs" / "chunks" / "my_feature"
        chunk_path.mkdir(parents=True)

        result = detect_artifact_type_from_path(chunk_path)
        assert result == ArtifactType.CHUNK

    def test_detects_narrative_path(self, tmp_path):
        """Detects NARRATIVE from docs/narratives/ path."""
        from external_refs import detect_artifact_type_from_path

        narrative_path = tmp_path / "docs" / "narratives" / "user_journey"
        narrative_path.mkdir(parents=True)

        result = detect_artifact_type_from_path(narrative_path)
        assert result == ArtifactType.NARRATIVE

    def test_detects_investigation_path(self, tmp_path):
        """Detects INVESTIGATION from docs/investigations/ path."""
        from external_refs import detect_artifact_type_from_path

        investigation_path = tmp_path / "docs" / "investigations" / "memory_leak"
        investigation_path.mkdir(parents=True)

        result = detect_artifact_type_from_path(investigation_path)
        assert result == ArtifactType.INVESTIGATION

    def test_detects_subsystem_path(self, tmp_path):
        """Detects SUBSYSTEM from docs/subsystems/ path."""
        from external_refs import detect_artifact_type_from_path

        subsystem_path = tmp_path / "docs" / "subsystems" / "auth_system"
        subsystem_path.mkdir(parents=True)

        result = detect_artifact_type_from_path(subsystem_path)
        assert result == ArtifactType.SUBSYSTEM

    def test_raises_for_invalid_path(self, tmp_path):
        """Raises ValueError for path not under a known artifact directory."""
        from external_refs import detect_artifact_type_from_path

        invalid_path = tmp_path / "src" / "utils"
        invalid_path.mkdir(parents=True)

        with pytest.raises(ValueError) as exc_info:
            detect_artifact_type_from_path(invalid_path)
        assert "artifact type" in str(exc_info.value).lower()

    def test_raises_for_docs_root(self, tmp_path):
        """Raises ValueError for docs directory itself."""
        from external_refs import detect_artifact_type_from_path

        docs_path = tmp_path / "docs"
        docs_path.mkdir(parents=True)

        with pytest.raises(ValueError):
            detect_artifact_type_from_path(docs_path)


class TestGetMainFileForType:
    """Tests for get_main_file_for_type utility."""

    def test_returns_goal_md_for_chunk(self):
        """Returns GOAL.md for CHUNK type."""
        from external_refs import get_main_file_for_type

        assert get_main_file_for_type(ArtifactType.CHUNK) == "GOAL.md"

    def test_returns_overview_md_for_narrative(self):
        """Returns OVERVIEW.md for NARRATIVE type."""
        from external_refs import get_main_file_for_type

        assert get_main_file_for_type(ArtifactType.NARRATIVE) == "OVERVIEW.md"

    def test_returns_overview_md_for_investigation(self):
        """Returns OVERVIEW.md for INVESTIGATION type."""
        from external_refs import get_main_file_for_type

        assert get_main_file_for_type(ArtifactType.INVESTIGATION) == "OVERVIEW.md"

    def test_returns_overview_md_for_subsystem(self):
        """Returns OVERVIEW.md for SUBSYSTEM type."""
        from external_refs import get_main_file_for_type

        assert get_main_file_for_type(ArtifactType.SUBSYSTEM) == "OVERVIEW.md"


class TestLoadExternalRef:
    """Tests for load_external_ref from external_refs module."""

    def test_loads_valid_external_ref(self, tmp_path):
        """Loads and returns ExternalArtifactRef from valid YAML."""
        from external_refs import load_external_ref

        ref_file = tmp_path / "external.yaml"
        ref_file.write_text(
            "artifact_type: chunk\n"
            "artifact_id: my_feature\n"
            "repo: acme/other-project\n"
        )

        ref = load_external_ref(tmp_path)
        assert isinstance(ref, ExternalArtifactRef)
        assert ref.artifact_type == ArtifactType.CHUNK
        assert ref.artifact_id == "my_feature"
        assert ref.repo == "acme/other-project"

    def test_loads_ref_with_track_and_pinned(self, tmp_path):
        """Loads external ref with track and pinned fields."""
        from external_refs import load_external_ref

        ref_file = tmp_path / "external.yaml"
        ref_file.write_text(
            "artifact_type: narrative\n"
            "artifact_id: user_journey\n"
            "repo: acme/docs\n"
            "track: main\n"
            "pinned: " + "a" * 40 + "\n"
        )

        ref = load_external_ref(tmp_path)
        assert ref.track == "main"
        assert ref.pinned == "a" * 40
        assert ref.artifact_type == ArtifactType.NARRATIVE

    def test_loads_ref_with_created_after(self, tmp_path):
        """Loads external ref with created_after field."""
        from external_refs import load_external_ref

        ref_file = tmp_path / "external.yaml"
        ref_file.write_text(
            "artifact_type: chunk\n"
            "artifact_id: feature_b\n"
            "repo: acme/chunks\n"
            "created_after:\n"
            "  - feature_a\n"
        )

        ref = load_external_ref(tmp_path)
        assert ref.created_after == ["feature_a"]

    def test_raises_for_missing_file(self, tmp_path):
        """Raises FileNotFoundError when external.yaml doesn't exist."""
        from external_refs import load_external_ref

        with pytest.raises(FileNotFoundError):
            load_external_ref(tmp_path)


class TestCreateExternalYaml:
    """Tests for create_external_yaml from external_refs module."""

    def test_creates_chunk_external_yaml(self, tmp_path):
        """Creates external.yaml for chunk in correct location."""
        from external_refs import create_external_yaml, load_external_ref

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

        # Verify content
        ref = load_external_ref(result.parent)
        assert ref.artifact_type == ArtifactType.CHUNK
        assert ref.artifact_id == "auth_token"
        assert ref.repo == "acme/chunks"

    def test_creates_narrative_external_yaml(self, tmp_path):
        """Creates external.yaml for narrative in correct location."""
        from external_refs import create_external_yaml, load_external_ref

        (tmp_path / "docs" / "narratives").mkdir(parents=True)

        result = create_external_yaml(
            project_path=tmp_path,
            short_name="user_journey",
            external_repo_ref="acme/docs",
            external_artifact_id="user_journey",
            pinned_sha="b" * 40,
            artifact_type=ArtifactType.NARRATIVE,
        )

        assert result.exists()
        assert result == tmp_path / "docs" / "narratives" / "user_journey" / "external.yaml"

        ref = load_external_ref(result.parent)
        assert ref.artifact_type == ArtifactType.NARRATIVE

    def test_creates_investigation_external_yaml(self, tmp_path):
        """Creates external.yaml for investigation in correct location."""
        from external_refs import create_external_yaml, load_external_ref

        (tmp_path / "docs" / "investigations").mkdir(parents=True)

        result = create_external_yaml(
            project_path=tmp_path,
            short_name="memory_leak",
            external_repo_ref="acme/research",
            external_artifact_id="memory_leak",
            pinned_sha="c" * 40,
            artifact_type=ArtifactType.INVESTIGATION,
        )

        assert result.exists()
        assert result == tmp_path / "docs" / "investigations" / "memory_leak" / "external.yaml"

        ref = load_external_ref(result.parent)
        assert ref.artifact_type == ArtifactType.INVESTIGATION

    def test_creates_subsystem_external_yaml(self, tmp_path):
        """Creates external.yaml for subsystem in correct location."""
        from external_refs import create_external_yaml, load_external_ref

        (tmp_path / "docs" / "subsystems").mkdir(parents=True)

        result = create_external_yaml(
            project_path=tmp_path,
            short_name="auth_system",
            external_repo_ref="acme/platform",
            external_artifact_id="auth_system",
            pinned_sha="d" * 40,
            artifact_type=ArtifactType.SUBSYSTEM,
        )

        assert result.exists()
        assert result == tmp_path / "docs" / "subsystems" / "auth_system" / "external.yaml"

        ref = load_external_ref(result.parent)
        assert ref.artifact_type == ArtifactType.SUBSYSTEM

    def test_includes_created_after(self, tmp_path):
        """Includes created_after when provided."""
        from external_refs import create_external_yaml, load_external_ref

        (tmp_path / "docs" / "chunks").mkdir(parents=True)

        result = create_external_yaml(
            project_path=tmp_path,
            short_name="feature_b",
            external_repo_ref="acme/chunks",
            external_artifact_id="feature_b",
            pinned_sha="a" * 40,
            artifact_type=ArtifactType.CHUNK,
            created_after=["feature_a"],
        )

        ref = load_external_ref(result.parent)
        assert ref.created_after == ["feature_a"]

    def test_defaults_track_to_main(self, tmp_path):
        """Track defaults to 'main' if not specified."""
        from external_refs import create_external_yaml, load_external_ref

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


class TestArtifactMainFile:
    """Tests for ARTIFACT_MAIN_FILE constant."""

    def test_constant_has_all_types(self):
        """ARTIFACT_MAIN_FILE has entries for all ArtifactType values."""
        from external_refs import ARTIFACT_MAIN_FILE

        for artifact_type in ArtifactType:
            assert artifact_type in ARTIFACT_MAIN_FILE
            assert isinstance(ARTIFACT_MAIN_FILE[artifact_type], str)


class TestArtifactDirName:
    """Tests for ARTIFACT_DIR_NAME constant."""

    def test_constant_has_all_types(self):
        """ARTIFACT_DIR_NAME has entries for all ArtifactType values."""
        from external_refs import ARTIFACT_DIR_NAME

        for artifact_type in ArtifactType:
            assert artifact_type in ARTIFACT_DIR_NAME
            assert isinstance(ARTIFACT_DIR_NAME[artifact_type], str)

    def test_dir_names_are_correct(self):
        """ARTIFACT_DIR_NAME has correct directory names."""
        from external_refs import ARTIFACT_DIR_NAME

        assert ARTIFACT_DIR_NAME[ArtifactType.CHUNK] == "chunks"
        assert ARTIFACT_DIR_NAME[ArtifactType.NARRATIVE] == "narratives"
        assert ARTIFACT_DIR_NAME[ArtifactType.INVESTIGATION] == "investigations"
        assert ARTIFACT_DIR_NAME[ArtifactType.SUBSYSTEM] == "subsystems"


class TestNormalizeArtifactPath:
    """Tests for normalize_artifact_path utility."""

    def test_standard_path_docs_chunks(self):
        """docs/chunks/foo -> (CHUNK, 'foo')."""
        from external_refs import normalize_artifact_path

        result = normalize_artifact_path("docs/chunks/foo")
        assert result == (ArtifactType.CHUNK, "foo")

    def test_standard_path_docs_investigations(self):
        """docs/investigations/bar -> (INVESTIGATION, 'bar')."""
        from external_refs import normalize_artifact_path

        result = normalize_artifact_path("docs/investigations/bar")
        assert result == (ArtifactType.INVESTIGATION, "bar")

    def test_standard_path_docs_narratives(self):
        """docs/narratives/baz -> (NARRATIVE, 'baz')."""
        from external_refs import normalize_artifact_path

        result = normalize_artifact_path("docs/narratives/baz")
        assert result == (ArtifactType.NARRATIVE, "baz")

    def test_standard_path_docs_subsystems(self):
        """docs/subsystems/qux -> (SUBSYSTEM, 'qux')."""
        from external_refs import normalize_artifact_path

        result = normalize_artifact_path("docs/subsystems/qux")
        assert result == (ArtifactType.SUBSYSTEM, "qux")

    def test_path_with_external_repo_prefix(self):
        """architecture/docs/chunks/foo -> (CHUNK, 'foo') with external_repo_name."""
        from external_refs import normalize_artifact_path

        result = normalize_artifact_path(
            "architecture/docs/chunks/foo",
            external_repo_name="architecture",
        )
        assert result == (ArtifactType.CHUNK, "foo")

    def test_type_without_docs_prefix_chunks(self):
        """chunks/foo -> (CHUNK, 'foo')."""
        from external_refs import normalize_artifact_path

        result = normalize_artifact_path("chunks/foo")
        assert result == (ArtifactType.CHUNK, "foo")

    def test_type_without_docs_prefix_investigations(self):
        """investigations/bar -> (INVESTIGATION, 'bar')."""
        from external_refs import normalize_artifact_path

        result = normalize_artifact_path("investigations/bar")
        assert result == (ArtifactType.INVESTIGATION, "bar")

    def test_trailing_slash_stripped(self):
        """docs/chunks/foo/ -> (CHUNK, 'foo')."""
        from external_refs import normalize_artifact_path

        result = normalize_artifact_path("docs/chunks/foo/")
        assert result == (ArtifactType.CHUNK, "foo")

    def test_just_artifact_name_searches(self, tmp_path):
        """foo -> searches and finds in chunks/."""
        from external_refs import normalize_artifact_path

        # Create artifact in chunks directory
        (tmp_path / "docs" / "chunks" / "foo").mkdir(parents=True)

        result = normalize_artifact_path("foo", search_path=tmp_path)
        assert result == (ArtifactType.CHUNK, "foo")

    def test_just_artifact_name_finds_investigation(self, tmp_path):
        """bar -> searches and finds in investigations/."""
        from external_refs import normalize_artifact_path

        # Create artifact in investigations directory
        (tmp_path / "docs" / "investigations" / "bar").mkdir(parents=True)

        result = normalize_artifact_path("bar", search_path=tmp_path)
        assert result == (ArtifactType.INVESTIGATION, "bar")

    def test_just_artifact_name_ambiguous_error(self, tmp_path):
        """foo exists in both chunks/ and investigations/ -> raises error."""
        from external_refs import normalize_artifact_path

        # Create artifact in both directories
        (tmp_path / "docs" / "chunks" / "foo").mkdir(parents=True)
        (tmp_path / "docs" / "investigations" / "foo").mkdir(parents=True)

        with pytest.raises(ValueError) as exc_info:
            normalize_artifact_path("foo", search_path=tmp_path)

        assert "ambiguous" in str(exc_info.value).lower()
        assert "foo" in str(exc_info.value)

    def test_artifact_name_not_found_error(self, tmp_path):
        """nonexistent -> raises error."""
        from external_refs import normalize_artifact_path

        # Create docs structure but not the artifact
        (tmp_path / "docs" / "chunks").mkdir(parents=True)

        with pytest.raises(ValueError) as exc_info:
            normalize_artifact_path("nonexistent", search_path=tmp_path)

        assert "not found" in str(exc_info.value).lower()
        assert "nonexistent" in str(exc_info.value)

    def test_absolute_path_rejected(self):
        """/absolute/path -> raises error."""
        from external_refs import normalize_artifact_path

        with pytest.raises(ValueError) as exc_info:
            normalize_artifact_path("/absolute/path/to/artifact")

        assert "absolute" in str(exc_info.value).lower()

    def test_artifact_name_without_search_path_error(self):
        """Just artifact name without search_path -> raises error."""
        from external_refs import normalize_artifact_path

        with pytest.raises(ValueError) as exc_info:
            normalize_artifact_path("my_artifact")

        assert "search path" in str(exc_info.value).lower()

    def test_multiple_trailing_slashes(self):
        """docs/chunks/foo// -> (CHUNK, 'foo')."""
        from external_refs import normalize_artifact_path

        result = normalize_artifact_path("docs/chunks/foo//")
        assert result == (ArtifactType.CHUNK, "foo")

    def test_external_repo_prefix_with_type_only(self):
        """architecture/chunks/foo -> (CHUNK, 'foo') when external_repo_name matches."""
        from external_refs import normalize_artifact_path

        result = normalize_artifact_path(
            "architecture/chunks/foo",
            external_repo_name="architecture",
        )
        assert result == (ArtifactType.CHUNK, "foo")


class TestStripArtifactPathPrefix:
    """Tests for strip_artifact_path_prefix utility."""

    def test_strips_docs_chunks_prefix(self):
        """docs/chunks/foo -> foo."""
        from external_refs import strip_artifact_path_prefix

        result = strip_artifact_path_prefix("docs/chunks/foo", ArtifactType.CHUNK)
        assert result == "foo"

    def test_strips_docs_investigations_prefix(self):
        """docs/investigations/bar -> bar."""
        from external_refs import strip_artifact_path_prefix

        result = strip_artifact_path_prefix("docs/investigations/bar", ArtifactType.INVESTIGATION)
        assert result == "bar"

    def test_strips_type_only_prefix(self):
        """chunks/foo -> foo."""
        from external_refs import strip_artifact_path_prefix

        result = strip_artifact_path_prefix("chunks/foo", ArtifactType.CHUNK)
        assert result == "foo"

    def test_returns_as_is_for_plain_name(self):
        """foo -> foo (no prefix to strip)."""
        from external_refs import strip_artifact_path_prefix

        result = strip_artifact_path_prefix("foo", ArtifactType.CHUNK)
        assert result == "foo"

    def test_strips_trailing_slash(self):
        """docs/chunks/foo/ -> foo."""
        from external_refs import strip_artifact_path_prefix

        result = strip_artifact_path_prefix("docs/chunks/foo/", ArtifactType.CHUNK)
        assert result == "foo"

    def test_wrong_type_prefix_returns_as_is(self):
        """docs/investigations/foo with CHUNK type -> docs/investigations/foo."""
        from external_refs import strip_artifact_path_prefix

        # When the type doesn't match, we return as-is (the caller knows the expected type)
        result = strip_artifact_path_prefix("docs/investigations/foo", ArtifactType.CHUNK)
        # This returns as-is because investigations != chunks
        assert result == "docs/investigations/foo"

    def test_all_artifact_types(self):
        """Test all artifact types work correctly."""
        from external_refs import strip_artifact_path_prefix

        # Test each type
        assert strip_artifact_path_prefix("docs/chunks/c", ArtifactType.CHUNK) == "c"
        assert strip_artifact_path_prefix("docs/narratives/n", ArtifactType.NARRATIVE) == "n"
        assert strip_artifact_path_prefix("docs/investigations/i", ArtifactType.INVESTIGATION) == "i"
        assert strip_artifact_path_prefix("docs/subsystems/s", ArtifactType.SUBSYSTEM) == "s"
