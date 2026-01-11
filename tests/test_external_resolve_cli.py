"""CLI integration tests for ve external resolve command.

# Chunk: docs/chunks/external_resolve_all_types - CLI integration tests
"""

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def chunk_repo(tmp_path_factory):
    """Create a repo with an external chunk reference."""
    repo_path = tmp_path_factory.mktemp("chunk_repo")
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Create external chunk reference
    chunks_dir = repo_path / "docs" / "chunks" / "0001-feature"
    chunks_dir.mkdir(parents=True)
    (chunks_dir / "external.yaml").write_text(
        "artifact_type: chunk\n"
        "artifact_id: 0001-shared_feature\n"
        "repo: acme/chunks\n"
        "track: main\n"
        "pinned: null\n"
    )

    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return repo_path


@pytest.fixture
def narrative_repo(tmp_path_factory):
    """Create a repo with an external narrative reference."""
    repo_path = tmp_path_factory.mktemp("narrative_repo")
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Create external narrative reference
    narratives_dir = repo_path / "docs" / "narratives" / "0001-big_project"
    narratives_dir.mkdir(parents=True)
    (narratives_dir / "external.yaml").write_text(
        "artifact_type: narrative\n"
        "artifact_id: 0001-feature_set\n"
        "repo: acme/narratives\n"
        "track: main\n"
        "pinned: null\n"
    )

    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return repo_path


@pytest.fixture
def investigation_repo(tmp_path_factory):
    """Create a repo with an external investigation reference."""
    repo_path = tmp_path_factory.mktemp("investigation_repo")
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Create external investigation reference
    investigations_dir = repo_path / "docs" / "investigations" / "0001-bug_analysis"
    investigations_dir.mkdir(parents=True)
    (investigations_dir / "external.yaml").write_text(
        "artifact_type: investigation\n"
        "artifact_id: 0001-memory_leak\n"
        "repo: acme/investigations\n"
        "track: main\n"
        "pinned: null\n"
    )

    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return repo_path


@pytest.fixture
def subsystem_repo(tmp_path_factory):
    """Create a repo with an external subsystem reference."""
    repo_path = tmp_path_factory.mktemp("subsystem_repo")
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Create external subsystem reference
    subsystems_dir = repo_path / "docs" / "subsystems" / "validation"
    subsystems_dir.mkdir(parents=True)
    (subsystems_dir / "external.yaml").write_text(
        "artifact_type: subsystem\n"
        "artifact_id: core_validation\n"
        "repo: acme/subsystems\n"
        "track: main\n"
        "pinned: null\n"
    )

    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return repo_path


class TestExternalResolveCliChunk:
    """CLI tests for chunk resolution."""

    def test_help_shows_artifact_terminology(self):
        """Help text mentions artifact types."""
        result = subprocess.run(
            ["uv", "run", "ve", "external", "resolve", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "artifact" in result.stdout.lower()

    def test_error_on_nonexistent_artifact(self, chunk_repo):
        """Shows error for nonexistent artifact."""
        result = subprocess.run(
            ["uv", "run", "ve", "external", "resolve", "9999-nonexistent", "--project-dir", str(chunk_repo)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "not found" in result.stderr.lower()

    def test_error_on_mutually_exclusive_options(self, chunk_repo):
        """Shows error for mutually exclusive options."""
        result = subprocess.run(
            ["uv", "run", "ve", "external", "resolve", "0001-feature", "--main-only", "--secondary-only", "--project-dir", str(chunk_repo)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "mutually exclusive" in result.stderr.lower()


class TestExternalResolveCliNarrative:
    """CLI tests for narrative resolution."""

    def test_error_on_nonexistent_narrative(self, narrative_repo):
        """Shows error for nonexistent narrative."""
        result = subprocess.run(
            ["uv", "run", "ve", "external", "resolve", "9999-nonexistent", "--project-dir", str(narrative_repo)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "not found" in result.stderr.lower()


class TestExternalResolveCliInvestigation:
    """CLI tests for investigation resolution."""

    def test_error_on_nonexistent_investigation(self, investigation_repo):
        """Shows error for nonexistent investigation."""
        result = subprocess.run(
            ["uv", "run", "ve", "external", "resolve", "9999-nonexistent", "--project-dir", str(investigation_repo)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "not found" in result.stderr.lower()


class TestExternalResolveCliSubsystem:
    """CLI tests for subsystem resolution."""

    def test_error_on_nonexistent_subsystem(self, subsystem_repo):
        """Shows error for nonexistent subsystem."""
        result = subprocess.run(
            ["uv", "run", "ve", "external", "resolve", "9999-nonexistent", "--project-dir", str(subsystem_repo)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "not found" in result.stderr.lower()


class TestBackwardCompatibility:
    """Tests for backward compatibility of CLI options."""

    def test_goal_only_alias_works(self, chunk_repo):
        """--goal-only is still accepted as alias for --main-only."""
        result = subprocess.run(
            ["uv", "run", "ve", "external", "resolve", "0001-feature", "--goal-only", "--project-dir", str(chunk_repo)],
            capture_output=True,
            text=True,
        )

        # Will fail due to repo not being accessible, but should not fail on option parsing
        assert "--goal-only" not in result.stderr or "unrecognized" not in result.stderr.lower()

    def test_plan_only_alias_works(self, chunk_repo):
        """--plan-only is still accepted as alias for --secondary-only."""
        result = subprocess.run(
            ["uv", "run", "ve", "external", "resolve", "0001-feature", "--plan-only", "--project-dir", str(chunk_repo)],
            capture_output=True,
            text=True,
        )

        # Will fail due to repo not being accessible, but should not fail on option parsing
        assert "--plan-only" not in result.stderr or "unrecognized" not in result.stderr.lower()

    def test_goal_and_plan_only_are_mutually_exclusive(self, chunk_repo):
        """--goal-only and --plan-only are mutually exclusive like --main-only and --secondary-only."""
        result = subprocess.run(
            ["uv", "run", "ve", "external", "resolve", "0001-feature", "--goal-only", "--plan-only", "--project-dir", str(chunk_repo)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "mutually exclusive" in result.stderr.lower()
