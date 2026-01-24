"""Tests for flexible artifact path handling in CLI commands.

# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/accept_full_artifact_paths - Flexible path acceptance
"""

import pytest
from click.testing import CliRunner

from ve import cli
from chunks import Chunks


@pytest.fixture
def runner():
    """Click test runner."""
    return CliRunner()


@pytest.fixture
def project_with_chunk(tmp_path):
    """Create a project with a single chunk for testing."""
    # Create docs/chunks directory
    chunks_dir = tmp_path / "docs" / "chunks"
    chunks_dir.mkdir(parents=True)

    # Create a chunk
    chunk_dir = chunks_dir / "my_test_chunk"
    chunk_dir.mkdir()
    (chunk_dir / "GOAL.md").write_text(
        "---\n"
        "status: IMPLEMENTING\n"
        "ticket: null\n"
        "parent_chunk: null\n"
        "code_paths: []\n"
        "code_references: []\n"
        "narrative: null\n"
        "subsystems: []\n"
        "created_after: []\n"
        "---\n"
        "# Chunk Goal\n"
        "Test chunk for flexible path handling.\n"
    )

    return tmp_path


@pytest.fixture
def project_with_investigation(tmp_path):
    """Create a project with a single investigation for testing."""
    # Create docs/investigations directory
    investigations_dir = tmp_path / "docs" / "investigations"
    investigations_dir.mkdir(parents=True)

    # Create an investigation
    investigation_dir = investigations_dir / "my_test_investigation"
    investigation_dir.mkdir()
    (investigation_dir / "OVERVIEW.md").write_text(
        "---\n"
        "status: ONGOING\n"
        "trigger: Test trigger\n"
        "proposed_chunks: []\n"
        "created_after: []\n"
        "---\n"
        "# Investigation Overview\n"
        "Test investigation for flexible path handling.\n"
    )

    return tmp_path


@pytest.fixture
def project_with_subsystem(tmp_path):
    """Create a project with a single subsystem for testing."""
    # Create docs/subsystems directory
    subsystems_dir = tmp_path / "docs" / "subsystems"
    subsystems_dir.mkdir(parents=True)

    # Create a subsystem
    subsystem_dir = subsystems_dir / "my_test_subsystem"
    subsystem_dir.mkdir()
    (subsystem_dir / "OVERVIEW.md").write_text(
        "---\n"
        "status: DOCUMENTED\n"
        "chunks: []\n"
        "code_references: []\n"
        "proposed_chunks: []\n"
        "created_after: []\n"
        "---\n"
        "# Subsystem Overview\n"
        "Test subsystem for flexible path handling.\n"
    )

    return tmp_path


@pytest.fixture
def project_with_narrative(tmp_path):
    """Create a project with a single narrative for testing."""
    # Create docs/narratives directory
    narratives_dir = tmp_path / "docs" / "narratives"
    narratives_dir.mkdir(parents=True)

    # Create a narrative
    narrative_dir = narratives_dir / "my_test_narrative"
    narrative_dir.mkdir()
    (narrative_dir / "OVERVIEW.md").write_text(
        "---\n"
        "status: ACTIVE\n"
        "advances_trunk_goal: Test\n"
        "proposed_chunks: []\n"
        "created_after: []\n"
        "---\n"
        "# Narrative Overview\n"
        "Test narrative for flexible path handling.\n"
    )

    return tmp_path


class TestChunkValidateFlexiblePath:
    """Tests for ve chunk validate with flexible paths."""

    def test_validate_with_just_name(self, runner, project_with_chunk):
        """ve chunk validate my_test_chunk should work."""
        result = runner.invoke(cli, [
            "chunk", "validate", "my_test_chunk",
            "--project-dir", str(project_with_chunk),
        ])
        # May have warnings about missing code_references, but shouldn't error on not found
        assert "not found" not in result.output.lower() or result.exit_code == 0

    def test_validate_with_docs_prefix(self, runner, project_with_chunk):
        """ve chunk validate docs/chunks/my_test_chunk should work."""
        result = runner.invoke(cli, [
            "chunk", "validate", "docs/chunks/my_test_chunk",
            "--project-dir", str(project_with_chunk),
        ])
        assert "not found" not in result.output.lower() or result.exit_code == 0

    def test_validate_with_type_prefix(self, runner, project_with_chunk):
        """ve chunk validate chunks/my_test_chunk should work."""
        result = runner.invoke(cli, [
            "chunk", "validate", "chunks/my_test_chunk",
            "--project-dir", str(project_with_chunk),
        ])
        assert "not found" not in result.output.lower() or result.exit_code == 0

    def test_validate_with_trailing_slash(self, runner, project_with_chunk):
        """ve chunk validate docs/chunks/my_test_chunk/ should work."""
        result = runner.invoke(cli, [
            "chunk", "validate", "docs/chunks/my_test_chunk/",
            "--project-dir", str(project_with_chunk),
        ])
        assert "not found" not in result.output.lower() or result.exit_code == 0


class TestChunkStatusFlexiblePath:
    """Tests for ve chunk status with flexible paths."""

    def test_status_with_just_name(self, runner, project_with_chunk):
        """ve chunk status my_test_chunk should work."""
        result = runner.invoke(cli, [
            "chunk", "status", "my_test_chunk",
            "--project-dir", str(project_with_chunk),
        ])
        assert result.exit_code == 0
        assert "IMPLEMENTING" in result.output

    def test_status_with_docs_prefix(self, runner, project_with_chunk):
        """ve chunk status docs/chunks/my_test_chunk should work."""
        result = runner.invoke(cli, [
            "chunk", "status", "docs/chunks/my_test_chunk",
            "--project-dir", str(project_with_chunk),
        ])
        assert result.exit_code == 0
        assert "IMPLEMENTING" in result.output

    def test_status_with_type_prefix(self, runner, project_with_chunk):
        """ve chunk status chunks/my_test_chunk should work."""
        result = runner.invoke(cli, [
            "chunk", "status", "chunks/my_test_chunk",
            "--project-dir", str(project_with_chunk),
        ])
        assert result.exit_code == 0
        assert "IMPLEMENTING" in result.output


class TestSubsystemValidateFlexiblePath:
    """Tests for ve subsystem validate with flexible paths."""

    def test_validate_with_just_name(self, runner, project_with_subsystem):
        """ve subsystem validate my_test_subsystem should work."""
        result = runner.invoke(cli, [
            "subsystem", "validate", "my_test_subsystem",
            "--project-dir", str(project_with_subsystem),
        ])
        assert result.exit_code == 0

    def test_validate_with_docs_prefix(self, runner, project_with_subsystem):
        """ve subsystem validate docs/subsystems/my_test_subsystem should work."""
        result = runner.invoke(cli, [
            "subsystem", "validate", "docs/subsystems/my_test_subsystem",
            "--project-dir", str(project_with_subsystem),
        ])
        assert result.exit_code == 0


class TestSubsystemStatusFlexiblePath:
    """Tests for ve subsystem status with flexible paths."""

    def test_status_with_just_name(self, runner, project_with_subsystem):
        """ve subsystem status my_test_subsystem should work."""
        result = runner.invoke(cli, [
            "subsystem", "status", "my_test_subsystem",
            "--project-dir", str(project_with_subsystem),
        ])
        assert result.exit_code == 0
        assert "DOCUMENTED" in result.output

    def test_status_with_docs_prefix(self, runner, project_with_subsystem):
        """ve subsystem status docs/subsystems/my_test_subsystem should work."""
        result = runner.invoke(cli, [
            "subsystem", "status", "docs/subsystems/my_test_subsystem",
            "--project-dir", str(project_with_subsystem),
        ])
        assert result.exit_code == 0
        assert "DOCUMENTED" in result.output


class TestInvestigationStatusFlexiblePath:
    """Tests for ve investigation status with flexible paths."""

    def test_status_with_just_name(self, runner, project_with_investigation):
        """ve investigation status my_test_investigation should work."""
        result = runner.invoke(cli, [
            "investigation", "status", "my_test_investigation",
            "--project-dir", str(project_with_investigation),
        ])
        assert result.exit_code == 0
        assert "ONGOING" in result.output

    def test_status_with_docs_prefix(self, runner, project_with_investigation):
        """ve investigation status docs/investigations/my_test_investigation should work."""
        result = runner.invoke(cli, [
            "investigation", "status", "docs/investigations/my_test_investigation",
            "--project-dir", str(project_with_investigation),
        ])
        assert result.exit_code == 0
        assert "ONGOING" in result.output


class TestNarrativeStatusFlexiblePath:
    """Tests for ve narrative status with flexible paths."""

    def test_status_with_just_name(self, runner, project_with_narrative):
        """ve narrative status my_test_narrative should work."""
        result = runner.invoke(cli, [
            "narrative", "status", "my_test_narrative",
            "--project-dir", str(project_with_narrative),
        ])
        assert result.exit_code == 0
        assert "ACTIVE" in result.output

    def test_status_with_docs_prefix(self, runner, project_with_narrative):
        """ve narrative status docs/narratives/my_test_narrative should work."""
        result = runner.invoke(cli, [
            "narrative", "status", "docs/narratives/my_test_narrative",
            "--project-dir", str(project_with_narrative),
        ])
        assert result.exit_code == 0
        assert "ACTIVE" in result.output
