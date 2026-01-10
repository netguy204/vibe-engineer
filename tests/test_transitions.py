"""Tests for state transition validation across workflow artifacts.

Chunk: docs/chunks/valid_transitions - State transition validation
"""

import pytest

from models import (
    ChunkStatus,
    NarrativeStatus,
    InvestigationStatus,
    VALID_CHUNK_TRANSITIONS,
    VALID_NARRATIVE_TRANSITIONS,
    VALID_INVESTIGATION_TRANSITIONS,
)
from ve import cli


# =============================================================================
# Transition Dict Structure Tests
# =============================================================================


class TestTransitionDictStructure:
    """Verify transition dicts have correct structure."""

    def test_chunk_transitions_has_all_statuses(self):
        """Every ChunkStatus has an entry in VALID_CHUNK_TRANSITIONS."""
        for status in ChunkStatus:
            assert status in VALID_CHUNK_TRANSITIONS, f"Missing entry for {status}"

    def test_narrative_transitions_has_all_statuses(self):
        """Every NarrativeStatus has an entry in VALID_NARRATIVE_TRANSITIONS."""
        for status in NarrativeStatus:
            assert status in VALID_NARRATIVE_TRANSITIONS, f"Missing entry for {status}"

    def test_investigation_transitions_has_all_statuses(self):
        """Every InvestigationStatus has an entry in VALID_INVESTIGATION_TRANSITIONS."""
        for status in InvestigationStatus:
            assert status in VALID_INVESTIGATION_TRANSITIONS, f"Missing entry for {status}"

    def test_chunk_terminal_state_has_empty_set(self):
        """HISTORICAL has no valid transitions (terminal state)."""
        assert VALID_CHUNK_TRANSITIONS[ChunkStatus.HISTORICAL] == set()

    def test_narrative_terminal_state_has_empty_set(self):
        """COMPLETED has no valid transitions (terminal state)."""
        assert VALID_NARRATIVE_TRANSITIONS[NarrativeStatus.COMPLETED] == set()

    def test_investigation_terminal_states_have_empty_set(self):
        """SOLVED and NOTED have no valid transitions (terminal states)."""
        assert VALID_INVESTIGATION_TRANSITIONS[InvestigationStatus.SOLVED] == set()
        assert VALID_INVESTIGATION_TRANSITIONS[InvestigationStatus.NOTED] == set()

    def test_investigation_deferred_can_resume(self):
        """DEFERRED can transition back to ONGOING."""
        assert InvestigationStatus.ONGOING in VALID_INVESTIGATION_TRANSITIONS[InvestigationStatus.DEFERRED]


class TestChunkTransitionValues:
    """Verify chunk transition values are correct."""

    def test_future_transitions(self):
        """FUTURE -> {IMPLEMENTING, HISTORICAL}"""
        expected = {ChunkStatus.IMPLEMENTING, ChunkStatus.HISTORICAL}
        assert VALID_CHUNK_TRANSITIONS[ChunkStatus.FUTURE] == expected

    def test_implementing_transitions(self):
        """IMPLEMENTING -> {ACTIVE, HISTORICAL}"""
        expected = {ChunkStatus.ACTIVE, ChunkStatus.HISTORICAL}
        assert VALID_CHUNK_TRANSITIONS[ChunkStatus.IMPLEMENTING] == expected

    def test_active_transitions(self):
        """ACTIVE -> {SUPERSEDED, HISTORICAL}"""
        expected = {ChunkStatus.SUPERSEDED, ChunkStatus.HISTORICAL}
        assert VALID_CHUNK_TRANSITIONS[ChunkStatus.ACTIVE] == expected

    def test_superseded_transitions(self):
        """SUPERSEDED -> {HISTORICAL}"""
        expected = {ChunkStatus.HISTORICAL}
        assert VALID_CHUNK_TRANSITIONS[ChunkStatus.SUPERSEDED] == expected


class TestNarrativeTransitionValues:
    """Verify narrative transition values are correct."""

    def test_drafting_transitions(self):
        """DRAFTING -> {ACTIVE}"""
        expected = {NarrativeStatus.ACTIVE}
        assert VALID_NARRATIVE_TRANSITIONS[NarrativeStatus.DRAFTING] == expected

    def test_active_transitions(self):
        """ACTIVE -> {COMPLETED}"""
        expected = {NarrativeStatus.COMPLETED}
        assert VALID_NARRATIVE_TRANSITIONS[NarrativeStatus.ACTIVE] == expected


class TestInvestigationTransitionValues:
    """Verify investigation transition values are correct."""

    def test_ongoing_transitions(self):
        """ONGOING -> {SOLVED, NOTED, DEFERRED}"""
        expected = {InvestigationStatus.SOLVED, InvestigationStatus.NOTED, InvestigationStatus.DEFERRED}
        assert VALID_INVESTIGATION_TRANSITIONS[InvestigationStatus.ONGOING] == expected

    def test_deferred_transitions(self):
        """DEFERRED -> {ONGOING}"""
        expected = {InvestigationStatus.ONGOING}
        assert VALID_INVESTIGATION_TRANSITIONS[InvestigationStatus.DEFERRED] == expected


# =============================================================================
# Chunk Status CLI Tests
# =============================================================================


class TestChunkStatusDisplay:
    """Tests for 've chunk status <id>' (display mode)."""

    def test_status_display_shows_current_status(self, runner, temp_project):
        """Show current status for an existing chunk."""
        runner.invoke(
            cli,
            ["chunk", "start", "validation", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "status", "validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "validation: IMPLEMENTING" in result.output


class TestChunkStatusTransitions:
    """Tests for valid and invalid chunk status transitions."""

    def test_valid_transition_implementing_to_active(self, runner, temp_project):
        """IMPLEMENTING -> ACTIVE works."""
        runner.invoke(
            cli,
            ["chunk", "start", "validation", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "status", "validation", "ACTIVE", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "validation: IMPLEMENTING" in result.output
        assert "ACTIVE" in result.output

    def test_valid_transition_future_to_implementing(self, runner, temp_project):
        """FUTURE -> IMPLEMENTING works."""
        runner.invoke(
            cli,
            ["chunk", "start", "validation", "--future", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "status", "validation", "IMPLEMENTING", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "validation: FUTURE" in result.output
        assert "IMPLEMENTING" in result.output

    def test_valid_transition_active_to_superseded(self, runner, temp_project):
        """ACTIVE -> SUPERSEDED works."""
        runner.invoke(
            cli,
            ["chunk", "start", "validation", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "status", "validation", "ACTIVE", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "status", "validation", "SUPERSEDED", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "ACTIVE" in result.output
        assert "SUPERSEDED" in result.output

    def test_invalid_transition_implementing_to_superseded(self, runner, temp_project):
        """Cannot skip steps: IMPLEMENTING -> SUPERSEDED fails."""
        runner.invoke(
            cli,
            ["chunk", "start", "validation", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "status", "validation", "SUPERSEDED", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Cannot transition from IMPLEMENTING to SUPERSEDED" in result.output
        assert "Valid transitions:" in result.output

    def test_invalid_transition_historical_to_any(self, runner, temp_project):
        """Terminal state enforced: HISTORICAL -> any fails."""
        runner.invoke(
            cli,
            ["chunk", "start", "validation", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "status", "validation", "HISTORICAL", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "status", "validation", "ACTIVE", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Cannot transition from HISTORICAL" in result.output
        assert "terminal state" in result.output


class TestChunkStatusErrors:
    """Tests for chunk status error handling."""

    def test_chunk_not_found_error(self, runner, temp_project):
        """Clear error message when chunk doesn't exist."""
        result = runner.invoke(
            cli,
            ["chunk", "status", "nonexistent", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Chunk 'nonexistent' not found" in result.output

    def test_invalid_status_value_error(self, runner, temp_project):
        """Lists valid statuses when invalid status provided."""
        runner.invoke(
            cli,
            ["chunk", "start", "validation", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "status", "validation", "FOO", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Invalid status 'FOO'" in result.output
        assert "IMPLEMENTING" in result.output
        assert "ACTIVE" in result.output


# =============================================================================
# Narrative Status CLI Tests
# =============================================================================


class TestNarrativeStatusDisplay:
    """Tests for 've narrative status <id>' (display mode)."""

    def test_status_display_shows_current_status(self, runner, temp_project):
        """Show current status for an existing narrative."""
        runner.invoke(
            cli,
            ["narrative", "create", "migration", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["narrative", "status", "migration", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "migration: DRAFTING" in result.output


class TestNarrativeStatusTransitions:
    """Tests for valid and invalid narrative status transitions."""

    def test_valid_transition_drafting_to_active(self, runner, temp_project):
        """DRAFTING -> ACTIVE works."""
        runner.invoke(
            cli,
            ["narrative", "create", "migration", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["narrative", "status", "migration", "ACTIVE", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "migration: DRAFTING" in result.output
        assert "ACTIVE" in result.output

    def test_valid_transition_active_to_completed(self, runner, temp_project):
        """ACTIVE -> COMPLETED works."""
        runner.invoke(
            cli,
            ["narrative", "create", "migration", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["narrative", "status", "migration", "ACTIVE", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["narrative", "status", "migration", "COMPLETED", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "ACTIVE" in result.output
        assert "COMPLETED" in result.output

    def test_invalid_transition_drafting_to_completed(self, runner, temp_project):
        """Cannot skip steps: DRAFTING -> COMPLETED fails."""
        runner.invoke(
            cli,
            ["narrative", "create", "migration", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["narrative", "status", "migration", "COMPLETED", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Cannot transition from DRAFTING to COMPLETED" in result.output
        assert "Valid transitions:" in result.output

    def test_invalid_transition_completed_to_any(self, runner, temp_project):
        """Terminal state enforced: COMPLETED -> any fails."""
        runner.invoke(
            cli,
            ["narrative", "create", "migration", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["narrative", "status", "migration", "ACTIVE", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["narrative", "status", "migration", "COMPLETED", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["narrative", "status", "migration", "DRAFTING", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Cannot transition from COMPLETED" in result.output
        assert "terminal state" in result.output


class TestNarrativeStatusErrors:
    """Tests for narrative status error handling."""

    def test_narrative_not_found_error(self, runner, temp_project):
        """Clear error message when narrative doesn't exist."""
        result = runner.invoke(
            cli,
            ["narrative", "status", "nonexistent", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Narrative 'nonexistent' not found" in result.output

    def test_invalid_status_value_error(self, runner, temp_project):
        """Lists valid statuses when invalid status provided."""
        runner.invoke(
            cli,
            ["narrative", "create", "migration", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["narrative", "status", "migration", "FOO", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Invalid status 'FOO'" in result.output
        assert "DRAFTING" in result.output
        assert "ACTIVE" in result.output


# =============================================================================
# Investigation Status CLI Tests
# =============================================================================


class TestInvestigationStatusDisplay:
    """Tests for 've investigation status <id>' (display mode)."""

    def test_status_display_shows_current_status(self, runner, temp_project):
        """Show current status for an existing investigation."""
        runner.invoke(
            cli,
            ["investigation", "create", "memory_leak", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["investigation", "status", "memory_leak", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "memory_leak: ONGOING" in result.output


class TestInvestigationStatusTransitions:
    """Tests for valid and invalid investigation status transitions."""

    def test_valid_transition_ongoing_to_solved(self, runner, temp_project):
        """ONGOING -> SOLVED works."""
        runner.invoke(
            cli,
            ["investigation", "create", "memory_leak", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["investigation", "status", "memory_leak", "SOLVED", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "memory_leak: ONGOING" in result.output
        assert "SOLVED" in result.output

    def test_valid_transition_ongoing_to_noted(self, runner, temp_project):
        """ONGOING -> NOTED works."""
        runner.invoke(
            cli,
            ["investigation", "create", "memory_leak", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["investigation", "status", "memory_leak", "NOTED", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "ONGOING" in result.output
        assert "NOTED" in result.output

    def test_valid_transition_ongoing_to_deferred(self, runner, temp_project):
        """ONGOING -> DEFERRED works."""
        runner.invoke(
            cli,
            ["investigation", "create", "memory_leak", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["investigation", "status", "memory_leak", "DEFERRED", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "ONGOING" in result.output
        assert "DEFERRED" in result.output

    def test_valid_transition_deferred_to_ongoing(self, runner, temp_project):
        """DEFERRED -> ONGOING (resume) works."""
        runner.invoke(
            cli,
            ["investigation", "create", "memory_leak", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["investigation", "status", "memory_leak", "DEFERRED", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["investigation", "status", "memory_leak", "ONGOING", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "DEFERRED" in result.output
        assert "ONGOING" in result.output

    def test_invalid_transition_solved_to_any(self, runner, temp_project):
        """Terminal state enforced: SOLVED -> any fails."""
        runner.invoke(
            cli,
            ["investigation", "create", "memory_leak", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["investigation", "status", "memory_leak", "SOLVED", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["investigation", "status", "memory_leak", "ONGOING", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Cannot transition from SOLVED" in result.output
        assert "terminal state" in result.output

    def test_invalid_transition_noted_to_any(self, runner, temp_project):
        """Terminal state enforced: NOTED -> any fails."""
        runner.invoke(
            cli,
            ["investigation", "create", "memory_leak", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["investigation", "status", "memory_leak", "NOTED", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["investigation", "status", "memory_leak", "ONGOING", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Cannot transition from NOTED" in result.output
        assert "terminal state" in result.output

    def test_invalid_transition_deferred_to_solved(self, runner, temp_project):
        """DEFERRED -> SOLVED fails (must resume first)."""
        runner.invoke(
            cli,
            ["investigation", "create", "memory_leak", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["investigation", "status", "memory_leak", "DEFERRED", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["investigation", "status", "memory_leak", "SOLVED", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Cannot transition from DEFERRED to SOLVED" in result.output
        assert "Valid transitions:" in result.output


class TestInvestigationStatusErrors:
    """Tests for investigation status error handling."""

    def test_investigation_not_found_error(self, runner, temp_project):
        """Clear error message when investigation doesn't exist."""
        result = runner.invoke(
            cli,
            ["investigation", "status", "nonexistent", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Investigation 'nonexistent' not found" in result.output

    def test_invalid_status_value_error(self, runner, temp_project):
        """Lists valid statuses when invalid status provided."""
        runner.invoke(
            cli,
            ["investigation", "create", "memory_leak", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["investigation", "status", "memory_leak", "FOO", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Invalid status 'FOO'" in result.output
        assert "ONGOING" in result.output
        assert "SOLVED" in result.output
