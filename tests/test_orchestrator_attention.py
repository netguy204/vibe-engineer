# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_attention_queue - Attention queue tests
"""Tests for the orchestrator attention queue functionality."""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from orchestrator.models import WorkUnit, WorkUnitPhase, WorkUnitStatus
from orchestrator.state import StateStore


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


class TestGetAttentionQueue:
    """Tests for StateStore.get_attention_queue()."""

    def test_empty_queue_returns_empty_list(self, store):
        """Empty attention queue returns empty list."""
        result = store.get_attention_queue()
        assert result == []

    def test_excludes_non_needs_attention(self, store):
        """Only NEEDS_ATTENTION work units are included."""
        now = datetime.now(timezone.utc)

        # Create work units with various statuses
        for i, status in enumerate([
            WorkUnitStatus.READY,
            WorkUnitStatus.RUNNING,
            WorkUnitStatus.BLOCKED,
            WorkUnitStatus.DONE,
        ]):
            unit = WorkUnit(
                chunk=f"chunk_{i}",
                phase=WorkUnitPhase.PLAN,
                status=status,
                created_at=now + timedelta(seconds=i),
                updated_at=now + timedelta(seconds=i),
            )
            store.create_work_unit(unit)

        result = store.get_attention_queue()
        assert result == []

    def test_returns_needs_attention_units(self, store):
        """NEEDS_ATTENTION work units are included."""
        now = datetime.now(timezone.utc)

        unit = WorkUnit(
            chunk="attention_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.NEEDS_ATTENTION,
            attention_reason="Agent asked a question",
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(unit)

        result = store.get_attention_queue()

        assert len(result) == 1
        work_unit, blocks_count = result[0]
        assert work_unit.chunk == "attention_chunk"
        assert work_unit.attention_reason == "Agent asked a question"
        assert blocks_count == 0

    def test_orders_by_blocks_count_descending(self, store):
        """Higher blocked count items appear first."""
        now = datetime.now(timezone.utc)

        # Create attention units
        for i, chunk_name in enumerate(["low_blocks", "high_blocks"]):
            unit = WorkUnit(
                chunk=chunk_name,
                phase=WorkUnitPhase.PLAN,
                status=WorkUnitStatus.NEEDS_ATTENTION,
                attention_reason=f"Attention needed for {chunk_name}",
                created_at=now + timedelta(seconds=i),
                updated_at=now + timedelta(seconds=i),
            )
            store.create_work_unit(unit)

        # Create work units that are blocked by high_blocks
        for i in range(3):
            blocked_unit = WorkUnit(
                chunk=f"blocked_{i}",
                phase=WorkUnitPhase.IMPLEMENT,
                status=WorkUnitStatus.BLOCKED,
                blocked_by=["high_blocks"],
                created_at=now + timedelta(seconds=10 + i),
                updated_at=now + timedelta(seconds=10 + i),
            )
            store.create_work_unit(blocked_unit)

        result = store.get_attention_queue()

        assert len(result) == 2
        # high_blocks should come first (blocks 3 units)
        assert result[0][0].chunk == "high_blocks"
        assert result[0][1] == 3
        # low_blocks should come second (blocks 0 units)
        assert result[1][0].chunk == "low_blocks"
        assert result[1][1] == 0

    def test_orders_by_time_when_equal_blocks(self, store):
        """Older items first among equal blocked counts."""
        now = datetime.now(timezone.utc)

        # Create attention units with different update times but same blocks count
        old_unit = WorkUnit(
            chunk="older_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.NEEDS_ATTENTION,
            attention_reason="Older question",
            created_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=2),
        )
        store.create_work_unit(old_unit)

        new_unit = WorkUnit(
            chunk="newer_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.NEEDS_ATTENTION,
            attention_reason="Newer question",
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(new_unit)

        result = store.get_attention_queue()

        assert len(result) == 2
        # Older item should come first (both have 0 blocks)
        assert result[0][0].chunk == "older_chunk"
        assert result[1][0].chunk == "newer_chunk"


class TestPendingAnswerPersistence:
    """Tests for pending_answer field persistence."""

    def test_stores_pending_answer_on_create(self, store):
        """pending_answer is stored on create."""
        now = datetime.now(timezone.utc)
        unit = WorkUnit(
            chunk="answer_test",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            pending_answer="Use JWT for authentication",
            created_at=now,
            updated_at=now,
        )

        store.create_work_unit(unit)
        retrieved = store.get_work_unit("answer_test")

        assert retrieved.pending_answer == "Use JWT for authentication"

    def test_updates_pending_answer(self, store):
        """pending_answer can be updated."""
        now = datetime.now(timezone.utc)
        unit = WorkUnit(
            chunk="answer_test",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.NEEDS_ATTENTION,
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(unit)

        # Update with pending_answer
        unit.pending_answer = "Use Redis for caching"
        unit.status = WorkUnitStatus.READY
        unit.updated_at = datetime.now(timezone.utc)
        store.update_work_unit(unit)

        retrieved = store.get_work_unit("answer_test")
        assert retrieved.pending_answer == "Use Redis for caching"

    def test_pending_answer_null_by_default(self, store):
        """pending_answer is None by default."""
        now = datetime.now(timezone.utc)
        unit = WorkUnit(
            chunk="no_answer",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(unit)

        retrieved = store.get_work_unit("no_answer")
        assert retrieved.pending_answer is None

    def test_clears_pending_answer(self, store):
        """pending_answer can be cleared (set to None)."""
        now = datetime.now(timezone.utc)
        unit = WorkUnit(
            chunk="clear_answer",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            pending_answer="Some answer",
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(unit)

        # Clear the pending_answer
        unit.pending_answer = None
        unit.updated_at = datetime.now(timezone.utc)
        store.update_work_unit(unit)

        retrieved = store.get_work_unit("clear_answer")
        assert retrieved.pending_answer is None

    def test_pending_answer_preserved_in_list(self, store):
        """pending_answer is included when listing work units."""
        now = datetime.now(timezone.utc)
        unit = WorkUnit(
            chunk="answer_list_test",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            pending_answer="Listed answer",
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(unit)

        units = store.list_work_units()

        assert len(units) == 1
        assert units[0].pending_answer == "Listed answer"
