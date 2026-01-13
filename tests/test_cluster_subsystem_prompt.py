"""Tests for cluster subsystem prompt feature.

# Chunk: docs/chunks/cluster_subsystem_prompt - Tests for cluster size warnings
"""

import pathlib
import pytest

from conftest import make_ve_initialized_git_repo


class TestClusterSizeWarning:
    """Tests for the ClusterSizeWarning dataclass."""

    def test_warning_dataclass_fields(self):
        """ClusterSizeWarning has all required fields."""
        from cluster_analysis import ClusterSizeWarning

        warning = ClusterSizeWarning(
            should_warn=True,
            cluster_size=5,
            prefix="auth",
            has_subsystem=False,
            threshold=5,
        )

        assert warning.should_warn is True
        assert warning.cluster_size == 5
        assert warning.prefix == "auth"
        assert warning.has_subsystem is False
        assert warning.threshold == 5


class TestCheckClusterSize:
    """Tests for the check_cluster_size() function."""

    def test_below_threshold_no_warning(self, temp_project):
        """Creating 4th chunk in a cluster doesn't trigger warning (default threshold 5)."""
        from cluster_analysis import check_cluster_size
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create 3 existing chunks with prefix "auth"
        for name in ["auth_login", "auth_logout", "auth_refresh"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        # Need an IMPLEMENTING chunk to create more, make one with different prefix
        chunks.create_chunk(None, "other_feature")
        chunks.update_status("other_feature", ChunkStatus.ACTIVE)

        # Check for 4th "auth" chunk (include_new_chunk=True adds 1)
        warning = check_cluster_size("auth", temp_project, include_new_chunk=True)

        assert warning.should_warn is False
        assert warning.cluster_size == 4  # 3 existing + 1 new
        assert warning.prefix == "auth"
        assert warning.threshold == 5

    def test_at_threshold_triggers_warning(self, temp_project):
        """Creating 5th chunk triggers warning (default threshold 5)."""
        from cluster_analysis import check_cluster_size
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create 4 existing chunks with prefix "auth"
        for name in ["auth_login", "auth_logout", "auth_refresh", "auth_verify"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        # Check for 5th "auth" chunk
        warning = check_cluster_size("auth", temp_project, include_new_chunk=True)

        assert warning.should_warn is True
        assert warning.cluster_size == 5
        assert warning.prefix == "auth"

    def test_above_threshold_triggers_warning(self, temp_project):
        """Creating 6th chunk triggers warning."""
        from cluster_analysis import check_cluster_size
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create 5 existing chunks with prefix "auth"
        for name in ["auth_login", "auth_logout", "auth_refresh", "auth_verify", "auth_reset"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        # Check for 6th "auth" chunk
        warning = check_cluster_size("auth", temp_project, include_new_chunk=True)

        assert warning.should_warn is True
        assert warning.cluster_size == 6
        assert warning.prefix == "auth"

    def test_no_warning_when_subsystem_exists(self, temp_project):
        """No warning if subsystem exists for prefix."""
        from cluster_analysis import check_cluster_size
        from chunks import Chunks
        from subsystems import Subsystems
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)
        subsystems = Subsystems(temp_project)

        # Create subsystem for "auth"
        subsystems.create_subsystem("auth")

        # Create 4 existing chunks with prefix "auth"
        for name in ["auth_login", "auth_logout", "auth_refresh", "auth_verify"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        # Check for 5th "auth" chunk - should NOT warn because subsystem exists
        warning = check_cluster_size("auth", temp_project, include_new_chunk=True)

        assert warning.should_warn is False
        assert warning.has_subsystem is True
        assert warning.cluster_size == 5  # Still counted

    def test_configurable_threshold(self, temp_project):
        """Custom threshold in .ve-config.yaml is respected."""
        from cluster_analysis import check_cluster_size
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)

        # Create config with custom threshold
        config_path = temp_project / ".ve-config.yaml"
        config_path.write_text("cluster_subsystem_threshold: 3\n")

        chunks = Chunks(temp_project)

        # Create 2 existing chunks with prefix "auth"
        for name in ["auth_login", "auth_logout"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        # Check for 3rd "auth" chunk - should warn with threshold=3
        warning = check_cluster_size("auth", temp_project, include_new_chunk=True)

        assert warning.should_warn is True
        assert warning.cluster_size == 3
        assert warning.threshold == 3

    def test_no_include_new_chunk(self, temp_project):
        """include_new_chunk=False only counts existing chunks."""
        from cluster_analysis import check_cluster_size
        from chunks import Chunks
        from models import ChunkStatus

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create 5 existing chunks with prefix "auth"
        for name in ["auth_login", "auth_logout", "auth_refresh", "auth_verify", "auth_reset"]:
            chunks.create_chunk(None, name)
            chunks.update_status(name, ChunkStatus.ACTIVE)

        # Check without adding new chunk
        warning = check_cluster_size("auth", temp_project, include_new_chunk=False)

        assert warning.cluster_size == 5  # Just the existing 5
        assert warning.should_warn is True  # Still at threshold

    def test_empty_cluster_no_warning(self, temp_project):
        """Creating first chunk in a new prefix doesn't warn."""
        from cluster_analysis import check_cluster_size

        make_ve_initialized_git_repo(temp_project)

        # Check for first "newprefix" chunk
        warning = check_cluster_size("newprefix", temp_project, include_new_chunk=True)

        assert warning.should_warn is False
        assert warning.cluster_size == 1


class TestFormatClusterWarning:
    """Tests for the format_cluster_warning() function."""

    def test_formats_warning_message(self):
        """Warning message includes ordinal, prefix, and suggestion."""
        from cluster_analysis import ClusterSizeWarning, format_cluster_warning

        warning = ClusterSizeWarning(
            should_warn=True,
            cluster_size=6,
            prefix="orch",
            has_subsystem=False,
            threshold=5,
        )

        message = format_cluster_warning(warning)

        assert "6th" in message
        assert "orch_*" in message
        assert "/subsystem-discover" in message

    def test_ordinal_formatting(self):
        """Ordinal numbers are formatted correctly."""
        from cluster_analysis import _ordinal

        assert _ordinal(1) == "1st"
        assert _ordinal(2) == "2nd"
        assert _ordinal(3) == "3rd"
        assert _ordinal(4) == "4th"
        assert _ordinal(5) == "5th"
        assert _ordinal(11) == "11th"
        assert _ordinal(12) == "12th"
        assert _ordinal(13) == "13th"
        assert _ordinal(21) == "21st"
        assert _ordinal(22) == "22nd"
        assert _ordinal(23) == "23rd"
        assert _ordinal(100) == "100th"
        assert _ordinal(101) == "101st"


class TestCLICreateEmitsWarning:
    """Tests for ve chunk create emitting cluster warnings."""

    def test_create_emits_warning_at_threshold(self, temp_project, runner):
        """ve chunk create shows warning when threshold exceeded."""
        from chunks import Chunks
        from models import ChunkStatus
        from ve import cli

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create 4 existing chunks with prefix "auth" (all as FUTURE to avoid guard)
        for name in ["auth_login", "auth_logout", "auth_refresh", "auth_verify"]:
            chunks.create_chunk(None, name, status="FUTURE")

        # Create 5th "auth" chunk - should show warning
        result = runner.invoke(
            cli, ["chunk", "create", "auth_reset", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert "Created" in result.output
        assert "5th" in result.output or "auth_*" in result.output
        assert "/subsystem-discover" in result.output

    def test_create_no_warning_below_threshold(self, temp_project, runner):
        """ve chunk create doesn't show warning below threshold."""
        from chunks import Chunks
        from models import ChunkStatus
        from ve import cli

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create 3 existing chunks with prefix "auth" (all as FUTURE to avoid guard)
        for name in ["auth_login", "auth_logout", "auth_refresh"]:
            chunks.create_chunk(None, name, status="FUTURE")

        # Create 4th "auth" chunk - should NOT show warning
        result = runner.invoke(
            cli, ["chunk", "create", "auth_verify", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert "Created" in result.output
        assert "/subsystem-discover" not in result.output

    def test_create_no_warning_when_subsystem_exists(self, temp_project, runner):
        """ve chunk create doesn't show warning if subsystem exists."""
        from chunks import Chunks
        from subsystems import Subsystems
        from models import ChunkStatus
        from ve import cli

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)
        subsystems = Subsystems(temp_project)

        # Create subsystem for "auth"
        subsystems.create_subsystem("auth")

        # Create 4 existing chunks with prefix "auth" (all as FUTURE to avoid guard)
        for name in ["auth_login", "auth_logout", "auth_refresh", "auth_verify"]:
            chunks.create_chunk(None, name, status="FUTURE")

        # Create 5th "auth" chunk - should NOT show warning (subsystem exists)
        result = runner.invoke(
            cli, ["chunk", "create", "auth_reset", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert "Created" in result.output
        assert "/subsystem-discover" not in result.output

    def test_create_future_chunk_emits_warning(self, temp_project, runner):
        """ve chunk create --future also shows warning when threshold exceeded."""
        from chunks import Chunks
        from models import ChunkStatus
        from ve import cli

        make_ve_initialized_git_repo(temp_project)
        chunks = Chunks(temp_project)

        # Create 4 existing chunks with prefix "auth"
        for name in ["auth_login", "auth_logout", "auth_refresh", "auth_verify"]:
            chunks.create_chunk(None, name, status="FUTURE")

        # Create 5th "auth" chunk with --future flag
        result = runner.invoke(
            cli, ["chunk", "create", "auth_reset", "--future", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert "Created" in result.output
        # Warning should still appear for --future chunks
        assert "5th" in result.output or "auth_*" in result.output
        assert "/subsystem-discover" in result.output


class TestVeConfigThreshold:
    """Tests for cluster_subsystem_threshold in VeConfig."""

    def test_default_threshold_is_5(self, temp_project):
        """Default threshold is 5 when config file doesn't exist."""
        from template_system import load_ve_config

        make_ve_initialized_git_repo(temp_project)

        config = load_ve_config(temp_project)

        assert config.cluster_subsystem_threshold == 5

    def test_loads_custom_threshold(self, temp_project):
        """Custom threshold is loaded from .ve-config.yaml."""
        from template_system import load_ve_config

        make_ve_initialized_git_repo(temp_project)
        config_path = temp_project / ".ve-config.yaml"
        config_path.write_text("cluster_subsystem_threshold: 10\n")

        config = load_ve_config(temp_project)

        assert config.cluster_subsystem_threshold == 10

    def test_as_dict_includes_threshold(self, temp_project):
        """VeConfig.as_dict() includes cluster_subsystem_threshold."""
        from template_system import load_ve_config

        make_ve_initialized_git_repo(temp_project)
        config_path = temp_project / ".ve-config.yaml"
        config_path.write_text("cluster_subsystem_threshold: 7\n")

        config = load_ve_config(temp_project)
        config_dict = config.as_dict()

        assert "cluster_subsystem_threshold" in config_dict
        assert config_dict["cluster_subsystem_threshold"] == 7
