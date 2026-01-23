"""Tests for narrative compact and update-refs commands.

# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle

Note: Basic narrative create/list/status tests are in test_narrative_create.py,
test_narrative_list.py, and test_transitions.py.
"""

import pytest

from ve import cli
from narratives import Narratives
from chunks import Chunks


class TestNarrativeCompact:
    """Tests for 've narrative compact' with in-repo storage."""

    def test_compact_creates_narrative(self, runner, temp_project):
        """ve narrative compact creates a narrative from multiple chunks."""
        # Create and complete two chunks
        runner.invoke(
            cli,
            ["chunk", "create", "chunk1", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "create", "chunk2", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["narrative", "compact", "chunk1", "chunk2", "--name", "combined", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert "Created narrative" in result.output
        assert "docs/narratives/combined" in result.output

    def test_compact_lists_consolidated_chunks(self, runner, temp_project):
        """Compact output lists the consolidated chunks."""
        # Create and complete two chunks
        runner.invoke(
            cli,
            ["chunk", "create", "chunk1", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "create", "chunk2", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["narrative", "compact", "chunk1", "chunk2", "--name", "combined", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert "chunk1" in result.output
        assert "chunk2" in result.output


class TestNarrativeUpdateRefs:
    """Tests for 've narrative update-refs' with in-repo storage."""

    def test_update_refs_no_chunks(self, runner, temp_project):
        """update-refs with no consolidated chunks does nothing."""
        runner.invoke(
            cli,
            ["narrative", "create", "my_narrative", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["narrative", "update-refs", "my_narrative", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert "no consolidated chunks" in result.output.lower()
