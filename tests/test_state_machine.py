"""Tests for StateMachine class."""
# Chunk: docs/chunks/artifact_manager_base - StateMachine tests for transition validation

import pytest

from models import (
    ChunkStatus,
    NarrativeStatus,
    InvestigationStatus,
    SubsystemStatus,
    VALID_CHUNK_TRANSITIONS,
    VALID_NARRATIVE_TRANSITIONS,
    VALID_INVESTIGATION_TRANSITIONS,
    VALID_STATUS_TRANSITIONS,
)
from state_machine import StateMachine


class TestStateMachine:
    """Tests for StateMachine transition validation."""

    def test_valid_chunk_transition_passes(self):
        """Valid chunk transition should not raise."""
        sm = StateMachine(VALID_CHUNK_TRANSITIONS, ChunkStatus)
        # FUTURE -> IMPLEMENTING is valid
        sm.validate_transition(ChunkStatus.FUTURE, ChunkStatus.IMPLEMENTING)

    def test_valid_chunk_transition_future_to_historical(self):
        """FUTURE -> HISTORICAL is valid for skipped chunks."""
        sm = StateMachine(VALID_CHUNK_TRANSITIONS, ChunkStatus)
        sm.validate_transition(ChunkStatus.FUTURE, ChunkStatus.HISTORICAL)

    def test_valid_chunk_transition_implementing_to_active(self):
        """IMPLEMENTING -> ACTIVE is valid for completed chunks."""
        sm = StateMachine(VALID_CHUNK_TRANSITIONS, ChunkStatus)
        sm.validate_transition(ChunkStatus.IMPLEMENTING, ChunkStatus.ACTIVE)

    def test_invalid_chunk_transition_raises(self):
        """Invalid chunk transition should raise ValueError."""
        sm = StateMachine(VALID_CHUNK_TRANSITIONS, ChunkStatus)
        with pytest.raises(ValueError) as exc_info:
            # FUTURE -> ACTIVE is not valid
            sm.validate_transition(ChunkStatus.FUTURE, ChunkStatus.ACTIVE)
        assert "Cannot transition from FUTURE to ACTIVE" in str(exc_info.value)
        assert "Valid transitions:" in str(exc_info.value)
        assert "HISTORICAL" in str(exc_info.value)
        assert "IMPLEMENTING" in str(exc_info.value)

    def test_terminal_state_transition_mentions_terminal(self):
        """Transition from terminal state should mention 'terminal'."""
        sm = StateMachine(VALID_CHUNK_TRANSITIONS, ChunkStatus)
        with pytest.raises(ValueError) as exc_info:
            # HISTORICAL is a terminal state
            sm.validate_transition(ChunkStatus.HISTORICAL, ChunkStatus.ACTIVE)
        assert "terminal state" in str(exc_info.value).lower()

    def test_narrative_valid_transition(self):
        """Valid narrative transition should not raise."""
        sm = StateMachine(VALID_NARRATIVE_TRANSITIONS, NarrativeStatus)
        sm.validate_transition(NarrativeStatus.DRAFTING, NarrativeStatus.ACTIVE)
        sm.validate_transition(NarrativeStatus.ACTIVE, NarrativeStatus.COMPLETED)

    def test_narrative_invalid_transition(self):
        """Invalid narrative transition should raise with correct message."""
        sm = StateMachine(VALID_NARRATIVE_TRANSITIONS, NarrativeStatus)
        with pytest.raises(ValueError) as exc_info:
            # DRAFTING -> COMPLETED is not valid (must go through ACTIVE)
            sm.validate_transition(NarrativeStatus.DRAFTING, NarrativeStatus.COMPLETED)
        assert "Cannot transition from DRAFTING to COMPLETED" in str(exc_info.value)

    def test_narrative_terminal_state(self):
        """Narrative COMPLETED is terminal."""
        sm = StateMachine(VALID_NARRATIVE_TRANSITIONS, NarrativeStatus)
        with pytest.raises(ValueError) as exc_info:
            sm.validate_transition(NarrativeStatus.COMPLETED, NarrativeStatus.ACTIVE)
        assert "terminal state" in str(exc_info.value).lower()

    def test_investigation_valid_transitions(self):
        """Valid investigation transitions should not raise."""
        sm = StateMachine(VALID_INVESTIGATION_TRANSITIONS, InvestigationStatus)
        sm.validate_transition(InvestigationStatus.ONGOING, InvestigationStatus.SOLVED)
        sm.validate_transition(InvestigationStatus.ONGOING, InvestigationStatus.NOTED)
        sm.validate_transition(InvestigationStatus.ONGOING, InvestigationStatus.DEFERRED)
        sm.validate_transition(InvestigationStatus.DEFERRED, InvestigationStatus.ONGOING)

    def test_investigation_terminal_states(self):
        """Investigation SOLVED and NOTED are terminal states."""
        sm = StateMachine(VALID_INVESTIGATION_TRANSITIONS, InvestigationStatus)

        with pytest.raises(ValueError) as exc_info:
            sm.validate_transition(InvestigationStatus.SOLVED, InvestigationStatus.ONGOING)
        assert "terminal state" in str(exc_info.value).lower()

        with pytest.raises(ValueError) as exc_info:
            sm.validate_transition(InvestigationStatus.NOTED, InvestigationStatus.ONGOING)
        assert "terminal state" in str(exc_info.value).lower()

    def test_subsystem_valid_transitions(self):
        """Valid subsystem transitions should not raise."""
        sm = StateMachine(VALID_STATUS_TRANSITIONS, SubsystemStatus)
        sm.validate_transition(SubsystemStatus.DISCOVERING, SubsystemStatus.DOCUMENTED)
        sm.validate_transition(SubsystemStatus.DOCUMENTED, SubsystemStatus.REFACTORING)
        sm.validate_transition(SubsystemStatus.REFACTORING, SubsystemStatus.STABLE)
        sm.validate_transition(SubsystemStatus.STABLE, SubsystemStatus.REFACTORING)

    def test_subsystem_terminal_state(self):
        """Subsystem DEPRECATED is terminal."""
        sm = StateMachine(VALID_STATUS_TRANSITIONS, SubsystemStatus)
        with pytest.raises(ValueError) as exc_info:
            sm.validate_transition(SubsystemStatus.DEPRECATED, SubsystemStatus.STABLE)
        assert "terminal state" in str(exc_info.value).lower()

    def test_error_message_includes_valid_transitions(self):
        """Error message should list valid transitions when they exist."""
        sm = StateMachine(VALID_CHUNK_TRANSITIONS, ChunkStatus)
        with pytest.raises(ValueError) as exc_info:
            sm.validate_transition(ChunkStatus.ACTIVE, ChunkStatus.FUTURE)
        error_msg = str(exc_info.value)
        # ACTIVE can transition to SUPERSEDED or HISTORICAL
        assert "SUPERSEDED" in error_msg or "HISTORICAL" in error_msg
