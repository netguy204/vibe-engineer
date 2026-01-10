"""Tests for artifact ordering system.

# Chunk: docs/chunks/0038-artifact_ordering_index - Causal ordering infrastructure
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

from artifact_ordering import (
    ArtifactIndex,
    ArtifactType,
    _get_git_hash,
    _get_all_artifact_hashes,
    _parse_created_after,
    _topological_sort_multi_parent,
)


class TestTopologicalSort:
    """Tests for the topological sort algorithm."""

    def test_empty_graph_returns_empty_list(self):
        """Empty dependency graph returns empty list."""
        deps: dict[str, list[str]] = {}
        result = _topological_sort_multi_parent(deps)
        assert result == []

    def test_single_node_no_parents(self):
        """Single node with no parents returns that node."""
        deps = {"0001-first": []}
        result = _topological_sort_multi_parent(deps)
        assert result == ["0001-first"]

    def test_linear_chain(self):
        """Linear chain A -> B -> C returns [A, B, C]."""
        deps = {
            "0001-a": [],
            "0002-b": ["0001-a"],
            "0003-c": ["0002-b"],
        }
        result = _topological_sort_multi_parent(deps)
        assert result == ["0001-a", "0002-b", "0003-c"]

    def test_multi_parent_dag(self):
        """Multi-parent DAG where C depends on both A and B."""
        deps = {
            "0001-a": [],
            "0002-b": [],
            "0003-c": ["0001-a", "0002-b"],
        }
        result = _topological_sort_multi_parent(deps)
        # C must come after both A and B
        c_index = result.index("0003-c")
        a_index = result.index("0001-a")
        b_index = result.index("0002-b")
        assert c_index > a_index
        assert c_index > b_index
        assert len(result) == 3

    def test_disconnected_components(self):
        """Disconnected components are all included in sorted order."""
        deps = {
            "0001-a": [],
            "0002-b": ["0001-a"],
            "0003-c": [],  # Disconnected from A-B chain
            "0004-d": ["0003-c"],
        }
        result = _topological_sort_multi_parent(deps)
        # Check ordering within chains
        assert result.index("0002-b") > result.index("0001-a")
        assert result.index("0004-d") > result.index("0003-c")
        assert len(result) == 4

    def test_deterministic_output(self):
        """Output is deterministic for same input."""
        deps = {
            "0003-c": [],
            "0001-a": [],
            "0002-b": [],
        }
        result1 = _topological_sort_multi_parent(deps)
        result2 = _topological_sort_multi_parent(deps)
        assert result1 == result2
        # Should be sorted alphabetically when at same level
        assert result1 == ["0001-a", "0002-b", "0003-c"]

    def test_missing_parent_handled_gracefully(self):
        """Reference to missing parent is handled gracefully.

        If a chunk references a parent that doesn't exist (e.g., deleted),
        the algorithm should skip the missing parent and include the child.
        """
        deps = {
            "0002-b": ["0001-missing"],  # Parent doesn't exist in deps
        }
        result = _topological_sort_multi_parent(deps)
        assert "0002-b" in result
        assert "0001-missing" not in result  # Missing parent not in output

    def test_complex_dag(self):
        """Complex DAG with multiple merge points."""
        #     A
        #    / \
        #   B   C
        #    \ / \
        #     D   E
        #      \ /
        #       F
        deps = {
            "0001-a": [],
            "0002-b": ["0001-a"],
            "0003-c": ["0001-a"],
            "0004-d": ["0002-b", "0003-c"],
            "0005-e": ["0003-c"],
            "0006-f": ["0004-d", "0005-e"],
        }
        result = _topological_sort_multi_parent(deps)

        # Verify all constraints
        assert result.index("0001-a") < result.index("0002-b")
        assert result.index("0001-a") < result.index("0003-c")
        assert result.index("0002-b") < result.index("0004-d")
        assert result.index("0003-c") < result.index("0004-d")
        assert result.index("0003-c") < result.index("0005-e")
        assert result.index("0004-d") < result.index("0006-f")
        assert result.index("0005-e") < result.index("0006-f")
        assert len(result) == 6


@pytest.fixture
def git_temp_dir():
    """Create a temporary directory with git initialized."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        subprocess.run(
            ["git", "init"],
            cwd=tmppath,
            capture_output=True,
            check=True,
        )
        # Configure git user for commits
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmppath,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmppath,
            capture_output=True,
            check=True,
        )
        yield tmppath


class TestGitHashUtilities:
    """Tests for git hash functions."""

    def test_get_git_hash_returns_hash_for_file(self, git_temp_dir):
        """get_git_hash returns a valid hash for a file in a git repo."""
        test_file = git_temp_dir / "test.txt"
        test_file.write_text("hello world")

        result = _get_git_hash(test_file)

        assert result is not None
        assert len(result) == 40  # Git hashes are 40 hex characters
        assert all(c in "0123456789abcdef" for c in result)

    def test_get_git_hash_returns_none_for_nonexistent_file(self, git_temp_dir):
        """get_git_hash returns None for nonexistent file."""
        nonexistent = git_temp_dir / "nonexistent.txt"

        result = _get_git_hash(nonexistent)

        assert result is None

    def test_get_git_hash_same_content_same_hash(self, git_temp_dir):
        """Same content produces same hash."""
        file1 = git_temp_dir / "file1.txt"
        file2 = git_temp_dir / "file2.txt"
        file1.write_text("same content")
        file2.write_text("same content")

        hash1 = _get_git_hash(file1)
        hash2 = _get_git_hash(file2)

        assert hash1 == hash2

    def test_get_git_hash_different_content_different_hash(self, git_temp_dir):
        """Different content produces different hash."""
        file1 = git_temp_dir / "file1.txt"
        file2 = git_temp_dir / "file2.txt"
        file1.write_text("content one")
        file2.write_text("content two")

        hash1 = _get_git_hash(file1)
        hash2 = _get_git_hash(file2)

        assert hash1 != hash2

    def test_get_all_artifact_hashes_batched(self, git_temp_dir):
        """get_all_artifact_hashes returns hashes for all artifacts."""
        # Create artifact structure
        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        (chunks_dir / "0001-first").mkdir()
        (chunks_dir / "0001-first" / "GOAL.md").write_text("# First chunk")

        (chunks_dir / "0002-second").mkdir()
        (chunks_dir / "0002-second" / "GOAL.md").write_text("# Second chunk")

        result = _get_all_artifact_hashes(chunks_dir, ArtifactType.CHUNK)

        assert len(result) == 2
        assert "0001-first" in result
        assert "0002-second" in result
        assert len(result["0001-first"]) == 40
        assert len(result["0002-second"]) == 40

    def test_get_all_artifact_hashes_empty_dir(self, git_temp_dir):
        """get_all_artifact_hashes returns empty dict for empty dir."""
        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        result = _get_all_artifact_hashes(chunks_dir, ArtifactType.CHUNK)

        assert result == {}

    def test_get_all_artifact_hashes_handles_overview_md(self, git_temp_dir):
        """get_all_artifact_hashes uses OVERVIEW.md for narratives/subsystems."""
        narratives_dir = git_temp_dir / "docs" / "narratives"
        narratives_dir.mkdir(parents=True)

        (narratives_dir / "0001-test").mkdir()
        (narratives_dir / "0001-test" / "OVERVIEW.md").write_text("# Narrative")

        result = _get_all_artifact_hashes(narratives_dir, ArtifactType.NARRATIVE)

        assert len(result) == 1
        assert "0001-test" in result


class TestFrontmatterParsing:
    """Tests for frontmatter parsing functions."""

    def test_parse_created_after_empty_list(self, tmp_path):
        """Empty created_after returns empty list."""
        goal = tmp_path / "GOAL.md"
        goal.write_text(
            """---
status: IMPLEMENTING
created_after: []
---
# Chunk Goal
"""
        )
        result = _parse_created_after(goal)
        assert result == []

    def test_parse_created_after_list(self, tmp_path):
        """List of short names is returned as-is."""
        goal = tmp_path / "GOAL.md"
        goal.write_text(
            """---
status: IMPLEMENTING
created_after:
  - "0001-first"
  - "0002-second"
---
# Chunk Goal
"""
        )
        result = _parse_created_after(goal)
        assert result == ["0001-first", "0002-second"]

    def test_parse_created_after_legacy_string(self, tmp_path):
        """Legacy single string is converted to list."""
        goal = tmp_path / "GOAL.md"
        goal.write_text(
            """---
status: IMPLEMENTING
created_after: "0001-first"
---
# Chunk Goal
"""
        )
        result = _parse_created_after(goal)
        assert result == ["0001-first"]

    def test_parse_created_after_missing_field(self, tmp_path):
        """Missing created_after field defaults to empty list."""
        goal = tmp_path / "GOAL.md"
        goal.write_text(
            """---
status: IMPLEMENTING
---
# Chunk Goal
"""
        )
        result = _parse_created_after(goal)
        assert result == []

    def test_parse_created_after_null_value(self, tmp_path):
        """Null created_after field returns empty list."""
        goal = tmp_path / "GOAL.md"
        goal.write_text(
            """---
status: IMPLEMENTING
created_after: null
---
# Chunk Goal
"""
        )
        result = _parse_created_after(goal)
        assert result == []

    def test_parse_created_after_no_frontmatter(self, tmp_path):
        """File without frontmatter returns empty list."""
        goal = tmp_path / "GOAL.md"
        goal.write_text("# Chunk Goal\n\nNo frontmatter here.")
        result = _parse_created_after(goal)
        assert result == []

    def test_parse_created_after_invalid_yaml(self, tmp_path):
        """Invalid YAML returns empty list."""
        goal = tmp_path / "GOAL.md"
        goal.write_text(
            """---
status: IMPLEMENTING
created_after: [unclosed bracket
---
# Chunk Goal
"""
        )
        result = _parse_created_after(goal)
        assert result == []

    def test_parse_created_after_nonexistent_file(self, tmp_path):
        """Nonexistent file returns empty list."""
        goal = tmp_path / "nonexistent.md"
        result = _parse_created_after(goal)
        assert result == []


def _create_chunk(chunks_dir: Path, name: str, created_after: list[str] | None = None):
    """Helper to create a chunk directory with GOAL.md frontmatter."""
    chunk_dir = chunks_dir / name
    chunk_dir.mkdir(parents=True, exist_ok=True)

    ca_str = "[]"
    if created_after:
        ca_items = "\n".join(f'  - "{ca}"' for ca in created_after)
        ca_str = f"\n{ca_items}"

    (chunk_dir / "GOAL.md").write_text(
        f"""---
status: IMPLEMENTING
created_after: {ca_str}
---
# Chunk Goal for {name}
"""
    )


class TestArtifactIndex:
    """Tests for ArtifactIndex class."""

    def test_get_ordered_empty_dir(self, git_temp_dir):
        """get_ordered returns empty list when no artifacts exist."""
        (git_temp_dir / "docs" / "chunks").mkdir(parents=True)
        index = ArtifactIndex(git_temp_dir)

        result = index.get_ordered(ArtifactType.CHUNK)

        assert result == []

    def test_get_ordered_no_created_after_falls_back_to_sequence(self, git_temp_dir):
        """When created_after is empty, falls back to sequence number order."""
        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Create chunks without created_after (out of order)
        _create_chunk(chunks_dir, "0003-third")
        _create_chunk(chunks_dir, "0001-first")
        _create_chunk(chunks_dir, "0002-second")

        index = ArtifactIndex(git_temp_dir)
        result = index.get_ordered(ArtifactType.CHUNK)

        # Should be in sequence order
        assert result == ["0001-first", "0002-second", "0003-third"]

    def test_get_ordered_with_created_after_uses_causal_order(self, git_temp_dir):
        """When created_after is populated, uses topological order."""
        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-first")
        _create_chunk(chunks_dir, "0002-second", created_after=["0001-first"])
        _create_chunk(chunks_dir, "0003-third", created_after=["0002-second"])

        index = ArtifactIndex(git_temp_dir)
        result = index.get_ordered(ArtifactType.CHUNK)

        assert result == ["0001-first", "0002-second", "0003-third"]

    def test_get_ordered_multi_parent_dag(self, git_temp_dir):
        """Multi-parent DAG is correctly ordered."""
        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-a")
        _create_chunk(chunks_dir, "0002-b")
        _create_chunk(chunks_dir, "0003-merge", created_after=["0001-a", "0002-b"])

        index = ArtifactIndex(git_temp_dir)
        result = index.get_ordered(ArtifactType.CHUNK)

        # 0003-merge must come after both 0001-a and 0002-b
        assert result.index("0003-merge") > result.index("0001-a")
        assert result.index("0003-merge") > result.index("0002-b")

    def test_find_tips_identifies_artifacts_with_no_dependents(self, git_temp_dir):
        """find_tips returns artifacts not referenced in any created_after."""
        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-first")
        _create_chunk(chunks_dir, "0002-second", created_after=["0001-first"])
        _create_chunk(chunks_dir, "0003-third", created_after=["0002-second"])

        index = ArtifactIndex(git_temp_dir)
        tips = index.find_tips(ArtifactType.CHUNK)

        # Only 0003-third has no dependents
        assert tips == ["0003-third"]

    def test_find_tips_multiple_tips(self, git_temp_dir):
        """find_tips returns multiple tips when branches exist."""
        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-root")
        _create_chunk(chunks_dir, "0002-branch_a", created_after=["0001-root"])
        _create_chunk(chunks_dir, "0003-branch_b", created_after=["0001-root"])

        index = ArtifactIndex(git_temp_dir)
        tips = index.find_tips(ArtifactType.CHUNK)

        # Both branches are tips
        assert sorted(tips) == ["0002-branch_a", "0003-branch_b"]

    def test_find_tips_empty_returns_all(self, git_temp_dir):
        """When no created_after is set, all artifacts are tips."""
        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-first")
        _create_chunk(chunks_dir, "0002-second")

        index = ArtifactIndex(git_temp_dir)
        tips = index.find_tips(ArtifactType.CHUNK)

        assert sorted(tips) == ["0001-first", "0002-second"]

    def test_index_file_created_on_query(self, git_temp_dir):
        """Index file is created when get_ordered is called."""
        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)
        _create_chunk(chunks_dir, "0001-first")

        index = ArtifactIndex(git_temp_dir)
        index_file = git_temp_dir / ".artifact-order.json"

        assert not index_file.exists()
        index.get_ordered(ArtifactType.CHUNK)
        assert index_file.exists()

    def test_index_uses_cache_when_fresh(self, git_temp_dir):
        """Subsequent queries use cached index when artifacts unchanged."""
        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)
        _create_chunk(chunks_dir, "0001-first")

        index = ArtifactIndex(git_temp_dir)

        # First query builds index
        result1 = index.get_ordered(ArtifactType.CHUNK)

        # Modify index file timestamp but not content (simulating cache use)
        index_file = git_temp_dir / ".artifact-order.json"
        initial_content = index_file.read_text()

        # Second query should return same result
        result2 = index.get_ordered(ArtifactType.CHUNK)

        assert result1 == result2
        # Index file should still have same content
        assert index_file.read_text() == initial_content

    def test_index_rebuilds_on_new_artifact(self, git_temp_dir):
        """Index rebuilds when a new artifact is added."""
        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)
        _create_chunk(chunks_dir, "0001-first")

        index = ArtifactIndex(git_temp_dir)
        result1 = index.get_ordered(ArtifactType.CHUNK)
        assert result1 == ["0001-first"]

        # Add a new chunk
        _create_chunk(chunks_dir, "0002-second", created_after=["0001-first"])

        result2 = index.get_ordered(ArtifactType.CHUNK)
        assert result2 == ["0001-first", "0002-second"]

    def test_index_rebuilds_on_modified_artifact(self, git_temp_dir):
        """Index rebuilds when an artifact is modified."""
        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)
        _create_chunk(chunks_dir, "0001-first")
        _create_chunk(chunks_dir, "0002-second")

        index = ArtifactIndex(git_temp_dir)
        tips1 = index.find_tips(ArtifactType.CHUNK)
        assert sorted(tips1) == ["0001-first", "0002-second"]

        # Modify second to depend on first
        _create_chunk(chunks_dir, "0002-second", created_after=["0001-first"])

        tips2 = index.find_tips(ArtifactType.CHUNK)
        assert tips2 == ["0002-second"]

    def test_rebuild_forces_index_regeneration(self, git_temp_dir):
        """rebuild() forces index to be regenerated."""
        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)
        _create_chunk(chunks_dir, "0001-first")

        index = ArtifactIndex(git_temp_dir)
        index.get_ordered(ArtifactType.CHUNK)

        index_file = git_temp_dir / ".artifact-order.json"
        initial_content = index_file.read_text()

        # Force rebuild
        index.rebuild(ArtifactType.CHUNK)

        # Index file should be regenerated (content may be same but was rebuilt)
        assert index_file.exists()

    def test_handles_narratives(self, git_temp_dir):
        """Works with narratives (OVERVIEW.md instead of GOAL.md)."""
        narratives_dir = git_temp_dir / "docs" / "narratives"
        narratives_dir.mkdir(parents=True)

        (narratives_dir / "0001-test").mkdir()
        (narratives_dir / "0001-test" / "OVERVIEW.md").write_text(
            """---
status: ACTIVE
created_after: []
---
# Narrative
"""
        )

        index = ArtifactIndex(git_temp_dir)
        result = index.get_ordered(ArtifactType.NARRATIVE)

        assert result == ["0001-test"]

    def test_handles_missing_docs_directory(self, git_temp_dir):
        """Returns empty list when docs directory doesn't exist."""
        index = ArtifactIndex(git_temp_dir)

        result = index.get_ordered(ArtifactType.CHUNK)

        assert result == []


class TestArtifactIndexIntegration:
    """Integration tests that validate the full flow."""

    def test_full_lifecycle_with_multiple_chunks(self, git_temp_dir):
        """Test full lifecycle: create, query, modify, rebuild."""
        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Create initial chunks with dependencies
        _create_chunk(chunks_dir, "0001-foundation")
        _create_chunk(chunks_dir, "0002-core", created_after=["0001-foundation"])
        _create_chunk(chunks_dir, "0003-feature_a", created_after=["0002-core"])
        _create_chunk(chunks_dir, "0004-feature_b", created_after=["0002-core"])

        index = ArtifactIndex(git_temp_dir)

        # Query ordered list
        ordered = index.get_ordered(ArtifactType.CHUNK)
        assert ordered.index("0001-foundation") < ordered.index("0002-core")
        assert ordered.index("0002-core") < ordered.index("0003-feature_a")
        assert ordered.index("0002-core") < ordered.index("0004-feature_b")

        # Query tips
        tips = index.find_tips(ArtifactType.CHUNK)
        assert sorted(tips) == ["0003-feature_a", "0004-feature_b"]

        # Verify index file was created
        index_file = git_temp_dir / ".artifact-order.json"
        assert index_file.exists()

        # Add a new chunk that merges the features
        _create_chunk(
            chunks_dir,
            "0005-merge",
            created_after=["0003-feature_a", "0004-feature_b"],
        )

        # Query again - should auto-rebuild
        ordered2 = index.get_ordered(ArtifactType.CHUNK)
        assert "0005-merge" in ordered2
        assert ordered2.index("0003-feature_a") < ordered2.index("0005-merge")
        assert ordered2.index("0004-feature_b") < ordered2.index("0005-merge")

        # Tips should now be just the merge
        tips2 = index.find_tips(ArtifactType.CHUNK)
        assert tips2 == ["0005-merge"]

    def test_index_file_format(self, git_temp_dir):
        """Verify the index file has the expected JSON structure."""
        import json

        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-test")

        index = ArtifactIndex(git_temp_dir)
        index.get_ordered(ArtifactType.CHUNK)

        index_file = git_temp_dir / ".artifact-order.json"
        data = json.loads(index_file.read_text())

        # Verify structure
        assert "chunk" in data
        chunk_data = data["chunk"]
        assert "ordered" in chunk_data
        assert "tips" in chunk_data
        assert "hashes" in chunk_data
        assert "version" in chunk_data

        assert chunk_data["ordered"] == ["0001-test"]
        assert chunk_data["tips"] == ["0001-test"]
        assert "0001-test" in chunk_data["hashes"]
        assert len(chunk_data["hashes"]["0001-test"]) == 40  # Git hash length

    def test_separate_type_indexes(self, git_temp_dir):
        """Different artifact types have separate index entries."""
        chunks_dir = git_temp_dir / "docs" / "chunks"
        narratives_dir = git_temp_dir / "docs" / "narratives"
        chunks_dir.mkdir(parents=True)
        narratives_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-chunk")

        (narratives_dir / "0001-narrative").mkdir()
        (narratives_dir / "0001-narrative" / "OVERVIEW.md").write_text(
            """---
status: ACTIVE
created_after: []
---
# Narrative
"""
        )

        index = ArtifactIndex(git_temp_dir)

        chunks = index.get_ordered(ArtifactType.CHUNK)
        narratives = index.get_ordered(ArtifactType.NARRATIVE)

        assert chunks == ["0001-chunk"]
        assert narratives == ["0001-narrative"]

    def test_deleted_artifact_triggers_rebuild(self, git_temp_dir):
        """Deleting an artifact triggers index rebuild."""
        import shutil

        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-first")
        _create_chunk(chunks_dir, "0002-second")

        index = ArtifactIndex(git_temp_dir)
        result1 = index.get_ordered(ArtifactType.CHUNK)
        assert len(result1) == 2

        # Delete a chunk
        shutil.rmtree(chunks_dir / "0002-second")

        # Query should rebuild and exclude deleted chunk
        result2 = index.get_ordered(ArtifactType.CHUNK)
        assert result2 == ["0001-first"]


class TestPerformance:
    """Performance validation tests.

    These tests verify performance criteria from the chunk goal.
    Tests are marked with approximate thresholds that may vary on slow machines.
    """

    def test_cold_rebuild_under_100ms_for_40_artifacts(self, git_temp_dir):
        """Cold rebuild completes in <100ms for ~40 artifacts."""
        import time

        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Create 40 chunks (current project scale)
        for i in range(40):
            # Create a dependency chain to make it interesting
            created_after = [f"{i - 1:04d}-chunk"] if i > 0 else None
            _create_chunk(chunks_dir, f"{i:04d}-chunk", created_after=created_after)

        index = ArtifactIndex(git_temp_dir)

        # Time cold rebuild
        start = time.perf_counter()
        index.rebuild(ArtifactType.CHUNK)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Allow generous headroom for CI environments
        # Goal says <100ms, we allow 200ms for test stability
        assert elapsed_ms < 200, f"Cold rebuild took {elapsed_ms:.1f}ms, expected <200ms"

    def test_warm_query_under_20ms(self, git_temp_dir):
        """Warm query (load + staleness check) completes in <20ms."""
        import time

        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Create 40 chunks
        for i in range(40):
            _create_chunk(chunks_dir, f"{i:04d}-chunk")

        index = ArtifactIndex(git_temp_dir)

        # Build index first (cold)
        index.get_ordered(ArtifactType.CHUNK)

        # Create fresh index instance to simulate warm query
        index2 = ArtifactIndex(git_temp_dir)

        # Time warm query
        start = time.perf_counter()
        index2.get_ordered(ArtifactType.CHUNK)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Allow generous headroom for CI environments
        # Goal says <20ms, we allow 50ms for test stability
        assert elapsed_ms < 50, f"Warm query took {elapsed_ms:.1f}ms, expected <50ms"


# Chunk: docs/chunks/0041-artifact_list_ordering - Backward compatibility tests
class TestBackwardCompatibility:
    """Tests for backward compatibility with mixed created_after scenarios.

    These tests verify that artifacts without created_after fields (pre-migration)
    work correctly alongside artifacts that have created_after populated.
    """

    def test_mixed_created_after_preserves_sequence_fallback(self, git_temp_dir):
        """Artifacts without created_after fall back to sequence order.

        This simulates the current repository state where chunks 0001-0036
        don't have created_after, and newer chunks do.
        """
        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Legacy chunks without created_after (simulating 0001-0036)
        _create_chunk(chunks_dir, "0001-legacy_a")
        _create_chunk(chunks_dir, "0002-legacy_b")
        _create_chunk(chunks_dir, "0003-legacy_c")

        # New chunks with created_after (simulating 0037+)
        _create_chunk(chunks_dir, "0037-new_a", created_after=["0003-legacy_c"])
        _create_chunk(chunks_dir, "0038-new_b", created_after=["0037-new_a"])
        _create_chunk(chunks_dir, "0039-new_c", created_after=["0038-new_b"])

        index = ArtifactIndex(git_temp_dir)
        ordered = index.get_ordered(ArtifactType.CHUNK)

        # All chunks should be present
        assert len(ordered) == 6

        # Legacy chunks should be in sequence order (they're all roots)
        legacy_chunks = [c for c in ordered if c.startswith("000")]
        assert legacy_chunks == ["0001-legacy_a", "0002-legacy_b", "0003-legacy_c"]

        # New chunks should come after legacy and in dependency order
        assert ordered.index("0003-legacy_c") < ordered.index("0037-new_a")
        assert ordered.index("0037-new_a") < ordered.index("0038-new_b")
        assert ordered.index("0038-new_b") < ordered.index("0039-new_c")

    def test_mixed_with_branching_dependencies(self, git_temp_dir):
        """Mixed scenario with branching in new chunks."""
        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Legacy chunks (roots)
        _create_chunk(chunks_dir, "0001-foundation")
        _create_chunk(chunks_dir, "0002-core")

        # New chunks with branches
        _create_chunk(chunks_dir, "0003-feature_a", created_after=["0002-core"])
        _create_chunk(chunks_dir, "0004-feature_b", created_after=["0002-core"])
        _create_chunk(chunks_dir, "0005-merge", created_after=["0003-feature_a", "0004-feature_b"])

        index = ArtifactIndex(git_temp_dir)
        ordered = index.get_ordered(ArtifactType.CHUNK)

        # Verify dependencies are respected
        assert ordered.index("0002-core") < ordered.index("0003-feature_a")
        assert ordered.index("0002-core") < ordered.index("0004-feature_b")
        assert ordered.index("0003-feature_a") < ordered.index("0005-merge")
        assert ordered.index("0004-feature_b") < ordered.index("0005-merge")

    def test_tips_with_mixed_created_after(self, git_temp_dir):
        """Tips are correctly identified with mixed created_after."""
        chunks_dir = git_temp_dir / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Legacy chunks - all are tips since none reference them
        _create_chunk(chunks_dir, "0001-legacy_a")
        _create_chunk(chunks_dir, "0002-legacy_b")

        # New chunk that references one legacy chunk
        _create_chunk(chunks_dir, "0003-new_a", created_after=["0001-legacy_a"])

        index = ArtifactIndex(git_temp_dir)
        tips = sorted(index.find_tips(ArtifactType.CHUNK))

        # 0002-legacy_b is a tip (no one references it)
        # 0003-new_a is a tip (no one references it)
        # 0001-legacy_a is NOT a tip (0003-new_a references it)
        assert tips == ["0002-legacy_b", "0003-new_a"]
