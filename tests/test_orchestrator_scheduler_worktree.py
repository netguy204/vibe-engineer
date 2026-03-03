# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/test_file_split - Split large scheduler test file
# Chunk: docs/chunks/deferred_worktree_creation - Tests verifying worktree creation at dispatch time
"""Tests for deferred worktree creation in the orchestrator scheduler.

These tests verify that worktrees are created at dispatch time (when
_run_work_unit is called), not at inject time.
"""

import pytest
from datetime import datetime, timezone

from orchestrator.models import (
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)

# Fixtures come from conftest.py:
# - state_store
# - mock_worktree_manager
# - mock_agent_runner
# - orchestrator_config
# - scheduler


class TestDeferredWorktreeCreation:
    """Tests for deferred worktree creation.

    These tests verify that worktrees are created at dispatch time (when
    _run_work_unit is called), not at inject time. This ensures:
    1. Injected work units don't consume resources until they run
    2. Blocked work sees the current repository state when it starts
    3. Worktrees reflect HEAD at dispatch time, not inject time
    """

    def test_inject_does_not_create_worktree(
        self, state_store, mock_worktree_manager, tmp_path
    ):
        """Inject creates a work unit but does NOT create a worktree.

        This verifies the deferred worktree creation behavior: when work is
        injected via the API, only a WorkUnit record is created. The worktree
        is NOT created until the scheduler dispatches the work.
        """
        # Create work unit directly (simulating inject behavior)
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Verify work unit exists
        stored = state_store.get_work_unit("test_chunk")
        assert stored is not None
        assert stored.status == WorkUnitStatus.READY

        # Verify worktree does NOT exist (worktree field is None on the work unit)
        assert stored.worktree is None

        # Also verify worktree_manager.create_worktree was NOT called
        mock_worktree_manager.create_worktree.assert_not_called()

    @pytest.mark.asyncio
    async def test_worktree_created_at_dispatch_time(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """Worktree is created when _run_work_unit is called (dispatch time).

        This verifies that the scheduler creates the worktree at the beginning
        of _run_work_unit, transitioning the work unit from READY to RUNNING.
        """
        # Set up chunk for activation
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text(
            """---
status: FUTURE
ticket: null
---

# Chunk Goal
"""
        )

        # Configure mock
        mock_worktree_manager.create_worktree.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        # Create READY work unit
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Verify worktree_manager.create_worktree NOT called yet
        mock_worktree_manager.create_worktree.assert_not_called()

        # Run the work unit (this is what the scheduler does when dispatching)
        await scheduler._run_work_unit(work_unit)

        # NOW worktree should have been created
        mock_worktree_manager.create_worktree.assert_called_once_with("test_chunk")

        # Work unit should be RUNNING with worktree path set
        updated = state_store.get_work_unit("test_chunk")
        assert updated.worktree == str(tmp_path)

    @pytest.mark.asyncio
    async def test_ready_work_unit_has_no_worktree_until_dispatched(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Work units in READY status waiting for slots do not have worktrees.

        This test verifies that work units can sit in the READY queue without
        consuming worktree resources.
        """
        # Create multiple READY work units
        now = datetime.now(timezone.utc)
        for i in range(5):
            work_unit = WorkUnit(
                chunk=f"chunk_{i}",
                phase=WorkUnitPhase.PLAN,
                status=WorkUnitStatus.READY,
                created_at=now,
                updated_at=now,
            )
            state_store.create_work_unit(work_unit)

        # Verify all work units exist and are READY
        for i in range(5):
            unit = state_store.get_work_unit(f"chunk_{i}")
            assert unit is not None
            assert unit.status == WorkUnitStatus.READY
            # No worktree assigned yet
            assert unit.worktree is None

        # No worktrees should have been created
        mock_worktree_manager.create_worktree.assert_not_called()


class TestBlockedWorkDeferredWorktree:
    """Tests for blocked work units and deferred worktree creation.

    When work has dependencies (blocked_by list), it should not get a worktree
    until:
    1. Dependencies complete
    2. The work unit transitions to READY
    3. The scheduler dispatches it (READY -> RUNNING)

    This ensures blocked work sees the repository state AFTER its dependencies
    have been merged.
    """

    def test_blocked_work_unit_has_no_worktree(
        self, state_store, mock_worktree_manager
    ):
        """BLOCKED work units do not have worktrees.

        Work blocked on dependencies should not consume worktree resources
        until those dependencies complete.
        """
        now = datetime.now(timezone.utc)

        # Create chunk_a as READY (the dependency)
        chunk_a = WorkUnit(
            chunk="chunk_a",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(chunk_a)

        # Create chunk_b as BLOCKED (depends on chunk_a)
        chunk_b = WorkUnit(
            chunk="chunk_b",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.BLOCKED,
            blocked_by=["chunk_a"],
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(chunk_b)

        # Verify chunk_b is BLOCKED
        stored = state_store.get_work_unit("chunk_b")
        assert stored.status == WorkUnitStatus.BLOCKED
        assert stored.blocked_by == ["chunk_a"]

        # BLOCKED work unit should have no worktree
        assert stored.worktree is None

        # No worktrees created for blocked work
        mock_worktree_manager.create_worktree.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocked_work_gets_worktree_only_when_running(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """Blocked work gets worktree only when it starts running.

        This tests the full flow:
        1. Work is BLOCKED (no worktree)
        2. Dependencies complete (still no worktree - work is now READY)
        3. Scheduler dispatches the work (NOW worktree is created)
        """
        # Set up chunk for activation
        chunk_dir = tmp_path / "docs" / "chunks" / "chunk_b"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text(
            """---
status: FUTURE
ticket: null
---

# Chunk Goal
"""
        )

        mock_worktree_manager.create_worktree.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)

        # Create work unit that was previously BLOCKED, now READY
        # (simulating after dependency completion)
        chunk_b = WorkUnit(
            chunk="chunk_b",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            blocked_by=["chunk_a"],  # Still has blocked_by info for traceability
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(chunk_b)

        # Verify no worktree yet (work is READY, not RUNNING)
        stored = state_store.get_work_unit("chunk_b")
        assert stored.worktree is None
        mock_worktree_manager.create_worktree.assert_not_called()

        # Now dispatch the work (scheduler runs it)
        await scheduler._run_work_unit(chunk_b)

        # Worktree should now be created
        mock_worktree_manager.create_worktree.assert_called_once_with("chunk_b")

        # Work unit should have worktree assigned
        updated = state_store.get_work_unit("chunk_b")
        assert updated.worktree == str(tmp_path)

    def test_blocked_to_ready_transition_no_worktree(
        self, state_store, mock_worktree_manager
    ):
        """Transitioning BLOCKED -> READY does not create worktree.

        When dependencies complete and work moves to READY, it should still
        NOT have a worktree. The worktree is only created at dispatch time.
        """
        now = datetime.now(timezone.utc)

        # Create BLOCKED work unit
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.BLOCKED,
            blocked_by=["dependency_chunk"],
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Verify BLOCKED state
        stored = state_store.get_work_unit("test_chunk")
        assert stored.status == WorkUnitStatus.BLOCKED
        assert stored.worktree is None

        # Simulate dependency completion - transition to READY
        stored.status = WorkUnitStatus.READY
        stored.blocked_by = []  # Clear blocking dependencies
        stored.updated_at = datetime.now(timezone.utc)
        state_store.update_work_unit(stored)

        # Work unit is now READY but still NO worktree
        updated = state_store.get_work_unit("test_chunk")
        assert updated.status == WorkUnitStatus.READY
        assert updated.worktree is None

        # worktree_manager.create_worktree should NOT have been called
        mock_worktree_manager.create_worktree.assert_not_called()


class TestDeferredWorktreeCreationIntegration:
    """Integration tests for deferred worktree creation with real git repos.

    These tests verify the full behavior using actual git worktrees, ensuring
    that the worktree reflects the repository state at dispatch time.
    """

    @pytest.fixture
    def git_repo(self, tmp_path):
        """Create a git repository for testing."""
        import subprocess

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Create initial commit so HEAD exists
        (tmp_path / "README.md").write_text("# Test\n")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        return tmp_path

    def test_worktree_reflects_current_head_at_dispatch_time(self, git_repo):
        """Worktree is created from current HEAD at dispatch time.

        This verifies that if commits are made after work is injected but before
        it runs, the worktree sees those commits.
        """
        import subprocess
        from orchestrator.worktree import WorktreeManager

        manager = WorktreeManager(git_repo)

        # Simulate: work is "injected" - at this point HEAD is at initial commit
        # We just note that no worktree exists yet
        assert not manager.worktree_exists("test_chunk")

        # Simulate: other work happens and commits are made
        (git_repo / "new_file.txt").write_text("new content after inject")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add new file after inject"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Now simulate: work is dispatched - worktree is created NOW
        worktree_path = manager.create_worktree("test_chunk")

        # The worktree should have the new file (HEAD at dispatch time)
        assert (worktree_path / "new_file.txt").exists()
        assert (worktree_path / "new_file.txt").read_text() == "new content after inject"

        # Clean up
        manager.remove_worktree("test_chunk", remove_branch=True)

    def test_blocked_work_sees_dependency_changes_when_dispatched(self, git_repo):
        """Blocked work sees changes from completed dependencies.

        This is the key scenario: chunk_b depends on chunk_a. When chunk_a
        completes and merges, and chunk_b is later dispatched, chunk_b's
        worktree should contain chunk_a's changes.
        """
        import subprocess
        from orchestrator.worktree import WorktreeManager

        manager = WorktreeManager(git_repo)

        # Simulate chunk_a completing: create its worktree, make changes, merge
        chunk_a_worktree = manager.create_worktree("chunk_a")

        # chunk_a makes changes
        (chunk_a_worktree / "chunk_a_file.txt").write_text("content from chunk_a")
        subprocess.run(
            ["git", "add", "."], cwd=chunk_a_worktree, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "chunk_a implementation"],
            cwd=chunk_a_worktree,
            check=True,
            capture_output=True,
        )

        # chunk_a completes - worktree is removed and branch is merged
        manager.remove_worktree("chunk_a", remove_branch=False)
        manager.merge_to_base("chunk_a", delete_branch=True)

        # Verify chunk_a's changes are now on the base branch
        assert (git_repo / "chunk_a_file.txt").exists()

        # Now chunk_b (which was blocked on chunk_a) is dispatched
        # Its worktree is created NOW, from current HEAD
        chunk_b_worktree = manager.create_worktree("chunk_b")

        # chunk_b's worktree should see chunk_a's file
        assert (chunk_b_worktree / "chunk_a_file.txt").exists()
        assert (
            (chunk_b_worktree / "chunk_a_file.txt").read_text()
            == "content from chunk_a"
        )

        # Clean up
        manager.remove_worktree("chunk_b", remove_branch=True)
