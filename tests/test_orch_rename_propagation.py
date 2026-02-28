# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_rename_propagation - Rename propagation tests
"""Tests for orchestrator chunk rename propagation.

When a chunk is renamed during a phase (e.g., via `ve chunk suggest-prefix`),
the orchestrator must detect the rename and propagate the new name through
all its data structures: database, filesystem, git branches, and cross-references.
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import shutil
import subprocess

from orchestrator.models import (
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
    ConflictVerdict,
)
from orchestrator.state import StateStore
from orchestrator.worktree import WorktreeManager, WorktreeError


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / ".ve" / "orchestrator.db"


@pytest.fixture
def store(db_path):
    """Create and initialize a state store."""
    store = StateStore(db_path)
    store.initialize()
    yield store
    store.close()


@pytest.fixture
def sample_work_unit():
    """Create a sample work unit for testing."""
    now = datetime.now(timezone.utc)
    return WorkUnit(
        chunk="old_name",
        phase=WorkUnitPhase.PLAN,
        status=WorkUnitStatus.RUNNING,
        blocked_by=[],
        worktree="/tmp/worktree",
        baseline_implementing=["old_name"],
        created_at=now,
        updated_at=now,
    )


class TestWorkUnitBaselineImplementing:
    """Tests for baseline_implementing field on WorkUnit."""

    def test_baseline_implementing_default_empty(self):
        """baseline_implementing defaults to empty list."""
        now = datetime.now(timezone.utc)
        unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        assert unit.baseline_implementing == []

    def test_baseline_implementing_persisted(self, store):
        """baseline_implementing is persisted to database."""
        now = datetime.now(timezone.utc)
        unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            baseline_implementing=["chunk_a", "chunk_b"],
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(unit)

        retrieved = store.get_work_unit("test")
        assert retrieved.baseline_implementing == ["chunk_a", "chunk_b"]

    def test_baseline_implementing_updated(self, store, sample_work_unit):
        """baseline_implementing can be updated."""
        store.create_work_unit(sample_work_unit)

        sample_work_unit.baseline_implementing = ["new_name"]
        sample_work_unit.updated_at = datetime.now(timezone.utc)
        store.update_work_unit(sample_work_unit)

        retrieved = store.get_work_unit(sample_work_unit.chunk)
        assert retrieved.baseline_implementing == ["new_name"]


class TestStateStoreRenameMethods:
    """Tests for StateStore rename propagation methods."""

    def test_rename_work_unit_success(self, store, sample_work_unit):
        """Work unit can be renamed atomically."""
        store.create_work_unit(sample_work_unit)

        renamed = store.rename_work_unit("old_name", "new_name")

        assert renamed.chunk == "new_name"
        assert renamed.phase == sample_work_unit.phase
        assert renamed.status == sample_work_unit.status
        assert store.get_work_unit("old_name") is None
        assert store.get_work_unit("new_name") is not None

    def test_rename_work_unit_not_found(self, store):
        """Renaming nonexistent work unit raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            store.rename_work_unit("nonexistent", "new_name")

    def test_rename_work_unit_target_exists(self, store, sample_work_unit):
        """Renaming to existing chunk name raises ValueError."""
        store.create_work_unit(sample_work_unit)

        # Create another work unit with the target name
        now = datetime.now(timezone.utc)
        existing = WorkUnit(
            chunk="new_name",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(existing)

        with pytest.raises(ValueError, match="already exists"):
            store.rename_work_unit("old_name", "new_name")

    def test_update_blocked_by_references(self, store, sample_work_unit):
        """blocked_by references are updated when chunk is renamed."""
        store.create_work_unit(sample_work_unit)

        # Create a work unit blocked by old_name
        now = datetime.now(timezone.utc)
        blocked = WorkUnit(
            chunk="blocked_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.BLOCKED,
            blocked_by=["old_name", "other_chunk"],
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(blocked)

        updated_count = store.update_blocked_by_references("old_name", "new_name")

        assert updated_count == 1
        retrieved = store.get_work_unit("blocked_chunk")
        assert "new_name" in retrieved.blocked_by
        assert "old_name" not in retrieved.blocked_by
        assert "other_chunk" in retrieved.blocked_by

    def test_update_conflict_verdicts_references(self, store, sample_work_unit):
        """conflict_verdicts references are re-keyed when chunk is renamed."""
        store.create_work_unit(sample_work_unit)

        # Create a work unit with conflict verdict for old_name
        now = datetime.now(timezone.utc)
        other = WorkUnit(
            chunk="other_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            conflict_verdicts={"old_name": ConflictVerdict.SERIALIZE.value},
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(other)

        updated_count = store.update_conflict_verdicts_references("old_name", "new_name")

        assert updated_count == 1
        retrieved = store.get_work_unit("other_chunk")
        assert "new_name" in retrieved.conflict_verdicts
        assert "old_name" not in retrieved.conflict_verdicts

    def test_update_conflict_analyses_references(self, store):
        """conflict_analyses table rows are updated when chunk is renamed."""
        from orchestrator.models import ConflictAnalysis

        now = datetime.now(timezone.utc)
        analysis = ConflictAnalysis(
            chunk_a="old_name",
            chunk_b="other_chunk",
            verdict=ConflictVerdict.INDEPENDENT,
            confidence=0.9,
            reason="No overlap",
            analysis_stage="GOAL",
            created_at=now,
        )
        store.save_conflict_analysis(analysis)

        updated_count = store.update_conflict_analyses_references("old_name", "new_name")

        assert updated_count == 1
        # The analysis should now be keyed by new_name
        result = store.get_conflict_analysis("new_name", "other_chunk")
        assert result is not None
        assert result.chunk_a == "new_name" or result.chunk_b == "new_name"


class TestWorktreeManagerRenameMethods:
    """Tests for WorktreeManager rename methods."""

    @pytest.fixture
    def git_repo(self, tmp_path):
        """Create a temporary git repository."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        subprocess.run(["git", "init"], cwd=repo_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo_path,
            capture_output=True,
        )
        # Create initial commit
        (repo_path / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            capture_output=True,
        )
        return repo_path

    @pytest.fixture
    def worktree_manager(self, git_repo):
        """Create a WorktreeManager."""
        return WorktreeManager(git_repo)

    def test_rename_branch_success(self, worktree_manager, git_repo):
        """Git branch can be renamed."""
        # Create the old branch
        subprocess.run(
            ["git", "branch", "orch/old_name"],
            cwd=git_repo,
            capture_output=True,
        )

        worktree_manager.rename_branch("old_name", "new_name")

        # Verify old branch gone, new branch exists
        result = subprocess.run(
            ["git", "branch", "--list", "orch/old_name"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == ""

        result = subprocess.run(
            ["git", "branch", "--list", "orch/new_name"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert "orch/new_name" in result.stdout

    def test_rename_branch_source_not_found(self, worktree_manager):
        """Renaming nonexistent branch raises WorktreeError."""
        with pytest.raises(WorktreeError, match="does not exist"):
            worktree_manager.rename_branch("nonexistent", "new_name")

    def test_rename_branch_target_exists(self, worktree_manager, git_repo):
        """Renaming to existing branch raises WorktreeError."""
        # Create both branches
        subprocess.run(
            ["git", "branch", "orch/old_name"],
            cwd=git_repo,
            capture_output=True,
        )
        subprocess.run(
            ["git", "branch", "orch/new_name"],
            cwd=git_repo,
            capture_output=True,
        )

        with pytest.raises(WorktreeError, match="already exists"):
            worktree_manager.rename_branch("old_name", "new_name")

    def test_rename_chunk_directory_success(self, worktree_manager, git_repo):
        """Chunk directory can be renamed."""
        # Create old chunk directory
        old_path = git_repo / ".ve" / "chunks" / "old_name"
        old_path.mkdir(parents=True)
        (old_path / "worktree").mkdir()
        (old_path / "log").mkdir()
        (old_path / "base_branch").write_text("main")

        worktree_manager.rename_chunk_directory("old_name", "new_name")

        # Verify old path gone, new path exists with contents
        assert not old_path.exists()
        new_path = git_repo / ".ve" / "chunks" / "new_name"
        assert new_path.exists()
        assert (new_path / "worktree").exists()
        assert (new_path / "log").exists()
        assert (new_path / "base_branch").exists()

    def test_rename_chunk_directory_source_not_found(self, worktree_manager):
        """Renaming nonexistent directory raises WorktreeError."""
        with pytest.raises(WorktreeError, match="does not exist"):
            worktree_manager.rename_chunk_directory("nonexistent", "new_name")

    def test_rename_chunk_directory_target_exists(self, worktree_manager, git_repo):
        """Renaming to existing directory raises WorktreeError."""
        # Create both directories
        (git_repo / ".ve" / "chunks" / "old_name").mkdir(parents=True)
        (git_repo / ".ve" / "chunks" / "new_name").mkdir(parents=True)

        with pytest.raises(WorktreeError, match="already exists"):
            worktree_manager.rename_chunk_directory("old_name", "new_name")


class TestRenameDetection:
    """Tests for _detect_rename helper method."""

    @pytest.fixture
    def mock_scheduler(self, store, tmp_path):
        """Create a mock scheduler with necessary dependencies."""
        from orchestrator.scheduler import Scheduler
        from orchestrator.agent import AgentRunner
        from orchestrator.models import OrchestratorConfig

        worktree_manager = Mock(spec=WorktreeManager)
        agent_runner = Mock(spec=AgentRunner)
        config = OrchestratorConfig()

        scheduler = Scheduler(
            store=store,
            worktree_manager=worktree_manager,
            agent_runner=agent_runner,
            config=config,
            project_dir=tmp_path,
        )
        return scheduler

    def test_detect_no_rename(self, mock_scheduler, sample_work_unit, tmp_path):
        """No rename detected when chunk is still present."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Mock Chunks.list_implementing_chunks to return old_name
        with patch("chunks.Chunks") as MockChunks:
            mock_chunks = Mock()
            mock_chunks.list_implementing_chunks.return_value = ["old_name"]
            MockChunks.return_value = mock_chunks

            result = mock_scheduler._detect_rename(sample_work_unit, worktree_path)

        assert result is None

    def test_detect_rename_single_new_chunk(self, mock_scheduler, sample_work_unit, tmp_path):
        """Rename detected when exactly one new chunk replaces the old."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Mock Chunks.list_implementing_chunks to return new_name
        with patch("chunks.Chunks") as MockChunks:
            mock_chunks = Mock()
            mock_chunks.list_implementing_chunks.return_value = ["new_name"]
            MockChunks.return_value = mock_chunks

            result = mock_scheduler._detect_rename(sample_work_unit, worktree_path)

        assert result == ("old_name", "new_name")

    def test_detect_rename_ambiguous_multiple_new(self, mock_scheduler, sample_work_unit, tmp_path):
        """No rename detected when multiple new chunks appear."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Mock Chunks.list_implementing_chunks to return multiple new chunks
        with patch("chunks.Chunks") as MockChunks:
            mock_chunks = Mock()
            mock_chunks.list_implementing_chunks.return_value = ["new_a", "new_b"]
            MockChunks.return_value = mock_chunks

            result = mock_scheduler._detect_rename(sample_work_unit, worktree_path)

        assert result is None

    def test_detect_rename_chunk_disappeared(self, mock_scheduler, sample_work_unit, tmp_path):
        """No rename detected when chunk disappeared with no replacement."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Mock Chunks.list_implementing_chunks to return empty list
        with patch("chunks.Chunks") as MockChunks:
            mock_chunks = Mock()
            mock_chunks.list_implementing_chunks.return_value = []
            MockChunks.return_value = mock_chunks

            result = mock_scheduler._detect_rename(sample_work_unit, worktree_path)

        assert result is None

    def test_detect_rename_no_baseline(self, mock_scheduler, sample_work_unit, tmp_path):
        """No rename detected when no baseline was captured."""
        sample_work_unit.baseline_implementing = []
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        result = mock_scheduler._detect_rename(sample_work_unit, worktree_path)

        assert result is None


class TestListImplementingChunks:
    """Tests for Chunks.list_implementing_chunks method."""

    @pytest.fixture
    def project_dir(self, tmp_path):
        """Create a temporary project directory with chunks."""
        project = tmp_path / "project"
        project.mkdir()
        (project / "docs" / "chunks").mkdir(parents=True)
        return project

    def _create_chunk(self, project_dir, name, status):
        """Helper to create a chunk with given status."""
        chunk_dir = project_dir / "docs" / "chunks" / name
        chunk_dir.mkdir()
        (chunk_dir / "GOAL.md").write_text(f"""---
status: {status}
---
# {name}
""")

    def test_list_implementing_empty(self, project_dir):
        """Returns empty list when no chunks exist."""
        from chunks import Chunks
        chunks = Chunks(project_dir)
        result = chunks.list_implementing_chunks()
        assert result == []

    def test_list_implementing_single(self, project_dir):
        """Returns single IMPLEMENTING chunk."""
        self._create_chunk(project_dir, "test_chunk", "IMPLEMENTING")

        from chunks import Chunks
        chunks = Chunks(project_dir)
        result = chunks.list_implementing_chunks()

        assert result == ["test_chunk"]

    def test_list_implementing_multiple(self, project_dir):
        """Returns all IMPLEMENTING chunks."""
        self._create_chunk(project_dir, "chunk_a", "IMPLEMENTING")
        self._create_chunk(project_dir, "chunk_b", "IMPLEMENTING")
        self._create_chunk(project_dir, "chunk_c", "ACTIVE")

        from chunks import Chunks
        chunks = Chunks(project_dir)
        result = chunks.list_implementing_chunks()

        assert len(result) == 2
        assert "chunk_a" in result
        assert "chunk_b" in result
        assert "chunk_c" not in result

    def test_list_implementing_excludes_other_statuses(self, project_dir):
        """Excludes FUTURE, ACTIVE, and HISTORICAL chunks."""
        self._create_chunk(project_dir, "implementing", "IMPLEMENTING")
        self._create_chunk(project_dir, "future", "FUTURE")
        self._create_chunk(project_dir, "active", "ACTIVE")
        self._create_chunk(project_dir, "historical", "HISTORICAL")

        from chunks import Chunks
        chunks = Chunks(project_dir)
        result = chunks.list_implementing_chunks()

        assert result == ["implementing"]


class TestDatabaseMigrationV14:
    """Tests for database migration adding baseline_implementing column."""

    def test_migration_v14_adds_column(self, tmp_path):
        """Migration v14 adds the baseline_implementing column."""
        db_path = tmp_path / ".ve" / "orchestrator.db"
        store = StateStore(db_path)
        store.initialize()

        # Check the column exists
        cursor = store.connection.execute("PRAGMA table_info(work_units)")
        columns = {row[1] for row in cursor.fetchall()}

        assert "baseline_implementing" in columns
        store.close()

    def test_migration_backwards_compatible(self, tmp_path):
        """Work units created before migration can be read with None baseline."""
        db_path = tmp_path / ".ve" / "orchestrator.db"
        store = StateStore(db_path)
        store.initialize()

        # Insert a work unit without baseline_implementing (simulating pre-migration)
        now = datetime.now(timezone.utc)
        store.connection.execute(
            """
            INSERT INTO work_units
                (chunk, phase, status, blocked_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("legacy_chunk", "PLAN", "READY", "[]", now.isoformat(), now.isoformat()),
        )

        # Should be able to read it with empty baseline_implementing
        unit = store.get_work_unit("legacy_chunk")
        assert unit is not None
        assert unit.baseline_implementing == []
        store.close()
