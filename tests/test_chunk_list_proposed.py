"""Tests for ve chunk list-proposed command."""
# Chunk: docs/chunks/0032-proposed_chunks_frontmatter - Tests for list-proposed

import pathlib

import pytest
from click.testing import CliRunner

from ve import cli
from chunks import Chunks
from investigations import Investigations
from narratives import Narratives
from subsystems import Subsystems


class TestListProposedChunksLogic:
    """Tests for the list_proposed_chunks business logic."""

    def test_empty_project_returns_empty_list(self, temp_project):
        """Verify empty project has no proposed chunks."""
        chunks = Chunks(temp_project)
        investigations = Investigations(temp_project)
        narratives = Narratives(temp_project)
        subsystems = Subsystems(temp_project)

        result = chunks.list_proposed_chunks(investigations, narratives, subsystems)
        assert result == []

    def test_investigation_with_proposed_chunks(self, temp_project):
        """Verify investigation proposed chunks are included."""
        # Create investigation directory with proposed chunks
        inv_dir = temp_project / "docs" / "investigations" / "0001-test_inv"
        inv_dir.mkdir(parents=True)

        overview = inv_dir / "OVERVIEW.md"
        overview.write_text("""---
status: ONGOING
trigger: "Test trigger"
proposed_chunks:
  - prompt: "First proposed chunk"
    chunk_directory: null
  - prompt: "Second proposed chunk"
    chunk_directory: "0005-already_created"
---
# Test Investigation
""")

        chunks = Chunks(temp_project)
        investigations = Investigations(temp_project)
        narratives = Narratives(temp_project)
        subsystems = Subsystems(temp_project)

        result = chunks.list_proposed_chunks(investigations, narratives, subsystems)

        # Should only include the one without chunk_directory
        assert len(result) == 1
        assert result[0]["prompt"] == "First proposed chunk"
        assert result[0]["source_type"] == "investigation"
        assert result[0]["source_id"] == "0001-test_inv"

    def test_narrative_with_proposed_chunks(self, temp_project):
        """Verify narrative proposed_chunks are included."""
        # Create narrative directory with proposed_chunks
        narr_dir = temp_project / "docs" / "narratives" / "0001-test_narr"
        narr_dir.mkdir(parents=True)

        overview = narr_dir / "OVERVIEW.md"
        overview.write_text("""---
status: DRAFTING
advances_trunk_goal: null
proposed_chunks:
  - prompt: "Narrative chunk prompt"
    chunk_directory: null
---
# Test Narrative
""")

        chunks = Chunks(temp_project)
        investigations = Investigations(temp_project)
        narratives = Narratives(temp_project)
        subsystems = Subsystems(temp_project)

        result = chunks.list_proposed_chunks(investigations, narratives, subsystems)

        assert len(result) == 1
        assert result[0]["prompt"] == "Narrative chunk prompt"
        assert result[0]["source_type"] == "narrative"
        assert result[0]["source_id"] == "0001-test_narr"

    def test_narrative_with_legacy_chunks_field(self, temp_project):
        """Verify legacy 'chunks' field in narratives is handled."""
        # Create narrative directory with legacy 'chunks' field
        narr_dir = temp_project / "docs" / "narratives" / "0001-legacy_narr"
        narr_dir.mkdir(parents=True)

        overview = narr_dir / "OVERVIEW.md"
        overview.write_text("""---
status: ACTIVE
advances_trunk_goal: null
chunks:
  - prompt: "Legacy chunk prompt"
    chunk_directory: null
---
# Legacy Narrative
""")

        chunks = Chunks(temp_project)
        investigations = Investigations(temp_project)
        narratives = Narratives(temp_project)
        subsystems = Subsystems(temp_project)

        result = chunks.list_proposed_chunks(investigations, narratives, subsystems)

        # Should map legacy 'chunks' to 'proposed_chunks'
        assert len(result) == 1
        assert result[0]["prompt"] == "Legacy chunk prompt"
        assert result[0]["source_type"] == "narrative"

    def test_subsystem_with_proposed_chunks(self, temp_project):
        """Verify subsystem proposed_chunks are included."""
        # Create subsystem directory with proposed_chunks
        sub_dir = temp_project / "docs" / "subsystems" / "0001-test_sub"
        sub_dir.mkdir(parents=True)

        overview = sub_dir / "OVERVIEW.md"
        overview.write_text("""---
status: DOCUMENTED
chunks: []
code_references: []
proposed_chunks:
  - prompt: "Consolidation chunk prompt"
    chunk_directory: null
---
# test_sub
""")

        chunks = Chunks(temp_project)
        investigations = Investigations(temp_project)
        narratives = Narratives(temp_project)
        subsystems = Subsystems(temp_project)

        result = chunks.list_proposed_chunks(investigations, narratives, subsystems)

        assert len(result) == 1
        assert result[0]["prompt"] == "Consolidation chunk prompt"
        assert result[0]["source_type"] == "subsystem"
        assert result[0]["source_id"] == "0001-test_sub"

    def test_created_chunks_filtered_out(self, temp_project):
        """Verify chunks with chunk_directory set are filtered out."""
        # Create narrative with a created chunk
        narr_dir = temp_project / "docs" / "narratives" / "0001-test_narr"
        narr_dir.mkdir(parents=True)

        overview = narr_dir / "OVERVIEW.md"
        overview.write_text("""---
status: ACTIVE
advances_trunk_goal: null
proposed_chunks:
  - prompt: "Already created"
    chunk_directory: "0010-already_created"
---
# Test Narrative
""")

        chunks = Chunks(temp_project)
        investigations = Investigations(temp_project)
        narratives = Narratives(temp_project)
        subsystems = Subsystems(temp_project)

        result = chunks.list_proposed_chunks(investigations, narratives, subsystems)

        # Should be empty since the only proposed chunk has been created
        assert result == []

    def test_multiple_sources_aggregated(self, temp_project):
        """Verify proposed chunks from multiple sources are aggregated."""
        # Create investigation
        inv_dir = temp_project / "docs" / "investigations" / "0001-inv"
        inv_dir.mkdir(parents=True)
        (inv_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
trigger: null
proposed_chunks:
  - prompt: "From investigation"
    chunk_directory: null
---
""")

        # Create narrative
        narr_dir = temp_project / "docs" / "narratives" / "0001-narr"
        narr_dir.mkdir(parents=True)
        (narr_dir / "OVERVIEW.md").write_text("""---
status: DRAFTING
advances_trunk_goal: null
proposed_chunks:
  - prompt: "From narrative"
    chunk_directory: null
---
""")

        # Create subsystem
        sub_dir = temp_project / "docs" / "subsystems" / "0001-sub"
        sub_dir.mkdir(parents=True)
        (sub_dir / "OVERVIEW.md").write_text("""---
status: DISCOVERING
chunks: []
code_references: []
proposed_chunks:
  - prompt: "From subsystem"
    chunk_directory: null
---
""")

        chunks = Chunks(temp_project)
        investigations = Investigations(temp_project)
        narratives = Narratives(temp_project)
        subsystems = Subsystems(temp_project)

        result = chunks.list_proposed_chunks(investigations, narratives, subsystems)

        assert len(result) == 3
        prompts = {r["prompt"] for r in result}
        assert prompts == {"From investigation", "From narrative", "From subsystem"}


class TestListProposedChunksCLI:
    """Tests for the ve chunk list-proposed CLI command."""

    def test_empty_project_outputs_message(self, temp_project, runner):
        """Verify empty project outputs appropriate message."""
        result = runner.invoke(cli, ["chunk", "list-proposed", "--project-dir", str(temp_project)])

        assert result.exit_code == 0
        assert "No proposed chunks found" in result.output

    def test_shows_grouped_output(self, temp_project, runner):
        """Verify output is grouped by source."""
        # Create narrative with proposed chunk
        narr_dir = temp_project / "docs" / "narratives" / "0001-test_narr"
        narr_dir.mkdir(parents=True)
        (narr_dir / "OVERVIEW.md").write_text("""---
status: DRAFTING
advances_trunk_goal: null
proposed_chunks:
  - prompt: "Test chunk prompt"
    chunk_directory: null
---
""")

        result = runner.invoke(cli, ["chunk", "list-proposed", "--project-dir", str(temp_project)])

        assert result.exit_code == 0
        assert "From docs/narratives/0001-test_narr:" in result.output
        assert "Test chunk prompt" in result.output

    def test_long_prompts_truncated(self, temp_project, runner):
        """Verify long prompts are truncated in output."""
        # Create narrative with very long prompt
        narr_dir = temp_project / "docs" / "narratives" / "0001-test_narr"
        narr_dir.mkdir(parents=True)

        long_prompt = "This is a very long prompt " * 10  # ~270 chars
        (narr_dir / "OVERVIEW.md").write_text(f"""---
status: DRAFTING
advances_trunk_goal: null
proposed_chunks:
  - prompt: "{long_prompt}"
    chunk_directory: null
---
""")

        result = runner.invoke(cli, ["chunk", "list-proposed", "--project-dir", str(temp_project)])

        assert result.exit_code == 0
        # Should be truncated with ...
        assert "..." in result.output
        # Full prompt shouldn't appear
        assert long_prompt not in result.output
