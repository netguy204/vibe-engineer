# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_foundation - State store tests
# Chunk: docs/chunks/orch_attention_reason - Attention reason persistence tests
"""Tests for the orchestrator SQLite state store."""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from orchestrator.models import WorkUnit, WorkUnitPhase, WorkUnitStatus
from orchestrator.state import StateStore, get_default_db_path


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
        chunk="test_chunk",
        phase=WorkUnitPhase.GOAL,
        status=WorkUnitStatus.READY,
        blocked_by=[],
        worktree=None,
        created_at=now,
        updated_at=now,
    )


class TestStateStoreInitialization:
    """Tests for database initialization."""

    def test_creates_database_directory(self, tmp_path):
        """Database directory is created if it doesn't exist."""
        db_path = tmp_path / "nested" / "dir" / "orchestrator.db"
        store = StateStore(db_path)
        store.initialize()
        store.close()

        assert db_path.parent.exists()

    def test_creates_tables(self, store, db_path):
        """All required tables are created."""
        cursor = store.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}

        assert "schema_migrations" in tables
        assert "work_units" in tables
        assert "status_log" in tables

    def test_records_migration_version(self, store):
        """Migration version is recorded."""
        cursor = store.connection.execute(
            "SELECT version FROM schema_migrations"
        )
        versions = [row[0] for row in cursor.fetchall()]

        assert 1 in versions

    def test_idempotent_initialization(self, db_path):
        """Multiple initializations don't fail."""
        store1 = StateStore(db_path)
        store1.initialize()
        store1.close()

        store2 = StateStore(db_path)
        store2.initialize()
        store2.close()

        # Should not raise


class TestWorkUnitCRUD:
    """Tests for work unit CRUD operations."""

    def test_create_work_unit(self, store, sample_work_unit):
        """Work units can be created."""
        created = store.create_work_unit(sample_work_unit)

        assert created.chunk == sample_work_unit.chunk
        assert created.phase == sample_work_unit.phase
        assert created.status == sample_work_unit.status

    def test_create_duplicate_raises(self, store, sample_work_unit):
        """Creating a duplicate work unit raises ValueError."""
        store.create_work_unit(sample_work_unit)

        with pytest.raises(ValueError, match="already exists"):
            store.create_work_unit(sample_work_unit)

    def test_get_work_unit(self, store, sample_work_unit):
        """Work units can be retrieved by chunk name."""
        store.create_work_unit(sample_work_unit)

        retrieved = store.get_work_unit(sample_work_unit.chunk)

        assert retrieved is not None
        assert retrieved.chunk == sample_work_unit.chunk
        assert retrieved.phase == sample_work_unit.phase
        assert retrieved.status == sample_work_unit.status

    def test_get_nonexistent_returns_none(self, store):
        """Getting a nonexistent work unit returns None."""
        result = store.get_work_unit("nonexistent")
        assert result is None

    def test_update_work_unit(self, store, sample_work_unit):
        """Work units can be updated."""
        store.create_work_unit(sample_work_unit)

        # Update the status
        sample_work_unit.status = WorkUnitStatus.RUNNING
        sample_work_unit.updated_at = datetime.now(timezone.utc)
        updated = store.update_work_unit(sample_work_unit)

        assert updated.status == WorkUnitStatus.RUNNING

        # Verify persisted
        retrieved = store.get_work_unit(sample_work_unit.chunk)
        assert retrieved.status == WorkUnitStatus.RUNNING

    def test_update_nonexistent_raises(self, store, sample_work_unit):
        """Updating a nonexistent work unit raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            store.update_work_unit(sample_work_unit)

    def test_delete_work_unit(self, store, sample_work_unit):
        """Work units can be deleted."""
        store.create_work_unit(sample_work_unit)

        result = store.delete_work_unit(sample_work_unit.chunk)

        assert result is True
        assert store.get_work_unit(sample_work_unit.chunk) is None

    def test_delete_nonexistent_returns_false(self, store):
        """Deleting a nonexistent work unit returns False."""
        result = store.delete_work_unit("nonexistent")
        assert result is False


class TestWorkUnitListing:
    """Tests for work unit listing operations."""

    def test_list_all_work_units(self, store):
        """All work units can be listed."""
        now = datetime.now(timezone.utc)

        for i, status in enumerate([WorkUnitStatus.READY, WorkUnitStatus.RUNNING]):
            unit = WorkUnit(
                chunk=f"chunk_{i}",
                phase=WorkUnitPhase.GOAL,
                status=status,
                blocked_by=[],
                worktree=None,
                created_at=now + timedelta(seconds=i),
                updated_at=now + timedelta(seconds=i),
            )
            store.create_work_unit(unit)

        units = store.list_work_units()

        assert len(units) == 2
        # Should be ordered by created_at
        assert units[0].chunk == "chunk_0"
        assert units[1].chunk == "chunk_1"

    def test_list_work_units_by_status(self, store):
        """Work units can be filtered by status."""
        now = datetime.now(timezone.utc)

        for i, status in enumerate([
            WorkUnitStatus.READY,
            WorkUnitStatus.RUNNING,
            WorkUnitStatus.READY,
        ]):
            unit = WorkUnit(
                chunk=f"chunk_{i}",
                phase=WorkUnitPhase.GOAL,
                status=status,
                blocked_by=[],
                worktree=None,
                created_at=now + timedelta(seconds=i),
                updated_at=now + timedelta(seconds=i),
            )
            store.create_work_unit(unit)

        ready_units = store.list_work_units(status=WorkUnitStatus.READY)

        assert len(ready_units) == 2
        assert all(u.status == WorkUnitStatus.READY for u in ready_units)

    def test_count_by_status(self, store):
        """Work units can be counted by status."""
        now = datetime.now(timezone.utc)

        for i, status in enumerate([
            WorkUnitStatus.READY,
            WorkUnitStatus.RUNNING,
            WorkUnitStatus.READY,
            WorkUnitStatus.BLOCKED,
        ]):
            unit = WorkUnit(
                chunk=f"chunk_{i}",
                phase=WorkUnitPhase.GOAL,
                status=status,
                blocked_by=[],
                worktree=None,
                created_at=now + timedelta(seconds=i),
                updated_at=now + timedelta(seconds=i),
            )
            store.create_work_unit(unit)

        counts = store.count_by_status()

        assert counts["READY"] == 2
        assert counts["RUNNING"] == 1
        assert counts["BLOCKED"] == 1


class TestStatusLogging:
    """Tests for status transition logging."""

    def test_logs_initial_status(self, store, sample_work_unit):
        """Initial status is logged when work unit is created."""
        store.create_work_unit(sample_work_unit)

        history = store.get_status_history(sample_work_unit.chunk)

        assert len(history) == 1
        assert history[0]["old_status"] is None
        assert history[0]["new_status"] == "READY"

    def test_logs_status_transitions(self, store, sample_work_unit):
        """Status transitions are logged when work unit is updated."""
        store.create_work_unit(sample_work_unit)

        # Transition to RUNNING
        sample_work_unit.status = WorkUnitStatus.RUNNING
        sample_work_unit.updated_at = datetime.now(timezone.utc)
        store.update_work_unit(sample_work_unit)

        # Transition to DONE
        sample_work_unit.status = WorkUnitStatus.DONE
        sample_work_unit.updated_at = datetime.now(timezone.utc)
        store.update_work_unit(sample_work_unit)

        history = store.get_status_history(sample_work_unit.chunk)

        assert len(history) == 3
        assert history[0]["old_status"] is None
        assert history[0]["new_status"] == "READY"
        assert history[1]["old_status"] == "READY"
        assert history[1]["new_status"] == "RUNNING"
        assert history[2]["old_status"] == "RUNNING"
        assert history[2]["new_status"] == "DONE"

    def test_no_log_for_same_status(self, store, sample_work_unit):
        """No log entry when status doesn't change."""
        store.create_work_unit(sample_work_unit)

        # Update without changing status
        sample_work_unit.phase = WorkUnitPhase.PLAN
        sample_work_unit.updated_at = datetime.now(timezone.utc)
        store.update_work_unit(sample_work_unit)

        history = store.get_status_history(sample_work_unit.chunk)

        # Only initial status logged
        assert len(history) == 1


class TestBlockedBy:
    """Tests for blocked_by field handling."""

    def test_stores_blocked_by_list(self, store):
        """blocked_by list is correctly stored and retrieved."""
        now = datetime.now(timezone.utc)
        unit = WorkUnit(
            chunk="dependent_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.BLOCKED,
            blocked_by=["chunk_a", "chunk_b", "chunk_c"],
            worktree=None,
            created_at=now,
            updated_at=now,
        )

        store.create_work_unit(unit)
        retrieved = store.get_work_unit("dependent_chunk")

        assert retrieved.blocked_by == ["chunk_a", "chunk_b", "chunk_c"]

    def test_updates_blocked_by_list(self, store):
        """blocked_by list can be updated."""
        now = datetime.now(timezone.utc)
        unit = WorkUnit(
            chunk="dependent_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.BLOCKED,
            blocked_by=["chunk_a", "chunk_b"],
            worktree=None,
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(unit)

        # Remove one blocker
        unit.blocked_by = ["chunk_a"]
        unit.updated_at = datetime.now(timezone.utc)
        store.update_work_unit(unit)

        retrieved = store.get_work_unit("dependent_chunk")
        assert retrieved.blocked_by == ["chunk_a"]


class TestDefaultDbPath:
    """Tests for get_default_db_path."""

    def test_returns_correct_path(self, tmp_path):
        """Returns the expected path under .ve directory."""
        result = get_default_db_path(tmp_path)

        assert result == tmp_path / ".ve" / "orchestrator.db"


class TestAttentionReasonPersistence:
    """Tests for attention_reason field persistence."""

    def test_stores_attention_reason(self, store):
        """attention_reason is stored on create."""
        now = datetime.now(timezone.utc)
        unit = WorkUnit(
            chunk="attention_test",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.NEEDS_ATTENTION,
            attention_reason="Connection timeout while accessing API",
            created_at=now,
            updated_at=now,
        )

        store.create_work_unit(unit)
        retrieved = store.get_work_unit("attention_test")

        assert retrieved.attention_reason == "Connection timeout while accessing API"

    def test_updates_attention_reason(self, store, sample_work_unit):
        """attention_reason can be updated."""
        store.create_work_unit(sample_work_unit)

        # Update with attention_reason
        sample_work_unit.status = WorkUnitStatus.NEEDS_ATTENTION
        sample_work_unit.attention_reason = "Question: Which framework should I use?"
        sample_work_unit.updated_at = datetime.now(timezone.utc)
        store.update_work_unit(sample_work_unit)

        retrieved = store.get_work_unit(sample_work_unit.chunk)
        assert retrieved.attention_reason == "Question: Which framework should I use?"

    def test_attention_reason_null_by_default(self, store, sample_work_unit):
        """attention_reason is None by default."""
        store.create_work_unit(sample_work_unit)
        retrieved = store.get_work_unit(sample_work_unit.chunk)

        assert retrieved.attention_reason is None

    def test_clears_attention_reason(self, store):
        """attention_reason can be cleared (set to None)."""
        now = datetime.now(timezone.utc)
        unit = WorkUnit(
            chunk="attention_test",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.NEEDS_ATTENTION,
            attention_reason="Some error",
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(unit)

        # Clear the attention_reason
        unit.status = WorkUnitStatus.READY
        unit.attention_reason = None
        unit.updated_at = datetime.now(timezone.utc)
        store.update_work_unit(unit)

        retrieved = store.get_work_unit("attention_test")
        assert retrieved.attention_reason is None

    def test_attention_reason_preserved_in_list(self, store):
        """attention_reason is included when listing work units."""
        now = datetime.now(timezone.utc)
        unit = WorkUnit(
            chunk="attention_test",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.NEEDS_ATTENTION,
            attention_reason="Agent asked a question",
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(unit)

        units = store.list_work_units()

        assert len(units) == 1
        assert units[0].attention_reason == "Agent asked a question"


class TestDisplacedChunkPersistence:
    """Tests for displaced_chunk field persistence."""

    def test_stores_displaced_chunk(self, store):
        """displaced_chunk is stored on create."""
        now = datetime.now(timezone.utc)
        unit = WorkUnit(
            chunk="target_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            displaced_chunk="existing_chunk",
            created_at=now,
            updated_at=now,
        )

        store.create_work_unit(unit)
        retrieved = store.get_work_unit("target_chunk")

        assert retrieved.displaced_chunk == "existing_chunk"

    def test_updates_displaced_chunk(self, store, sample_work_unit):
        """displaced_chunk can be updated."""
        store.create_work_unit(sample_work_unit)

        # Update with displaced_chunk
        sample_work_unit.displaced_chunk = "some_chunk"
        sample_work_unit.updated_at = datetime.now(timezone.utc)
        store.update_work_unit(sample_work_unit)

        retrieved = store.get_work_unit(sample_work_unit.chunk)
        assert retrieved.displaced_chunk == "some_chunk"

    def test_displaced_chunk_null_by_default(self, store, sample_work_unit):
        """displaced_chunk is None by default."""
        store.create_work_unit(sample_work_unit)
        retrieved = store.get_work_unit(sample_work_unit.chunk)

        assert retrieved.displaced_chunk is None

    def test_displaced_chunk_preserved_in_list(self, store):
        """displaced_chunk is included when listing work units."""
        now = datetime.now(timezone.utc)
        unit = WorkUnit(
            chunk="target_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            displaced_chunk="existing_chunk",
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(unit)

        units = store.list_work_units()

        assert len(units) == 1
        assert units[0].displaced_chunk == "existing_chunk"


class TestListBlockedByChunk:
    """Tests for list_blocked_by_chunk method."""

    def test_returns_blocked_units(self, store):
        """Returns work units that have the chunk in blocked_by."""
        now = datetime.now(timezone.utc)

        # Create blocker chunk
        blocker = WorkUnit(
            chunk="blocker_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(blocker)

        # Create blocked chunks
        blocked_a = WorkUnit(
            chunk="blocked_a",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.BLOCKED,
            blocked_by=["blocker_chunk"],
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(blocked_a)

        blocked_b = WorkUnit(
            chunk="blocked_b",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.BLOCKED,
            blocked_by=["blocker_chunk", "other_chunk"],
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(blocked_b)

        # Create non-blocked chunk
        not_blocked = WorkUnit(
            chunk="not_blocked",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            blocked_by=[],
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(not_blocked)

        # Query blocked units
        results = store.list_blocked_by_chunk("blocker_chunk")

        assert len(results) == 2
        chunk_names = [u.chunk for u in results]
        assert "blocked_a" in chunk_names
        assert "blocked_b" in chunk_names
        assert "not_blocked" not in chunk_names
        assert "blocker_chunk" not in chunk_names

    def test_returns_empty_when_no_blocked(self, store):
        """Returns empty list when no units are blocked by the chunk."""
        now = datetime.now(timezone.utc)

        unit = WorkUnit(
            chunk="some_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            blocked_by=[],
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(unit)

        results = store.list_blocked_by_chunk("nonexistent_blocker")

        assert results == []

    def test_returns_empty_for_empty_db(self, store):
        """Returns empty list when database is empty."""
        results = store.list_blocked_by_chunk("any_chunk")

        assert results == []
