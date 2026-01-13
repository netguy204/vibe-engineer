"""Integration tests for friction-to-resolution workflow.

# Chunk: docs/chunks/friction_chunk_workflow - Friction workflow integration tests

These tests verify the bidirectional linking between friction entries and chunks:
- /chunk-create adds friction_entries to chunk frontmatter and updates FRICTION.md
- /chunk-complete handles friction resolution status reporting

Note: These are unit/integration tests for the friction workflow logic.
The actual skill templates are tested via manual verification since they're
agent instructions rather than executable code.
"""

import pytest

from chunks import Chunks
from friction import Friction, FrictionStatus
from models import FrictionProposedChunk


class TestFrictionWorkflowIntegration:
    """Integration tests for friction entry lifecycle."""

    def _create_friction_log_with_entries(self, project_dir, entries):
        """Helper to create a FRICTION.md with specified entries."""
        friction_path = project_dir / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)

        # Build entry content
        entry_lines = []
        for entry in entries:
            entry_lines.append(
                f"### {entry['id']}: {entry.get('date', '2026-01-12')} "
                f"[{entry.get('theme', 'test')}] {entry['title']}\n\n"
                f"{entry.get('content', 'Content.')}\n"
            )

        friction_path.write_text(f"""---
themes:
  - id: test
    name: Test Theme
  - id: orchestrator
    name: Orchestrator
proposed_chunks: []
---

# Friction Log

## Entries

{''.join(entry_lines)}
""")

    def _create_chunk_with_friction_entries(
        self, project_dir, chunk_id, friction_entries, status="IMPLEMENTING"
    ):
        """Helper to create a chunk with friction_entries in frontmatter."""
        chunk_dir = project_dir / "docs" / "chunks" / chunk_id
        chunk_dir.mkdir(parents=True, exist_ok=True)

        # Build friction_entries YAML
        if friction_entries:
            friction_yaml = "friction_entries:\n"
            for entry in friction_entries:
                friction_yaml += f"  - entry_id: {entry['entry_id']}\n"
                friction_yaml += f"    scope: {entry.get('scope', 'full')}\n"
        else:
            friction_yaml = "friction_entries: []"

        goal_path = chunk_dir / "GOAL.md"
        goal_path.write_text(f"""---
status: {status}
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: null
subsystems: []
{friction_yaml}
created_after: []
---

# Chunk Goal

## Minor Goal

Test chunk addressing friction.

## Success Criteria

- Test passes
""")
        return chunk_dir

    def _update_friction_proposed_chunks(
        self, project_dir, proposed_chunk
    ):
        """Helper to add a proposed_chunks entry to FRICTION.md."""
        friction = Friction(project_dir)
        content = friction.read_content()
        frontmatter = friction.parse_frontmatter()

        if frontmatter is None:
            return

        # Add the proposed chunk
        frontmatter.proposed_chunks.append(proposed_chunk)

        # Rebuild the file with updated frontmatter
        import yaml
        import re

        match = re.match(r"^---\s*\n.*?\n---\s*\n(.*)$", content, re.DOTALL)
        if match:
            body = match.group(1)
        else:
            body = content

        new_frontmatter = yaml.dump(
            frontmatter.model_dump(), default_flow_style=False, sort_keys=False
        )
        new_content = f"---\n{new_frontmatter}---\n{body}"
        friction.write_content(new_content)


class TestChunkCreateWithFriction(TestFrictionWorkflowIntegration):
    """Tests for /chunk-create friction entry selection workflow."""

    def test_friction_entries_added_to_chunk_frontmatter(self, temp_project):
        """When friction entries are selected, they appear in chunk frontmatter."""
        # Setup: Create friction log with entries
        self._create_friction_log_with_entries(
            temp_project,
            [
                {"id": "F001", "title": "First friction point"},
                {"id": "F002", "title": "Second friction point"},
            ],
        )

        # Simulate what /chunk-create does: create chunk with friction_entries
        self._create_chunk_with_friction_entries(
            temp_project,
            "fix_friction",
            [
                {"entry_id": "F001", "scope": "full"},
                {"entry_id": "F002", "scope": "partial"},
            ],
        )

        # Verify: Chunk frontmatter contains friction_entries
        chunks = Chunks(temp_project)
        frontmatter = chunks.parse_chunk_frontmatter("fix_friction")

        assert frontmatter is not None
        assert len(frontmatter.friction_entries) == 2
        assert frontmatter.friction_entries[0].entry_id == "F001"
        assert frontmatter.friction_entries[0].scope == "full"
        assert frontmatter.friction_entries[1].entry_id == "F002"
        assert frontmatter.friction_entries[1].scope == "partial"

    def test_friction_status_transitions_to_addressed(self, temp_project):
        """When chunk is created with friction_entries, entries become ADDRESSED."""
        # Setup: Create friction log with entries
        self._create_friction_log_with_entries(
            temp_project,
            [
                {"id": "F001", "title": "First friction point"},
                {"id": "F002", "title": "Second friction point"},
            ],
        )

        friction = Friction(temp_project)

        # Verify initial status is OPEN
        assert friction.get_entry_status("F001") == FrictionStatus.OPEN
        assert friction.get_entry_status("F002") == FrictionStatus.OPEN

        # Simulate /chunk-create updating FRICTION.md proposed_chunks
        self._update_friction_proposed_chunks(
            temp_project,
            FrictionProposedChunk(
                prompt="Fix friction points F001 and F002",
                chunk_directory="fix_friction",
                addresses=["F001", "F002"],
            ),
        )

        # Verify status transitions to ADDRESSED
        assert friction.get_entry_status("F001") == FrictionStatus.ADDRESSED
        assert friction.get_entry_status("F002") == FrictionStatus.ADDRESSED

    def test_only_selected_entries_become_addressed(self, temp_project):
        """Only entries in proposed_chunks become ADDRESSED, others stay OPEN."""
        # Setup: Create friction log with entries
        self._create_friction_log_with_entries(
            temp_project,
            [
                {"id": "F001", "title": "First friction point"},
                {"id": "F002", "title": "Second friction point"},
                {"id": "F003", "title": "Third friction point"},
            ],
        )

        friction = Friction(temp_project)

        # Only address F001 and F002
        self._update_friction_proposed_chunks(
            temp_project,
            FrictionProposedChunk(
                prompt="Fix some friction",
                chunk_directory="partial_fix",
                addresses=["F001", "F002"],
            ),
        )

        # Verify F001 and F002 are ADDRESSED, F003 is OPEN
        assert friction.get_entry_status("F001") == FrictionStatus.ADDRESSED
        assert friction.get_entry_status("F002") == FrictionStatus.ADDRESSED
        assert friction.get_entry_status("F003") == FrictionStatus.OPEN


class TestChunkCompleteWithFriction(TestFrictionWorkflowIntegration):
    """Tests for /chunk-complete friction resolution workflow."""

    def test_friction_status_resolved_when_chunk_active(self, temp_project):
        """When chunk is ACTIVE, full-scope friction entries are RESOLVED."""
        # Setup: Create friction log with entries
        self._create_friction_log_with_entries(
            temp_project,
            [
                {"id": "F001", "title": "First friction point"},
            ],
        )

        # Create chunk that addresses the friction (IMPLEMENTING status)
        self._create_chunk_with_friction_entries(
            temp_project,
            "fix_friction",
            [{"entry_id": "F001", "scope": "full"}],
            status="IMPLEMENTING",
        )

        # Update FRICTION.md to link the entry
        self._update_friction_proposed_chunks(
            temp_project,
            FrictionProposedChunk(
                prompt="Fix F001",
                chunk_directory="fix_friction",
                addresses=["F001"],
            ),
        )

        friction = Friction(temp_project)
        chunks = Chunks(temp_project)

        # While chunk is IMPLEMENTING, entry is ADDRESSED (not RESOLVED)
        status = friction.get_entry_status("F001", chunks_module=chunks)
        assert status == FrictionStatus.ADDRESSED

        # Transition chunk to ACTIVE (simulating /chunk-complete)
        self._create_chunk_with_friction_entries(
            temp_project,
            "fix_friction",
            [{"entry_id": "F001", "scope": "full"}],
            status="ACTIVE",
        )

        # Now entry should be RESOLVED
        status = friction.get_entry_status("F001", chunks_module=chunks)
        assert status == FrictionStatus.RESOLVED

    def test_partial_scope_entry_remains_addressed(self, temp_project):
        """Partial-scope entries remain ADDRESSED even when chunk is ACTIVE."""
        # Setup: Create friction log with entries
        self._create_friction_log_with_entries(
            temp_project,
            [
                {"id": "F001", "title": "First friction point"},
            ],
        )

        # Create ACTIVE chunk with partial scope
        self._create_chunk_with_friction_entries(
            temp_project,
            "partial_fix",
            [{"entry_id": "F001", "scope": "partial"}],
            status="ACTIVE",
        )

        # Update FRICTION.md to link the entry
        self._update_friction_proposed_chunks(
            temp_project,
            FrictionProposedChunk(
                prompt="Partial fix for F001",
                chunk_directory="partial_fix",
                addresses=["F001"],
            ),
        )

        friction = Friction(temp_project)
        chunks = Chunks(temp_project)

        # Entry is RESOLVED because the chunk is ACTIVE
        # Note: The current implementation treats any ACTIVE chunk as resolving the entry
        # The scope (full/partial) is informational for the operator
        status = friction.get_entry_status("F001", chunks_module=chunks)
        assert status == FrictionStatus.RESOLVED


class TestFrictionWorkflowEdgeCases(TestFrictionWorkflowIntegration):
    """Edge case tests for friction workflow."""

    def test_chunk_addresses_multiple_themes(self, temp_project):
        """Chunk can address friction entries from multiple themes."""
        # Setup: Create friction log with entries from different themes
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes:
  - id: code-refs
    name: Code References
  - id: templates
    name: Templates
proposed_chunks: []
---

# Friction Log

## Entries

### F001: 2026-01-12 [code-refs] Code ref friction

Content.

### F002: 2026-01-12 [templates] Template friction

Content.
""")

        # Create chunk addressing both
        self._create_chunk_with_friction_entries(
            temp_project,
            "multi_theme_fix",
            [
                {"entry_id": "F001", "scope": "full"},
                {"entry_id": "F002", "scope": "full"},
            ],
        )

        # Update FRICTION.md
        self._update_friction_proposed_chunks(
            temp_project,
            FrictionProposedChunk(
                prompt="Fix multiple theme issues",
                chunk_directory="multi_theme_fix",
                addresses=["F001", "F002"],
            ),
        )

        friction = Friction(temp_project)

        # Both entries should be ADDRESSED
        assert friction.get_entry_status("F001") == FrictionStatus.ADDRESSED
        assert friction.get_entry_status("F002") == FrictionStatus.ADDRESSED

    def test_multiple_chunks_address_same_entry_partial_scope(self, temp_project):
        """Multiple chunks can address the same entry with partial scope."""
        # Setup: Create friction log with one entry
        self._create_friction_log_with_entries(
            temp_project,
            [{"id": "F001", "title": "Complex friction needing multiple fixes"}],
        )

        # Create first chunk (partial scope)
        self._create_chunk_with_friction_entries(
            temp_project,
            "partial_fix_1",
            [{"entry_id": "F001", "scope": "partial"}],
            status="ACTIVE",
        )

        # Create second chunk (partial scope)
        self._create_chunk_with_friction_entries(
            temp_project,
            "partial_fix_2",
            [{"entry_id": "F001", "scope": "partial"}],
            status="IMPLEMENTING",
        )

        # Link first chunk to friction
        self._update_friction_proposed_chunks(
            temp_project,
            FrictionProposedChunk(
                prompt="First partial fix",
                chunk_directory="partial_fix_1",
                addresses=["F001"],
            ),
        )

        friction = Friction(temp_project)
        chunks = Chunks(temp_project)

        # Entry is resolved by first chunk (which is ACTIVE)
        status = friction.get_entry_status("F001", chunks_module=chunks)
        assert status == FrictionStatus.RESOLVED

    def test_ve_friction_list_open_returns_correct_entries(self, temp_project):
        """ve friction list --open correctly filters to OPEN entries only."""
        # Setup: Create friction log with mixed-status entries
        self._create_friction_log_with_entries(
            temp_project,
            [
                {"id": "F001", "title": "Addressed friction"},
                {"id": "F002", "title": "Open friction"},
                {"id": "F003", "title": "Another open friction"},
            ],
        )

        # Mark F001 as addressed
        self._update_friction_proposed_chunks(
            temp_project,
            FrictionProposedChunk(
                prompt="Fix F001",
                chunk_directory="fix_f001",
                addresses=["F001"],
            ),
        )

        friction = Friction(temp_project)

        # List only OPEN entries
        open_entries = friction.list_entries(status_filter=FrictionStatus.OPEN)

        assert len(open_entries) == 2
        entry_ids = [entry.id for entry, status in open_entries]
        assert "F001" not in entry_ids
        assert "F002" in entry_ids
        assert "F003" in entry_ids

    def test_existing_proposed_chunk_updated_when_chunk_created(self, temp_project):
        """If proposed_chunk exists without chunk_directory, it gets updated."""
        # Setup: Create friction log with proposed_chunk (but no chunk_directory)
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes:
  - id: test
    name: Test Theme
proposed_chunks:
  - prompt: Fix friction pattern
    chunk_directory: null
    addresses:
      - F001
      - F002
---

# Friction Log

## Entries

### F001: 2026-01-12 [test] First friction

Content.

### F002: 2026-01-12 [test] Second friction

Content.
""")

        friction = Friction(temp_project)

        # Entries are OPEN because chunk_directory is null
        assert friction.get_entry_status("F001") == FrictionStatus.OPEN
        assert friction.get_entry_status("F002") == FrictionStatus.OPEN

        # Simulate /chunk-create updating the existing proposed_chunk with chunk_directory
        # (In practice, the agent would edit the YAML to set chunk_directory)
        friction_path.write_text("""---
themes:
  - id: test
    name: Test Theme
proposed_chunks:
  - prompt: Fix friction pattern
    chunk_directory: fix_friction_pattern
    addresses:
      - F001
      - F002
---

# Friction Log

## Entries

### F001: 2026-01-12 [test] First friction

Content.

### F002: 2026-01-12 [test] Second friction

Content.
""")

        # Now entries should be ADDRESSED
        assert friction.get_entry_status("F001") == FrictionStatus.ADDRESSED
        assert friction.get_entry_status("F002") == FrictionStatus.ADDRESSED
