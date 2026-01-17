# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
"""Tests for the orchestrator conflict oracle."""

import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from orchestrator.oracle import (
    AnalysisStage,
    ConflictOracle,
    create_oracle,
)
from orchestrator.models import (
    ConflictAnalysis,
    ConflictVerdict,
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)
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


@pytest.fixture
def project_dir(tmp_path):
    """Create a project directory with chunk structure."""
    # Create chunk directories
    chunk_dir = tmp_path / "docs" / "chunks"
    chunk_dir.mkdir(parents=True)

    return tmp_path


@pytest.fixture
def oracle(project_dir, store):
    """Create a conflict oracle for testing."""
    return create_oracle(project_dir, store)


class TestAnalysisStageDetection:
    """Tests for detecting analysis stage based on chunk state."""

    def test_proposed_stage_when_no_chunk_dir(self, oracle, project_dir):
        """Returns PROPOSED when chunk directory doesn't exist."""
        stage = oracle._detect_stage("nonexistent_chunk")
        assert stage == AnalysisStage.PROPOSED

    def test_goal_stage_when_goal_exists(self, oracle, project_dir):
        """Returns GOAL when GOAL.md exists."""
        # Create chunk with GOAL.md
        chunk_dir = project_dir / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: FUTURE
---
## Minor Goal
Test goal
""")

        stage = oracle._detect_stage("test_chunk")
        assert stage == AnalysisStage.GOAL

    def test_plan_stage_when_plan_has_locations(self, oracle, project_dir):
        """Returns PLAN when PLAN.md has Location: lines."""
        chunk_dir = project_dir / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("## Minor Goal\nTest")
        (chunk_dir / "PLAN.md").write_text("""
## Step 1
Location: src/foo.py

Implement foo
""")

        stage = oracle._detect_stage("test_chunk")
        assert stage == AnalysisStage.PLAN


class TestLocationExtraction:
    """Tests for extracting Location: lines from PLAN.md."""

    def test_extracts_simple_locations(self, oracle, project_dir):
        """Extracts simple file paths from Location: lines."""
        chunk_dir = project_dir / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "PLAN.md").write_text("""
## Step 1
Location: src/foo.py

## Step 2
Location: src/bar.py
""")

        locations = oracle._extract_locations_from_plan("test_chunk")
        assert "src/foo.py" in locations
        assert "src/bar.py" in locations

    def test_extracts_locations_with_annotations(self, oracle, project_dir):
        """Extracts paths from Location: lines with (new file) etc."""
        chunk_dir = project_dir / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "PLAN.md").write_text("""
## Step 1
Location: src/new_module.py (new file)

## Step 2
Location: src/existing.py (modify)
""")

        locations = oracle._extract_locations_from_plan("test_chunk")
        assert "src/new_module.py" in locations
        assert "src/existing.py" in locations

    def test_extracts_backtick_locations(self, oracle, project_dir):
        """Extracts paths from Location: `path` format."""
        chunk_dir = project_dir / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "PLAN.md").write_text("""
## Step 1
Location: `src/foo.py`
""")

        locations = oracle._extract_locations_from_plan("test_chunk")
        assert "src/foo.py" in locations

    def test_returns_empty_for_missing_plan(self, oracle, project_dir):
        """Returns empty list when PLAN.md doesn't exist."""
        locations = oracle._extract_locations_from_plan("nonexistent")
        assert locations == []


class TestPlanStageAnalysis:
    """Tests for conflict analysis at PLAN stage (file overlap)."""

    def test_independent_when_no_file_overlap(self, oracle, project_dir, store):
        """Returns INDEPENDENT when chunks touch different files."""
        # Create chunk_a with Location: src/foo.py
        chunk_a_dir = project_dir / "docs" / "chunks" / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text("## Minor Goal\nTest A")
        (chunk_a_dir / "PLAN.md").write_text("Location: src/foo.py")

        # Create chunk_b with Location: src/bar.py
        chunk_b_dir = project_dir / "docs" / "chunks" / "chunk_b"
        chunk_b_dir.mkdir(parents=True)
        (chunk_b_dir / "GOAL.md").write_text("## Minor Goal\nTest B")
        (chunk_b_dir / "PLAN.md").write_text("Location: src/bar.py")

        analysis = oracle.analyze_conflict("chunk_a", "chunk_b")

        assert analysis.verdict == ConflictVerdict.INDEPENDENT
        assert analysis.analysis_stage == AnalysisStage.PLAN
        assert analysis.confidence >= 0.7

    def test_ask_operator_when_single_file_overlap(self, oracle, project_dir, store):
        """Returns ASK_OPERATOR when chunks share one file."""
        # Create chunk_a
        chunk_a_dir = project_dir / "docs" / "chunks" / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text("## Minor Goal\nTest A")
        (chunk_a_dir / "PLAN.md").write_text("""
Location: src/shared.py
Location: src/foo.py
""")

        # Create chunk_b touching shared.py
        chunk_b_dir = project_dir / "docs" / "chunks" / "chunk_b"
        chunk_b_dir.mkdir(parents=True)
        (chunk_b_dir / "GOAL.md").write_text("## Minor Goal\nTest B")
        (chunk_b_dir / "PLAN.md").write_text("""
Location: src/shared.py
Location: src/bar.py
""")

        analysis = oracle.analyze_conflict("chunk_a", "chunk_b")

        assert analysis.verdict == ConflictVerdict.ASK_OPERATOR
        assert "src/shared.py" in analysis.overlapping_files

    def test_serialize_when_multiple_file_overlaps(self, oracle, project_dir, store):
        """Returns SERIALIZE when chunks share multiple files."""
        # Create chunk_a
        chunk_a_dir = project_dir / "docs" / "chunks" / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text("## Minor Goal\nTest A")
        (chunk_a_dir / "PLAN.md").write_text("""
Location: src/shared1.py
Location: src/shared2.py
Location: src/shared3.py
""")

        # Create chunk_b touching all same files
        chunk_b_dir = project_dir / "docs" / "chunks" / "chunk_b"
        chunk_b_dir.mkdir(parents=True)
        (chunk_b_dir / "GOAL.md").write_text("## Minor Goal\nTest B")
        (chunk_b_dir / "PLAN.md").write_text("""
Location: src/shared1.py
Location: src/shared2.py
Location: src/shared3.py
""")

        analysis = oracle.analyze_conflict("chunk_a", "chunk_b")

        assert analysis.verdict == ConflictVerdict.SERIALIZE
        assert len(analysis.overlapping_files) >= 3


class TestGoalStageAnalysis:
    """Tests for conflict analysis at GOAL stage (semantic comparison)."""

    def test_template_boilerplate_not_flagged_as_conflict(self, oracle, project_dir, store):
        """Template comment block in GOAL.md should not cause false positive conflicts.

        Regression test: chunks with identical template boilerplate but distinct
        actual goals were being flagged as conflicting due to example paths like
        'src/segment/writer.rs' appearing in both templates.
        """
        # Standard GOAL.md template with example paths that caused false positives
        template_comment = '''<!--
╔══════════════════════════════════════════════════════════════════════════════╗
║  DO NOT DELETE THIS COMMENT BLOCK until the chunk complete command is run.   ║
╚══════════════════════════════════════════════════════════════════════════════╝

CODE_PATHS:
- Populated at planning time
- List files you expect to create or modify
- Example: ["src/segment/writer.rs", "src/segment/format.rs"]

CODE_REFERENCES:
- Example:
  code_references:
    - ref: src/segment/writer.rs#SegmentWriter
      implements: "Core write loop and buffer management"
-->'''

        # Create chunk_a about authentication (with template)
        chunk_a_dir = project_dir / "docs" / "chunks" / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text(f"""---
status: FUTURE
---
{template_comment}

## Minor Goal
Implement user authentication with OAuth2 flow.
""")

        # Create chunk_b about UI (with same template)
        chunk_b_dir = project_dir / "docs" / "chunks" / "chunk_b"
        chunk_b_dir.mkdir(parents=True)
        (chunk_b_dir / "GOAL.md").write_text(f"""---
status: FUTURE
---
{template_comment}

## Minor Goal
Add dark mode toggle to the settings page.
""")

        analysis = oracle.analyze_conflict("chunk_a", "chunk_b")

        # Should be INDEPENDENT - the template examples should NOT cause overlap
        assert analysis.verdict == ConflictVerdict.INDEPENDENT, (
            f"Expected INDEPENDENT but got {analysis.verdict}. "
            f"Reason: {analysis.reason}. "
            "Template boilerplate should be stripped before analysis."
        )

    def test_independent_when_goals_distinct(self, oracle, project_dir, store):
        """Returns INDEPENDENT when goals describe distinct work."""
        # Create chunk_a about authentication
        chunk_a_dir = project_dir / "docs" / "chunks" / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text("""---
status: FUTURE
---
## Minor Goal
Implement database connection pooling for PostgreSQL backend.
""")

        # Create chunk_b about UI
        chunk_b_dir = project_dir / "docs" / "chunks" / "chunk_b"
        chunk_b_dir.mkdir(parents=True)
        (chunk_b_dir / "GOAL.md").write_text("""---
status: FUTURE
---
## Minor Goal
Add dark mode toggle to the user interface settings page.
""")

        analysis = oracle.analyze_conflict("chunk_a", "chunk_b")

        # Should be INDEPENDENT since goals are clearly distinct
        assert analysis.verdict == ConflictVerdict.INDEPENDENT

    def test_ask_operator_when_goals_share_terms(self, oracle, project_dir, store):
        """Returns ASK_OPERATOR when goals share significant terms."""
        # Create chunk_a
        chunk_a_dir = project_dir / "docs" / "chunks" / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text("""---
status: FUTURE
---
## Minor Goal
Add user_authentication validation to the login_handler module.
""")

        # Create chunk_b with overlapping terms
        chunk_b_dir = project_dir / "docs" / "chunks" / "chunk_b"
        chunk_b_dir.mkdir(parents=True)
        (chunk_b_dir / "GOAL.md").write_text("""---
status: FUTURE
---
## Minor Goal
Implement user_authentication token refresh in login_handler.
""")

        analysis = oracle.analyze_conflict("chunk_a", "chunk_b")

        assert analysis.verdict == ConflictVerdict.ASK_OPERATOR


class TestProposedStageAnalysis:
    """Tests for conflict analysis at PROPOSED stage."""

    def test_ask_operator_for_proposed_stage(self, oracle, project_dir, store):
        """Returns ASK_OPERATOR with low confidence for PROPOSED stage."""
        # Neither chunk has any files
        analysis = oracle.analyze_conflict("nonexistent_a", "nonexistent_b")

        assert analysis.verdict == ConflictVerdict.ASK_OPERATOR
        assert analysis.confidence <= 0.3
        assert analysis.analysis_stage == AnalysisStage.PROPOSED


class TestConflictCaching:
    """Tests for caching and retrieval of conflict analyses."""

    def test_should_serialize_caches_result(self, oracle, project_dir, store):
        """should_serialize() caches the analysis result."""
        # Create chunks at GOAL stage
        for chunk in ["chunk_a", "chunk_b"]:
            chunk_dir = project_dir / "docs" / "chunks" / chunk
            chunk_dir.mkdir(parents=True)
            (chunk_dir / "GOAL.md").write_text(f"## Minor Goal\nTest {chunk}")

        # First call - triggers analysis
        verdict1 = oracle.should_serialize("chunk_a", "chunk_b")

        # Second call - should use cache
        verdict2 = oracle.should_serialize("chunk_a", "chunk_b")

        assert verdict1 == verdict2

        # Verify analysis was stored
        stored = store.get_conflict_analysis("chunk_a", "chunk_b")
        assert stored is not None
        assert stored.verdict == verdict1

    def test_cached_analysis_independent_of_order(self, oracle, project_dir, store):
        """Cached analysis found regardless of chunk order in query."""
        for chunk in ["chunk_a", "chunk_b"]:
            chunk_dir = project_dir / "docs" / "chunks" / chunk
            chunk_dir.mkdir(parents=True)
            (chunk_dir / "GOAL.md").write_text(f"## Minor Goal\nTest {chunk}")

        # Analyze in one order
        oracle.analyze_conflict("chunk_a", "chunk_b")

        # Retrieve in opposite order
        stored = store.get_conflict_analysis("chunk_b", "chunk_a")
        assert stored is not None


class TestHtmlCommentStripping:
    """Tests for the _strip_html_comments helper."""

    def test_single_line_comment_removed(self, oracle):
        """Single-line HTML comments are removed."""
        text = "text before <!-- comment --> text after"
        result = oracle._strip_html_comments(text)
        assert result == "text before  text after"

    def test_multi_line_comment_removed(self, oracle):
        """Multi-line HTML comments are removed."""
        text = """text before
<!-- this is
a multi-line
comment -->
text after"""
        result = oracle._strip_html_comments(text)
        assert "this is" not in result
        assert "multi-line" not in result
        assert "text before" in result
        assert "text after" in result

    def test_multiple_comments_all_removed(self, oracle):
        """Multiple comments in one string are all removed."""
        text = "<!-- first --> middle <!-- second --> end"
        result = oracle._strip_html_comments(text)
        assert "first" not in result
        assert "second" not in result
        assert "middle" in result
        assert "end" in result

    def test_text_without_comments_unchanged(self, oracle):
        """Text without comments is returned unchanged."""
        text = "no comments here"
        result = oracle._strip_html_comments(text)
        assert result == text

    def test_empty_string_returns_empty(self, oracle):
        """Empty string input returns empty string."""
        result = oracle._strip_html_comments("")
        assert result == ""

    def test_comment_at_start(self, oracle):
        """Comment at start of string is removed."""
        text = "<!-- start comment --> text follows"
        result = oracle._strip_html_comments(text)
        assert "start comment" not in result
        assert "text follows" in result

    def test_comment_at_end(self, oracle):
        """Comment at end of string is removed."""
        text = "text before <!-- end comment -->"
        result = oracle._strip_html_comments(text)
        assert "end comment" not in result
        assert "text before" in result

    def test_preserves_markdown_content(self, oracle):
        """Regular markdown content is preserved."""
        text = """## Minor Goal

Implement authentication.

## Success Criteria

- Users can log in
"""
        result = oracle._strip_html_comments(text)
        assert "## Minor Goal" in result
        assert "Implement authentication" in result
        assert "## Success Criteria" in result


class TestCommonTermsFinding:
    """Tests for the _find_common_terms helper."""

    def test_finds_underscore_terms(self, oracle):
        """Finds terms containing underscores."""
        text_a = "The user_authentication module handles login."
        text_b = "Implement user_authentication for the API."

        terms = oracle._find_common_terms(text_a, text_b)
        assert "user_authentication" in terms

    def test_ignores_short_words(self, oracle):
        """Ignores very short words."""
        text_a = "The API uses REST."
        text_b = "The API endpoint."

        terms = oracle._find_common_terms(text_a, text_b)
        # "api" and "the" should not be in results due to length/stopwords
        assert "the" not in terms

    def test_ignores_stopwords(self, oracle):
        """Ignores common stopwords."""
        text_a = "This should have functionality."
        text_b = "This should work correctly."

        terms = oracle._find_common_terms(text_a, text_b)
        assert "should" not in terms
        assert "this" not in terms


class TestConflictPersistence:
    """Tests for conflict analysis persistence in StateStore."""

    def test_save_and_retrieve_analysis(self, store):
        """Analysis can be saved and retrieved."""
        now = datetime.now(timezone.utc)
        analysis = ConflictAnalysis(
            chunk_a="chunk_a",
            chunk_b="chunk_b",
            verdict=ConflictVerdict.SERIALIZE,
            confidence=0.85,
            reason="File overlap detected",
            analysis_stage=AnalysisStage.PLAN,
            overlapping_files=["src/shared.py"],
            overlapping_symbols=[],
            created_at=now,
        )

        store.save_conflict_analysis(analysis)
        retrieved = store.get_conflict_analysis("chunk_a", "chunk_b")

        assert retrieved is not None
        assert retrieved.verdict == ConflictVerdict.SERIALIZE
        assert retrieved.confidence == 0.85
        assert "src/shared.py" in retrieved.overlapping_files

    def test_list_conflicts_for_chunk(self, store):
        """Can list all conflicts involving a specific chunk."""
        now = datetime.now(timezone.utc)

        # Create multiple analyses
        for other in ["b", "c", "d"]:
            analysis = ConflictAnalysis(
                chunk_a="chunk_a",
                chunk_b=f"chunk_{other}",
                verdict=ConflictVerdict.INDEPENDENT,
                confidence=0.9,
                reason="Test",
                analysis_stage=AnalysisStage.GOAL,
                created_at=now,
            )
            store.save_conflict_analysis(analysis)

        conflicts = store.list_conflicts_for_chunk("chunk_a")
        assert len(conflicts) == 3

    def test_clear_conflicts_for_chunk(self, store):
        """Can clear conflicts when chunk advances."""
        now = datetime.now(timezone.utc)

        analysis = ConflictAnalysis(
            chunk_a="chunk_a",
            chunk_b="chunk_b",
            verdict=ConflictVerdict.ASK_OPERATOR,
            confidence=0.5,
            reason="Test",
            analysis_stage=AnalysisStage.GOAL,
            created_at=now,
        )
        store.save_conflict_analysis(analysis)

        deleted = store.clear_conflicts_for_chunk("chunk_a")
        assert deleted == 1

        # Should be gone
        retrieved = store.get_conflict_analysis("chunk_a", "chunk_b")
        assert retrieved is None

    def test_list_all_conflicts_with_verdict_filter(self, store):
        """Can filter conflicts by verdict."""
        now = datetime.now(timezone.utc)

        # Create mix of verdicts
        for verdict, chunk in [
            (ConflictVerdict.INDEPENDENT, "b"),
            (ConflictVerdict.SERIALIZE, "c"),
            (ConflictVerdict.ASK_OPERATOR, "d"),
        ]:
            analysis = ConflictAnalysis(
                chunk_a="chunk_a",
                chunk_b=f"chunk_{chunk}",
                verdict=verdict,
                confidence=0.8,
                reason="Test",
                analysis_stage=AnalysisStage.PLAN,
                created_at=now,
            )
            store.save_conflict_analysis(analysis)

        # Filter to only ASK_OPERATOR
        conflicts = store.list_all_conflicts(verdict=ConflictVerdict.ASK_OPERATOR)
        assert len(conflicts) == 1
        assert conflicts[0].verdict == ConflictVerdict.ASK_OPERATOR
