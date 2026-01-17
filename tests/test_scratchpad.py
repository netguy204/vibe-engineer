"""Tests for scratchpad storage module."""
# Chunk: docs/chunks/scratchpad_storage - Unit tests for scratchpad infrastructure
# Chunk: docs/chunks/scratchpad_cross_project - Cross-project listing tests

from datetime import datetime
from pathlib import Path
import tempfile
import pytest
import yaml

from models import (
    ScratchpadChunkFrontmatter,
    ScratchpadChunkStatus,
    ScratchpadNarrativeFrontmatter,
    ScratchpadNarrativeStatus,
)
from scratchpad import (
    Scratchpad,
    ScratchpadChunks,
    ScratchpadNarratives,
    ScratchpadEntry,
    ScratchpadListResult,
)


# ============================================================================
# Model Tests
# ============================================================================


class TestScratchpadChunkStatus:
    """Tests for ScratchpadChunkStatus enum."""

    def test_valid_status_values(self):
        """Verify all expected status values exist."""
        assert ScratchpadChunkStatus.IMPLEMENTING == "IMPLEMENTING"
        assert ScratchpadChunkStatus.ACTIVE == "ACTIVE"
        assert ScratchpadChunkStatus.ARCHIVED == "ARCHIVED"

    def test_status_count(self):
        """Verify exactly 3 status values."""
        assert len(ScratchpadChunkStatus) == 3


class TestScratchpadChunkFrontmatter:
    """Tests for ScratchpadChunkFrontmatter model."""

    def test_parse_full_frontmatter(self):
        """Parse frontmatter with all fields populated."""
        data = {
            "status": "IMPLEMENTING",
            "ticket": "LIN-123",
            "success_criteria": ["Criteria 1", "Criteria 2"],
            "created_at": "2025-01-01T10:00:00",
        }
        fm = ScratchpadChunkFrontmatter.model_validate(data)
        assert fm.status == ScratchpadChunkStatus.IMPLEMENTING
        assert fm.ticket == "LIN-123"
        assert fm.success_criteria == ["Criteria 1", "Criteria 2"]
        assert fm.created_at == "2025-01-01T10:00:00"

    def test_parse_minimal_frontmatter(self):
        """Parse frontmatter with only required fields."""
        data = {
            "status": "ACTIVE",
            "created_at": "2025-01-01T10:00:00",
        }
        fm = ScratchpadChunkFrontmatter.model_validate(data)
        assert fm.status == ScratchpadChunkStatus.ACTIVE
        assert fm.ticket is None
        assert fm.success_criteria == []

    def test_invalid_status_raises_error(self):
        """Invalid status value should raise ValidationError."""
        data = {
            "status": "INVALID",
            "created_at": "2025-01-01T10:00:00",
        }
        with pytest.raises(Exception):  # Pydantic ValidationError
            ScratchpadChunkFrontmatter.model_validate(data)


class TestScratchpadNarrativeStatus:
    """Tests for ScratchpadNarrativeStatus enum."""

    def test_valid_status_values(self):
        """Verify all expected status values exist."""
        assert ScratchpadNarrativeStatus.DRAFTING == "DRAFTING"
        assert ScratchpadNarrativeStatus.ACTIVE == "ACTIVE"
        assert ScratchpadNarrativeStatus.ARCHIVED == "ARCHIVED"

    def test_status_count(self):
        """Verify exactly 3 status values."""
        assert len(ScratchpadNarrativeStatus) == 3


class TestScratchpadNarrativeFrontmatter:
    """Tests for ScratchpadNarrativeFrontmatter model."""

    def test_parse_full_frontmatter(self):
        """Parse frontmatter with all fields populated."""
        data = {
            "status": "ACTIVE",
            "ambition": "Refactor the widget system",
            "chunk_prompts": ["Prompt 1", "Prompt 2"],
            "created_at": "2025-01-01T10:00:00",
        }
        fm = ScratchpadNarrativeFrontmatter.model_validate(data)
        assert fm.status == ScratchpadNarrativeStatus.ACTIVE
        assert fm.ambition == "Refactor the widget system"
        assert fm.chunk_prompts == ["Prompt 1", "Prompt 2"]
        assert fm.created_at == "2025-01-01T10:00:00"

    def test_parse_minimal_frontmatter(self):
        """Parse frontmatter with only required fields."""
        data = {
            "status": "DRAFTING",
            "created_at": "2025-01-01T10:00:00",
        }
        fm = ScratchpadNarrativeFrontmatter.model_validate(data)
        assert fm.status == ScratchpadNarrativeStatus.DRAFTING
        assert fm.ambition is None
        assert fm.chunk_prompts == []


# ============================================================================
# Scratchpad Class Tests
# ============================================================================


class TestScratchpad:
    """Tests for Scratchpad class."""

    @pytest.mark.no_isolated_scratchpad
    def test_default_root(self):
        """Default root is ~/.vibe/scratchpad/."""
        scratchpad = Scratchpad()
        assert scratchpad.root == Path.home() / ".vibe" / "scratchpad"

    def test_custom_root(self):
        """Custom root can be provided."""
        custom_path = Path("/custom/path")
        scratchpad = Scratchpad(scratchpad_root=custom_path)
        assert scratchpad.root == custom_path

    def test_ensure_initialized_creates_directory(self, tmp_path: Path):
        """ensure_initialized() creates the directory structure."""
        scratchpad_root = tmp_path / "test_scratchpad_init"
        scratchpad = Scratchpad(scratchpad_root=scratchpad_root)

        assert not scratchpad_root.exists()
        scratchpad.ensure_initialized()
        assert scratchpad_root.exists()
        assert scratchpad_root.is_dir()

    def test_ensure_initialized_idempotent(self, tmp_path: Path):
        """ensure_initialized() can be called multiple times safely."""
        scratchpad_root = tmp_path / "scratchpad"
        scratchpad = Scratchpad(scratchpad_root=scratchpad_root)

        scratchpad.ensure_initialized()
        scratchpad.ensure_initialized()  # Should not raise
        assert scratchpad_root.exists()

    def test_derive_project_name(self, tmp_path: Path):
        """derive_project_name() extracts directory name."""
        repo_path = tmp_path / "my-project"
        repo_path.mkdir()

        assert Scratchpad.derive_project_name(repo_path) == "my-project"

    def test_derive_project_name_resolves_symlinks(self, tmp_path: Path):
        """derive_project_name() resolves symlinks."""
        real_path = tmp_path / "real-project"
        real_path.mkdir()
        symlink_path = tmp_path / "link-to-project"
        symlink_path.symlink_to(real_path)

        assert Scratchpad.derive_project_name(symlink_path) == "real-project"

    def test_get_task_prefix(self):
        """get_task_prefix() adds 'task:' prefix."""
        assert Scratchpad.get_task_prefix("my-task") == "task:my-task"
        assert Scratchpad.get_task_prefix("migration-2025") == "task:migration-2025"

    def test_get_project_dir(self, tmp_path: Path):
        """get_project_dir() returns correct path."""
        scratchpad = Scratchpad(scratchpad_root=tmp_path)
        assert scratchpad.get_project_dir("my-project") == tmp_path / "my-project"

    def test_get_task_dir(self, tmp_path: Path):
        """get_task_dir() returns correct path with task prefix."""
        scratchpad = Scratchpad(scratchpad_root=tmp_path)
        assert scratchpad.get_task_dir("my-task") == tmp_path / "task:my-task"

    def test_resolve_context_with_task_name(self, tmp_path: Path):
        """resolve_context() prioritizes task_name."""
        scratchpad = Scratchpad(scratchpad_root=tmp_path)
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Task name should take priority over project path
        result = scratchpad.resolve_context(
            project_path=project_path,
            task_name="my-task",
        )
        assert result == tmp_path / "task:my-task"

    def test_resolve_context_with_project_path(self, tmp_path: Path):
        """resolve_context() uses project_path when no task_name."""
        scratchpad = Scratchpad(scratchpad_root=tmp_path)
        project_path = tmp_path / "my-project"
        project_path.mkdir()

        result = scratchpad.resolve_context(project_path=project_path)
        assert result == tmp_path / "my-project"

    def test_resolve_context_requires_argument(self, tmp_path: Path):
        """resolve_context() raises if no context provided."""
        scratchpad = Scratchpad(scratchpad_root=tmp_path)

        with pytest.raises(ValueError, match="Either project_path or task_name must be provided"):
            scratchpad.resolve_context()

    def test_list_contexts_empty(self, tmp_path: Path):
        """list_contexts() returns empty list when no contexts exist."""
        scratchpad = Scratchpad(scratchpad_root=tmp_path / "nonexistent")
        assert scratchpad.list_contexts() == []

    def test_list_contexts(self, tmp_path: Path):
        """list_contexts() lists all context directories."""
        scratchpad_root = tmp_path / "test_list_contexts_root"
        scratchpad = Scratchpad(scratchpad_root=scratchpad_root)
        scratchpad.ensure_initialized()

        # Create some context directories
        (scratchpad_root / "project-a").mkdir()
        (scratchpad_root / "project-b").mkdir()
        (scratchpad_root / "task:migration").mkdir()
        (scratchpad_root / ".hidden").mkdir()  # Should be ignored

        contexts = sorted(scratchpad.list_contexts())
        assert contexts == ["project-a", "project-b", "task:migration"]


# ============================================================================
# ScratchpadChunks Tests
# ============================================================================


class TestScratchpadChunks:
    """Tests for ScratchpadChunks manager class."""

    @pytest.fixture
    def setup_chunks(self, tmp_path: Path):
        """Create a scratchpad with chunks manager for testing."""
        scratchpad = Scratchpad(scratchpad_root=tmp_path)
        scratchpad.ensure_initialized()
        context_path = tmp_path / "test-project"
        context_path.mkdir()
        chunks = ScratchpadChunks(scratchpad, context_path)
        return scratchpad, chunks, context_path

    def test_enumerate_chunks_empty(self, setup_chunks):
        """enumerate_chunks() returns empty list when no chunks."""
        _, chunks, _ = setup_chunks
        assert chunks.enumerate_chunks() == []

    def test_create_chunk(self, setup_chunks):
        """create_chunk() creates directory and GOAL.md."""
        _, chunks, context_path = setup_chunks

        chunk_path = chunks.create_chunk("my-chunk")

        assert chunk_path.exists()
        assert chunk_path.is_dir()
        assert chunk_path.name == "my-chunk"
        assert (chunk_path / "GOAL.md").exists()

        # Verify frontmatter
        goal_content = (chunk_path / "GOAL.md").read_text()
        assert "status: IMPLEMENTING" in goal_content
        assert "# my-chunk" in goal_content

    def test_create_chunk_with_ticket(self, setup_chunks):
        """create_chunk() includes ticket in frontmatter."""
        _, chunks, _ = setup_chunks

        chunk_path = chunks.create_chunk("my-chunk", ticket="LIN-123")
        goal_content = (chunk_path / "GOAL.md").read_text()
        assert "ticket: LIN-123" in goal_content

    def test_create_chunk_duplicate_raises_error(self, setup_chunks):
        """create_chunk() rejects duplicate names."""
        _, chunks, _ = setup_chunks

        chunks.create_chunk("my-chunk")
        with pytest.raises(ValueError, match="already exists"):
            chunks.create_chunk("my-chunk")

    def test_create_chunk_invalid_name(self, setup_chunks):
        """create_chunk() rejects invalid short_name."""
        _, chunks, _ = setup_chunks

        with pytest.raises(ValueError, match="Invalid short_name"):
            chunks.create_chunk("123-invalid")  # Must start with letter

        with pytest.raises(ValueError, match="Invalid short_name"):
            chunks.create_chunk("My-Chunk")  # Must be lowercase

        with pytest.raises(ValueError, match="Invalid short_name"):
            chunks.create_chunk("")  # Cannot be empty

    def test_enumerate_chunks(self, setup_chunks):
        """enumerate_chunks() lists chunk directories."""
        _, chunks, _ = setup_chunks

        chunks.create_chunk("chunk-a")
        chunks.create_chunk("chunk-b")
        chunks.create_chunk("chunk-c")

        chunk_list = sorted(chunks.enumerate_chunks())
        assert chunk_list == ["chunk-a", "chunk-b", "chunk-c"]

    def test_get_chunk_path(self, setup_chunks):
        """get_chunk_path() returns path for existing chunk."""
        _, chunks, context_path = setup_chunks

        chunks.create_chunk("my-chunk")

        path = chunks.get_chunk_path("my-chunk")
        assert path == context_path / "chunks" / "my-chunk"

    def test_get_chunk_path_not_found(self, setup_chunks):
        """get_chunk_path() returns None for non-existent chunk."""
        _, chunks, _ = setup_chunks

        assert chunks.get_chunk_path("nonexistent") is None

    def test_get_chunk_goal_path(self, setup_chunks):
        """get_chunk_goal_path() returns path to GOAL.md."""
        _, chunks, context_path = setup_chunks

        chunks.create_chunk("my-chunk")

        goal_path = chunks.get_chunk_goal_path("my-chunk")
        assert goal_path == context_path / "chunks" / "my-chunk" / "GOAL.md"

    def test_parse_chunk_frontmatter(self, setup_chunks):
        """parse_chunk_frontmatter() parses valid frontmatter."""
        _, chunks, _ = setup_chunks

        chunks.create_chunk("my-chunk", ticket="LIN-456")

        fm = chunks.parse_chunk_frontmatter("my-chunk")
        assert fm is not None
        assert fm.status == ScratchpadChunkStatus.IMPLEMENTING
        assert fm.ticket == "LIN-456"
        assert isinstance(fm.created_at, str)

    def test_parse_chunk_frontmatter_not_found(self, setup_chunks):
        """parse_chunk_frontmatter() returns None for non-existent chunk."""
        _, chunks, _ = setup_chunks

        assert chunks.parse_chunk_frontmatter("nonexistent") is None

    def test_parse_chunk_frontmatter_invalid(self, setup_chunks):
        """parse_chunk_frontmatter() returns None for invalid frontmatter."""
        _, chunks, context_path = setup_chunks

        # Create chunk manually with invalid frontmatter
        chunk_path = context_path / "chunks" / "bad-chunk"
        chunk_path.mkdir(parents=True)
        (chunk_path / "GOAL.md").write_text("No frontmatter here")

        assert chunks.parse_chunk_frontmatter("bad-chunk") is None

    def test_list_chunks_ordered_by_creation(self, setup_chunks):
        """list_chunks() orders by creation time (newest first)."""
        _, chunks, context_path = setup_chunks

        # Create chunks with specific timestamps
        chunks_dir = context_path / "chunks"
        chunks_dir.mkdir(parents=True)

        for name, time in [
            ("old-chunk", "2025-01-01T10:00:00"),
            ("middle-chunk", "2025-01-02T10:00:00"),
            ("new-chunk", "2025-01-03T10:00:00"),
        ]:
            chunk_path = chunks_dir / name
            chunk_path.mkdir()
            (chunk_path / "GOAL.md").write_text(
                f"---\nstatus: IMPLEMENTING\ncreated_at: \"{time}\"\n---\n# {name}\n"
            )

        chunk_list = chunks.list_chunks()
        assert chunk_list == ["new-chunk", "middle-chunk", "old-chunk"]

    def test_archive_chunk(self, setup_chunks):
        """archive_chunk() updates status to ARCHIVED."""
        _, chunks, _ = setup_chunks

        chunks.create_chunk("my-chunk")

        # Verify initial status
        fm = chunks.parse_chunk_frontmatter("my-chunk")
        assert fm.status == ScratchpadChunkStatus.IMPLEMENTING

        # Archive
        chunks.archive_chunk("my-chunk")

        # Verify archived status
        fm = chunks.parse_chunk_frontmatter("my-chunk")
        assert fm.status == ScratchpadChunkStatus.ARCHIVED

    def test_archive_chunk_not_found(self, setup_chunks):
        """archive_chunk() raises for non-existent chunk."""
        _, chunks, _ = setup_chunks

        with pytest.raises(ValueError, match="not found"):
            chunks.archive_chunk("nonexistent")


# ============================================================================
# ScratchpadNarratives Tests
# ============================================================================


class TestScratchpadNarratives:
    """Tests for ScratchpadNarratives manager class."""

    @pytest.fixture
    def setup_narratives(self, tmp_path: Path):
        """Create a scratchpad with narratives manager for testing."""
        scratchpad = Scratchpad(scratchpad_root=tmp_path)
        scratchpad.ensure_initialized()
        context_path = tmp_path / "test-project"
        context_path.mkdir()
        narratives = ScratchpadNarratives(scratchpad, context_path)
        return scratchpad, narratives, context_path

    def test_enumerate_narratives_empty(self, setup_narratives):
        """enumerate_narratives() returns empty list when no narratives."""
        _, narratives, _ = setup_narratives
        assert narratives.enumerate_narratives() == []

    def test_create_narrative(self, setup_narratives):
        """create_narrative() creates directory and OVERVIEW.md."""
        _, narratives, context_path = setup_narratives

        narrative_path = narratives.create_narrative("my-narrative")

        assert narrative_path.exists()
        assert narrative_path.is_dir()
        assert narrative_path.name == "my-narrative"
        assert (narrative_path / "OVERVIEW.md").exists()

        # Verify frontmatter
        overview_content = (narrative_path / "OVERVIEW.md").read_text()
        assert "status: DRAFTING" in overview_content
        assert "# my-narrative" in overview_content

    def test_create_narrative_duplicate_raises_error(self, setup_narratives):
        """create_narrative() rejects duplicate names."""
        _, narratives, _ = setup_narratives

        narratives.create_narrative("my-narrative")
        with pytest.raises(ValueError, match="already exists"):
            narratives.create_narrative("my-narrative")

    def test_create_narrative_invalid_name(self, setup_narratives):
        """create_narrative() rejects invalid short_name."""
        _, narratives, _ = setup_narratives

        with pytest.raises(ValueError, match="Invalid short_name"):
            narratives.create_narrative("123-invalid")

        with pytest.raises(ValueError, match="Invalid short_name"):
            narratives.create_narrative("My-Narrative")

    def test_enumerate_narratives(self, setup_narratives):
        """enumerate_narratives() lists narrative directories."""
        _, narratives, _ = setup_narratives

        narratives.create_narrative("narrative-a")
        narratives.create_narrative("narrative-b")

        narrative_list = sorted(narratives.enumerate_narratives())
        assert narrative_list == ["narrative-a", "narrative-b"]

    def test_get_narrative_path(self, setup_narratives):
        """get_narrative_path() returns path for existing narrative."""
        _, narratives, context_path = setup_narratives

        narratives.create_narrative("my-narrative")

        path = narratives.get_narrative_path("my-narrative")
        assert path == context_path / "narratives" / "my-narrative"

    def test_get_narrative_path_not_found(self, setup_narratives):
        """get_narrative_path() returns None for non-existent narrative."""
        _, narratives, _ = setup_narratives

        assert narratives.get_narrative_path("nonexistent") is None

    def test_get_narrative_overview_path(self, setup_narratives):
        """get_narrative_overview_path() returns path to OVERVIEW.md."""
        _, narratives, context_path = setup_narratives

        narratives.create_narrative("my-narrative")

        overview_path = narratives.get_narrative_overview_path("my-narrative")
        assert overview_path == context_path / "narratives" / "my-narrative" / "OVERVIEW.md"

    def test_parse_narrative_frontmatter(self, setup_narratives):
        """parse_narrative_frontmatter() parses valid frontmatter."""
        _, narratives, _ = setup_narratives

        narratives.create_narrative("my-narrative")

        fm = narratives.parse_narrative_frontmatter("my-narrative")
        assert fm is not None
        assert fm.status == ScratchpadNarrativeStatus.DRAFTING
        assert isinstance(fm.created_at, str)

    def test_parse_narrative_frontmatter_not_found(self, setup_narratives):
        """parse_narrative_frontmatter() returns None for non-existent narrative."""
        _, narratives, _ = setup_narratives

        assert narratives.parse_narrative_frontmatter("nonexistent") is None

    def test_parse_narrative_frontmatter_invalid(self, setup_narratives):
        """parse_narrative_frontmatter() returns None for invalid frontmatter."""
        _, narratives, context_path = setup_narratives

        # Create narrative manually with invalid frontmatter
        narrative_path = context_path / "narratives" / "bad-narrative"
        narrative_path.mkdir(parents=True)
        (narrative_path / "OVERVIEW.md").write_text("No frontmatter here")

        assert narratives.parse_narrative_frontmatter("bad-narrative") is None

    def test_list_narratives_ordered_by_creation(self, setup_narratives):
        """list_narratives() orders by creation time (newest first)."""
        _, narratives, context_path = setup_narratives

        # Create narratives with specific timestamps
        narratives_dir = context_path / "narratives"
        narratives_dir.mkdir(parents=True)

        for name, time in [
            ("old-narrative", "2025-01-01T10:00:00"),
            ("middle-narrative", "2025-01-02T10:00:00"),
            ("new-narrative", "2025-01-03T10:00:00"),
        ]:
            narrative_path = narratives_dir / name
            narrative_path.mkdir()
            (narrative_path / "OVERVIEW.md").write_text(
                f"---\nstatus: DRAFTING\ncreated_at: \"{time}\"\n---\n# {name}\n"
            )

        narrative_list = narratives.list_narratives()
        assert narrative_list == ["new-narrative", "middle-narrative", "old-narrative"]

    def test_archive_narrative(self, setup_narratives):
        """archive_narrative() updates status to ARCHIVED."""
        _, narratives, _ = setup_narratives

        narratives.create_narrative("my-narrative")

        # Verify initial status
        fm = narratives.parse_narrative_frontmatter("my-narrative")
        assert fm.status == ScratchpadNarrativeStatus.DRAFTING

        # Archive
        narratives.archive_narrative("my-narrative")

        # Verify archived status
        fm = narratives.parse_narrative_frontmatter("my-narrative")
        assert fm.status == ScratchpadNarrativeStatus.ARCHIVED

    def test_archive_narrative_not_found(self, setup_narratives):
        """archive_narrative() raises for non-existent narrative."""
        _, narratives, _ = setup_narratives

        with pytest.raises(ValueError, match="not found"):
            narratives.archive_narrative("nonexistent")


# ============================================================================
# Cross-Project Listing Tests (scratchpad_cross_project chunk)
# ============================================================================


class TestScratchpadEntry:
    """Tests for ScratchpadEntry dataclass."""

    def test_entry_creation(self):
        """ScratchpadEntry can be created with all fields."""
        entry = ScratchpadEntry(
            context_name="vibe-engineer",
            artifact_type="chunk",
            name="my-chunk",
            status="IMPLEMENTING",
            created_at="2025-01-01T10:00:00",
        )
        assert entry.context_name == "vibe-engineer"
        assert entry.artifact_type == "chunk"
        assert entry.name == "my-chunk"
        assert entry.status == "IMPLEMENTING"
        assert entry.created_at == "2025-01-01T10:00:00"

    def test_entry_task_context(self):
        """ScratchpadEntry supports task: prefixed context names."""
        entry = ScratchpadEntry(
            context_name="task:cloud-migration",
            artifact_type="narrative",
            name="migration-plan",
            status="DRAFTING",
            created_at="2025-01-02T10:00:00",
        )
        assert entry.context_name == "task:cloud-migration"


class TestScratchpadListResult:
    """Tests for ScratchpadListResult dataclass."""

    def test_empty_result(self):
        """ScratchpadListResult with no entries."""
        result = ScratchpadListResult(entries_by_context={}, total_count=0)
        assert result.entries_by_context == {}
        assert result.total_count == 0

    def test_result_with_entries(self):
        """ScratchpadListResult with multiple contexts."""
        entries = [
            ScratchpadEntry("project-a", "chunk", "chunk1", "IMPLEMENTING", "2025-01-01T10:00:00"),
            ScratchpadEntry("project-a", "narrative", "plan", "DRAFTING", "2025-01-01T10:00:00"),
        ]
        result = ScratchpadListResult(
            entries_by_context={"project-a": entries},
            total_count=2,
        )
        assert len(result.entries_by_context["project-a"]) == 2
        assert result.total_count == 2


class TestScratchpadListAll:
    """Tests for Scratchpad.list_all() cross-project listing."""

    @pytest.fixture
    def setup_multi_context(self, tmp_path: Path):
        """Create a scratchpad with multiple contexts for testing."""
        scratchpad = Scratchpad(scratchpad_root=tmp_path)
        scratchpad.ensure_initialized()

        # Create multiple contexts
        contexts = {
            "vibe-engineer": {"chunks": ["chunk-a", "chunk-b"], "narratives": ["plan-1"]},
            "pybusiness": {"chunks": ["fix-bug"], "narratives": []},
            "task:cloud-migration": {"chunks": ["migrate-auth"], "narratives": ["migration-plan"]},
        }

        for context_name, artifacts in contexts.items():
            context_path = tmp_path / context_name
            context_path.mkdir(parents=True)

            # Create chunks
            chunks_dir = context_path / "chunks"
            chunks_dir.mkdir()
            for i, chunk_name in enumerate(artifacts["chunks"]):
                chunk_path = chunks_dir / chunk_name
                chunk_path.mkdir()
                (chunk_path / "GOAL.md").write_text(
                    f'---\nstatus: IMPLEMENTING\ncreated_at: "2025-01-0{i+1}T10:00:00"\n---\n# {chunk_name}\n'
                )

            # Create narratives
            narratives_dir = context_path / "narratives"
            narratives_dir.mkdir()
            for i, narrative_name in enumerate(artifacts["narratives"]):
                narrative_path = narratives_dir / narrative_name
                narrative_path.mkdir()
                (narrative_path / "OVERVIEW.md").write_text(
                    f'---\nstatus: DRAFTING\ncreated_at: "2025-01-0{i+1}T10:00:00"\n---\n# {narrative_name}\n'
                )

        return scratchpad

    def test_list_all_returns_all_contexts(self, setup_multi_context):
        """list_all() returns entries from all contexts."""
        scratchpad = setup_multi_context

        result = scratchpad.list_all()

        assert "vibe-engineer" in result.entries_by_context
        assert "pybusiness" in result.entries_by_context
        assert "task:cloud-migration" in result.entries_by_context

    def test_list_all_includes_both_artifact_types(self, setup_multi_context):
        """list_all() includes both chunks and narratives."""
        scratchpad = setup_multi_context

        result = scratchpad.list_all()

        # vibe-engineer should have 2 chunks and 1 narrative
        ve_entries = result.entries_by_context["vibe-engineer"]
        chunks = [e for e in ve_entries if e.artifact_type == "chunk"]
        narratives = [e for e in ve_entries if e.artifact_type == "narrative"]
        assert len(chunks) == 2
        assert len(narratives) == 1

    def test_list_all_total_count(self, setup_multi_context):
        """list_all() returns correct total count."""
        scratchpad = setup_multi_context

        result = scratchpad.list_all()

        # 2 + 1 + 1 + 1 + 1 = 6 total entries
        assert result.total_count == 6

    def test_list_all_empty_scratchpad(self, tmp_path: Path):
        """list_all() returns empty result for empty scratchpad."""
        scratchpad = Scratchpad(scratchpad_root=tmp_path / "nonexistent")

        result = scratchpad.list_all()

        assert result.entries_by_context == {}
        assert result.total_count == 0

    def test_list_all_filter_chunks_only(self, setup_multi_context):
        """list_all(artifact_type='chunk') returns only chunks."""
        scratchpad = setup_multi_context

        result = scratchpad.list_all(artifact_type="chunk")

        for entries in result.entries_by_context.values():
            for entry in entries:
                assert entry.artifact_type == "chunk"

    def test_list_all_filter_narratives_only(self, setup_multi_context):
        """list_all(artifact_type='narrative') returns only narratives."""
        scratchpad = setup_multi_context

        result = scratchpad.list_all(artifact_type="narrative")

        for entries in result.entries_by_context.values():
            for entry in entries:
                assert entry.artifact_type == "narrative"

    def test_list_all_filter_tasks_only(self, setup_multi_context):
        """list_all(context_type='task') returns only task contexts."""
        scratchpad = setup_multi_context

        result = scratchpad.list_all(context_type="task")

        assert "task:cloud-migration" in result.entries_by_context
        assert "vibe-engineer" not in result.entries_by_context
        assert "pybusiness" not in result.entries_by_context

    def test_list_all_filter_projects_only(self, setup_multi_context):
        """list_all(context_type='project') returns only project contexts."""
        scratchpad = setup_multi_context

        result = scratchpad.list_all(context_type="project")

        assert "vibe-engineer" in result.entries_by_context
        assert "pybusiness" in result.entries_by_context
        assert "task:cloud-migration" not in result.entries_by_context

    def test_list_all_filter_by_status(self, tmp_path: Path):
        """list_all(status='ACTIVE') returns only entries with that status."""
        scratchpad = Scratchpad(scratchpad_root=tmp_path)
        scratchpad.ensure_initialized()

        # Create context with mixed statuses
        context_path = tmp_path / "test-project"
        chunks_dir = context_path / "chunks"
        chunks_dir.mkdir(parents=True)

        for name, status in [("active-chunk", "ACTIVE"), ("implementing-chunk", "IMPLEMENTING")]:
            chunk_path = chunks_dir / name
            chunk_path.mkdir()
            (chunk_path / "GOAL.md").write_text(
                f'---\nstatus: {status}\ncreated_at: "2025-01-01T10:00:00"\n---\n# {name}\n'
            )

        result = scratchpad.list_all(status="ACTIVE")

        all_entries = [e for entries in result.entries_by_context.values() for e in entries]
        assert len(all_entries) == 1
        assert all_entries[0].name == "active-chunk"
        assert all_entries[0].status == "ACTIVE"

    def test_list_all_status_case_insensitive(self, tmp_path: Path):
        """list_all() normalizes status filter to uppercase."""
        scratchpad = Scratchpad(scratchpad_root=tmp_path)
        scratchpad.ensure_initialized()

        context_path = tmp_path / "test-project"
        chunks_dir = context_path / "chunks"
        chunks_dir.mkdir(parents=True)

        chunk_path = chunks_dir / "test-chunk"
        chunk_path.mkdir()
        (chunk_path / "GOAL.md").write_text(
            '---\nstatus: IMPLEMENTING\ncreated_at: "2025-01-01T10:00:00"\n---\n# test-chunk\n'
        )

        result = scratchpad.list_all(status="implementing")  # lowercase

        all_entries = [e for entries in result.entries_by_context.values() for e in entries]
        assert len(all_entries) == 1
        assert all_entries[0].status == "IMPLEMENTING"

    def test_list_all_entries_sorted_newest_first(self, tmp_path: Path):
        """list_all() returns entries sorted by creation time (newest first)."""
        scratchpad = Scratchpad(scratchpad_root=tmp_path)
        scratchpad.ensure_initialized()

        context_path = tmp_path / "test-project"
        chunks_dir = context_path / "chunks"
        chunks_dir.mkdir(parents=True)

        for name, time in [
            ("old-chunk", "2025-01-01T10:00:00"),
            ("new-chunk", "2025-01-03T10:00:00"),
            ("middle-chunk", "2025-01-02T10:00:00"),
        ]:
            chunk_path = chunks_dir / name
            chunk_path.mkdir()
            (chunk_path / "GOAL.md").write_text(
                f'---\nstatus: IMPLEMENTING\ncreated_at: "{time}"\n---\n# {name}\n'
            )

        result = scratchpad.list_all()

        entries = result.entries_by_context["test-project"]
        assert entries[0].name == "new-chunk"
        assert entries[1].name == "middle-chunk"
        assert entries[2].name == "old-chunk"


class TestScratchpadListContext:
    """Tests for Scratchpad.list_context() single-context listing."""

    @pytest.fixture
    def setup_single_context(self, tmp_path: Path):
        """Create a scratchpad with a single context for testing."""
        scratchpad = Scratchpad(scratchpad_root=tmp_path)
        scratchpad.ensure_initialized()

        context_path = tmp_path / "test-project"
        context_path.mkdir()

        # Create chunks
        chunks_dir = context_path / "chunks"
        chunks_dir.mkdir()
        chunk_path = chunks_dir / "my-chunk"
        chunk_path.mkdir()
        (chunk_path / "GOAL.md").write_text(
            '---\nstatus: IMPLEMENTING\ncreated_at: "2025-01-01T10:00:00"\n---\n# my-chunk\n'
        )

        # Create narratives
        narratives_dir = context_path / "narratives"
        narratives_dir.mkdir()
        narrative_path = narratives_dir / "my-narrative"
        narrative_path.mkdir()
        (narrative_path / "OVERVIEW.md").write_text(
            '---\nstatus: DRAFTING\ncreated_at: "2025-01-01T10:00:00"\n---\n# my-narrative\n'
        )

        return scratchpad

    def test_list_context_returns_single_context(self, setup_single_context):
        """list_context() returns entries for specified context only."""
        scratchpad = setup_single_context

        result = scratchpad.list_context("test-project")

        assert "test-project" in result.entries_by_context
        assert len(result.entries_by_context) == 1

    def test_list_context_nonexistent(self, setup_single_context):
        """list_context() returns empty result for nonexistent context."""
        scratchpad = setup_single_context

        result = scratchpad.list_context("nonexistent-project")

        assert result.entries_by_context == {}
        assert result.total_count == 0

    def test_list_context_with_filters(self, setup_single_context):
        """list_context() applies artifact_type and status filters."""
        scratchpad = setup_single_context

        result = scratchpad.list_context("test-project", artifact_type="chunk")

        entries = result.entries_by_context["test-project"]
        assert len(entries) == 1
        assert entries[0].artifact_type == "chunk"
