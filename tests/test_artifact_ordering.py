"""Tests for artifact ordering system.

# Chunk: docs/chunks/artifact_ordering_index - Causal ordering infrastructure
# Chunk: docs/chunks/artifact_index_no_git - Directory-based staleness detection
"""

from pathlib import Path

import pytest

from artifact_ordering import (
    ArtifactIndex,
    ArtifactType,
    _enumerate_artifacts,
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


class TestEnumerateArtifacts:
    """Tests for _enumerate_artifacts function."""

    def test_enumerate_artifacts_returns_set_of_directories(self, tmp_path):
        """Returns set of artifact directory names."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        (chunks_dir / "0001-first").mkdir()
        (chunks_dir / "0001-first" / "GOAL.md").write_text("# First")

        (chunks_dir / "0002-second").mkdir()
        (chunks_dir / "0002-second" / "GOAL.md").write_text("# Second")

        result = _enumerate_artifacts(chunks_dir, ArtifactType.CHUNK)

        assert result == {"0001-first", "0002-second"}

    def test_enumerate_artifacts_empty_dir(self, tmp_path):
        """Returns empty set for empty directory."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        result = _enumerate_artifacts(chunks_dir, ArtifactType.CHUNK)

        assert result == set()

    def test_enumerate_artifacts_nonexistent_dir(self, tmp_path):
        """Returns empty set for nonexistent directory."""
        chunks_dir = tmp_path / "docs" / "chunks"  # Not created

        result = _enumerate_artifacts(chunks_dir, ArtifactType.CHUNK)

        assert result == set()

    def test_enumerate_artifacts_ignores_missing_main_file(self, tmp_path):
        """Ignores directories without the required main file."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Valid chunk
        (chunks_dir / "0001-first").mkdir()
        (chunks_dir / "0001-first" / "GOAL.md").write_text("# First")

        # Invalid chunk (no GOAL.md)
        (chunks_dir / "0002-incomplete").mkdir()

        result = _enumerate_artifacts(chunks_dir, ArtifactType.CHUNK)

        assert result == {"0001-first"}

    def test_enumerate_artifacts_handles_overview_md(self, tmp_path):
        """Uses OVERVIEW.md for narratives/subsystems."""
        narratives_dir = tmp_path / "docs" / "narratives"
        narratives_dir.mkdir(parents=True)

        (narratives_dir / "0001-test").mkdir()
        (narratives_dir / "0001-test" / "OVERVIEW.md").write_text("# Narrative")

        result = _enumerate_artifacts(narratives_dir, ArtifactType.NARRATIVE)

        assert result == {"0001-test"}


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


def _create_chunk(
    chunks_dir: Path,
    name: str,
    created_after: list[str] | None = None,
    status: str = "IMPLEMENTING",
):
    """Helper to create a chunk directory with GOAL.md frontmatter."""
    chunk_dir = chunks_dir / name
    chunk_dir.mkdir(parents=True, exist_ok=True)

    ca_str = "[]"
    if created_after:
        ca_items = "\n".join(f'  - "{ca}"' for ca in created_after)
        ca_str = f"\n{ca_items}"

    (chunk_dir / "GOAL.md").write_text(
        f"""---
status: {status}
created_after: {ca_str}
---
# Chunk Goal for {name}
"""
    )


class TestArtifactIndex:
    """Tests for ArtifactIndex class."""

    def test_get_ordered_empty_dir(self, tmp_path):
        """get_ordered returns empty list when no artifacts exist."""
        (tmp_path / "docs" / "chunks").mkdir(parents=True)
        index = ArtifactIndex(tmp_path)

        result = index.get_ordered(ArtifactType.CHUNK)

        assert result == []

    def test_get_ordered_no_created_after_falls_back_to_sequence(self, tmp_path):
        """When created_after is empty, falls back to sequence number order."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Create chunks without created_after (out of order)
        _create_chunk(chunks_dir, "0003-third")
        _create_chunk(chunks_dir, "0001-first")
        _create_chunk(chunks_dir, "0002-second")

        index = ArtifactIndex(tmp_path)
        result = index.get_ordered(ArtifactType.CHUNK)

        # Should be in sequence order
        assert result == ["0001-first", "0002-second", "0003-third"]

    def test_get_ordered_with_created_after_uses_causal_order(self, tmp_path):
        """When created_after is populated, uses topological order."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-first")
        _create_chunk(chunks_dir, "0002-second", created_after=["0001-first"])
        _create_chunk(chunks_dir, "0003-third", created_after=["0002-second"])

        index = ArtifactIndex(tmp_path)
        result = index.get_ordered(ArtifactType.CHUNK)

        assert result == ["0001-first", "0002-second", "0003-third"]

    def test_get_ordered_multi_parent_dag(self, tmp_path):
        """Multi-parent DAG is correctly ordered."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-a")
        _create_chunk(chunks_dir, "0002-b")
        _create_chunk(chunks_dir, "0003-merge", created_after=["0001-a", "0002-b"])

        index = ArtifactIndex(tmp_path)
        result = index.get_ordered(ArtifactType.CHUNK)

        # 0003-merge must come after both 0001-a and 0002-b
        assert result.index("0003-merge") > result.index("0001-a")
        assert result.index("0003-merge") > result.index("0002-b")

    def test_find_tips_identifies_artifacts_with_no_dependents(self, tmp_path):
        """find_tips returns artifacts not referenced in any created_after."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-first")
        _create_chunk(chunks_dir, "0002-second", created_after=["0001-first"])
        _create_chunk(chunks_dir, "0003-third", created_after=["0002-second"])

        index = ArtifactIndex(tmp_path)
        tips = index.find_tips(ArtifactType.CHUNK)

        # Only 0003-third has no dependents
        assert tips == ["0003-third"]

    def test_find_tips_multiple_tips(self, tmp_path):
        """find_tips returns multiple tips when branches exist."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-root")
        _create_chunk(chunks_dir, "0002-branch_a", created_after=["0001-root"])
        _create_chunk(chunks_dir, "0003-branch_b", created_after=["0001-root"])

        index = ArtifactIndex(tmp_path)
        tips = index.find_tips(ArtifactType.CHUNK)

        # Both branches are tips
        assert sorted(tips) == ["0002-branch_a", "0003-branch_b"]

    def test_find_tips_empty_returns_all(self, tmp_path):
        """When no created_after is set, all artifacts are tips."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-first")
        _create_chunk(chunks_dir, "0002-second")

        index = ArtifactIndex(tmp_path)
        tips = index.find_tips(ArtifactType.CHUNK)

        assert sorted(tips) == ["0001-first", "0002-second"]

    def test_index_file_created_on_query(self, tmp_path):
        """Index file is created when get_ordered is called."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)
        _create_chunk(chunks_dir, "0001-first")

        index = ArtifactIndex(tmp_path)
        index_file = tmp_path / ".artifact-order.json"

        assert not index_file.exists()
        index.get_ordered(ArtifactType.CHUNK)
        assert index_file.exists()

    def test_index_uses_cache_when_fresh(self, tmp_path):
        """Subsequent queries use cached index when artifacts unchanged."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)
        _create_chunk(chunks_dir, "0001-first")

        index = ArtifactIndex(tmp_path)

        # First query builds index
        result1 = index.get_ordered(ArtifactType.CHUNK)

        # Modify index file timestamp but not content (simulating cache use)
        index_file = tmp_path / ".artifact-order.json"
        initial_content = index_file.read_text()

        # Second query should return same result
        result2 = index.get_ordered(ArtifactType.CHUNK)

        assert result1 == result2
        # Index file should still have same content
        assert index_file.read_text() == initial_content

    def test_index_rebuilds_on_new_artifact(self, tmp_path):
        """Index rebuilds when a new artifact is added."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)
        _create_chunk(chunks_dir, "0001-first")

        index = ArtifactIndex(tmp_path)
        result1 = index.get_ordered(ArtifactType.CHUNK)
        assert result1 == ["0001-first"]

        # Add a new chunk
        _create_chunk(chunks_dir, "0002-second", created_after=["0001-first"])

        result2 = index.get_ordered(ArtifactType.CHUNK)
        assert result2 == ["0001-first", "0002-second"]

    def test_rebuild_forces_index_regeneration(self, tmp_path):
        """rebuild() forces index to be regenerated."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)
        _create_chunk(chunks_dir, "0001-first")

        index = ArtifactIndex(tmp_path)
        index.get_ordered(ArtifactType.CHUNK)

        index_file = tmp_path / ".artifact-order.json"
        initial_content = index_file.read_text()

        # Force rebuild
        index.rebuild(ArtifactType.CHUNK)

        # Index file should be regenerated (content may be same but was rebuilt)
        assert index_file.exists()

    def test_handles_narratives(self, tmp_path):
        """Works with narratives (OVERVIEW.md instead of GOAL.md)."""
        narratives_dir = tmp_path / "docs" / "narratives"
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

        index = ArtifactIndex(tmp_path)
        result = index.get_ordered(ArtifactType.NARRATIVE)

        assert result == ["0001-test"]

    def test_handles_missing_docs_directory(self, tmp_path):
        """Returns empty list when docs directory doesn't exist."""
        index = ArtifactIndex(tmp_path)

        result = index.get_ordered(ArtifactType.CHUNK)

        assert result == []


class TestArtifactIndexIntegration:
    """Integration tests that validate the full flow."""

    def test_full_lifecycle_with_multiple_chunks(self, tmp_path):
        """Test full lifecycle: create, query, modify, rebuild."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Create initial chunks with dependencies
        _create_chunk(chunks_dir, "0001-foundation")
        _create_chunk(chunks_dir, "0002-core", created_after=["0001-foundation"])
        _create_chunk(chunks_dir, "0003-feature_a", created_after=["0002-core"])
        _create_chunk(chunks_dir, "0004-feature_b", created_after=["0002-core"])

        index = ArtifactIndex(tmp_path)

        # Query ordered list
        ordered = index.get_ordered(ArtifactType.CHUNK)
        assert ordered.index("0001-foundation") < ordered.index("0002-core")
        assert ordered.index("0002-core") < ordered.index("0003-feature_a")
        assert ordered.index("0002-core") < ordered.index("0004-feature_b")

        # Query tips
        tips = index.find_tips(ArtifactType.CHUNK)
        assert sorted(tips) == ["0003-feature_a", "0004-feature_b"]

        # Verify index file was created
        index_file = tmp_path / ".artifact-order.json"
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

    def test_index_file_format(self, tmp_path):
        """Verify the index file has the expected JSON structure."""
        import json

        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-test")

        index = ArtifactIndex(tmp_path)
        index.get_ordered(ArtifactType.CHUNK)

        index_file = tmp_path / ".artifact-order.json"
        data = json.loads(index_file.read_text())

        # Verify structure
        assert "chunk" in data
        chunk_data = data["chunk"]
        assert "ordered" in chunk_data
        assert "tips" in chunk_data
        assert "directories" in chunk_data
        assert "version" in chunk_data

        assert chunk_data["ordered"] == ["0001-test"]
        assert chunk_data["tips"] == ["0001-test"]
        assert chunk_data["directories"] == ["0001-test"]
        assert chunk_data["version"] == 3

    def test_separate_type_indexes(self, tmp_path):
        """Different artifact types have separate index entries."""
        chunks_dir = tmp_path / "docs" / "chunks"
        narratives_dir = tmp_path / "docs" / "narratives"
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

        index = ArtifactIndex(tmp_path)

        chunks = index.get_ordered(ArtifactType.CHUNK)
        narratives = index.get_ordered(ArtifactType.NARRATIVE)

        assert chunks == ["0001-chunk"]
        assert narratives == ["0001-narrative"]

    def test_deleted_artifact_triggers_rebuild(self, tmp_path):
        """Deleting an artifact triggers index rebuild."""
        import shutil

        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-first")
        _create_chunk(chunks_dir, "0002-second")

        index = ArtifactIndex(tmp_path)
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

    def test_cold_rebuild_under_100ms_for_40_artifacts(self, tmp_path):
        """Cold rebuild completes in <100ms for ~40 artifacts."""
        import time

        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Create 40 chunks (current project scale)
        for i in range(40):
            # Create a dependency chain to make it interesting
            created_after = [f"{i - 1:04d}-chunk"] if i > 0 else None
            _create_chunk(chunks_dir, f"{i:04d}-chunk", created_after=created_after)

        index = ArtifactIndex(tmp_path)

        # Time cold rebuild
        start = time.perf_counter()
        index.rebuild(ArtifactType.CHUNK)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Allow generous headroom for CI environments
        # Goal says <100ms, we allow 200ms for test stability
        assert elapsed_ms < 200, f"Cold rebuild took {elapsed_ms:.1f}ms, expected <200ms"

    def test_warm_query_under_20ms(self, tmp_path):
        """Warm query (load + staleness check) completes in <20ms."""
        import time

        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Create 40 chunks
        for i in range(40):
            _create_chunk(chunks_dir, f"{i:04d}-chunk")

        index = ArtifactIndex(tmp_path)

        # Build index first (cold)
        index.get_ordered(ArtifactType.CHUNK)

        # Create fresh index instance to simulate warm query
        index2 = ArtifactIndex(tmp_path)

        # Time warm query
        start = time.perf_counter()
        index2.get_ordered(ArtifactType.CHUNK)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Allow generous headroom for CI environments
        # Goal says <20ms, we allow 50ms for test stability
        assert elapsed_ms < 50, f"Warm query took {elapsed_ms:.1f}ms, expected <50ms"


# Chunk: docs/chunks/artifact_list_ordering - Backward compatibility tests
class TestBackwardCompatibility:
    """Tests for backward compatibility with mixed created_after scenarios.

    These tests verify that artifacts without created_after fields (pre-migration)
    work correctly alongside artifacts that have created_after populated.
    """

    def test_mixed_created_after_preserves_sequence_fallback(self, tmp_path):
        """Artifacts without created_after fall back to sequence order.

        This simulates the current repository state where chunks 0001-0036
        don't have created_after, and newer chunks do.
        """
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Legacy chunks without created_after (simulating 0001-0036)
        _create_chunk(chunks_dir, "0001-legacy_a")
        _create_chunk(chunks_dir, "0002-legacy_b")
        _create_chunk(chunks_dir, "0003-legacy_c")

        # New chunks with created_after (simulating 0037+)
        _create_chunk(chunks_dir, "0037-new_a", created_after=["0003-legacy_c"])
        _create_chunk(chunks_dir, "0038-new_b", created_after=["0037-new_a"])
        _create_chunk(chunks_dir, "0039-new_c", created_after=["0038-new_b"])

        index = ArtifactIndex(tmp_path)
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

    def test_mixed_with_branching_dependencies(self, tmp_path):
        """Mixed scenario with branching in new chunks."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Legacy chunks (roots)
        _create_chunk(chunks_dir, "0001-foundation")
        _create_chunk(chunks_dir, "0002-core")

        # New chunks with branches
        _create_chunk(chunks_dir, "0003-feature_a", created_after=["0002-core"])
        _create_chunk(chunks_dir, "0004-feature_b", created_after=["0002-core"])
        _create_chunk(chunks_dir, "0005-merge", created_after=["0003-feature_a", "0004-feature_b"])

        index = ArtifactIndex(tmp_path)
        ordered = index.get_ordered(ArtifactType.CHUNK)

        # Verify dependencies are respected
        assert ordered.index("0002-core") < ordered.index("0003-feature_a")
        assert ordered.index("0002-core") < ordered.index("0004-feature_b")
        assert ordered.index("0003-feature_a") < ordered.index("0005-merge")
        assert ordered.index("0004-feature_b") < ordered.index("0005-merge")

    def test_tips_with_mixed_created_after(self, tmp_path):
        """Tips are correctly identified with mixed created_after."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Legacy chunks - all are tips since none reference them
        _create_chunk(chunks_dir, "0001-legacy_a")
        _create_chunk(chunks_dir, "0002-legacy_b")

        # New chunk that references one legacy chunk
        _create_chunk(chunks_dir, "0003-new_a", created_after=["0001-legacy_a"])

        index = ArtifactIndex(tmp_path)
        tips = sorted(index.find_tips(ArtifactType.CHUNK))

        # 0002-legacy_b is a tip (no one references it)
        # 0003-new_a is a tip (no one references it)
        # 0001-legacy_a is NOT a tip (0003-new_a references it)
        assert tips == ["0002-legacy_b", "0003-new_a"]


# Chunk: docs/chunks/artifact_index_no_git - Non-git operation tests
class TestNonGitOperation:
    """Tests that verify ArtifactIndex works without git.

    These tests explicitly verify that the index works in directories
    that are not git repositories, validating the git-free design.
    """

    def test_works_in_non_git_directory(self, tmp_path):
        """ArtifactIndex works in a directory that is not a git repo."""
        # tmp_path is NOT a git repo - this is the key assertion
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-first")
        _create_chunk(chunks_dir, "0002-second", created_after=["0001-first"])

        index = ArtifactIndex(tmp_path)
        ordered = index.get_ordered(ArtifactType.CHUNK)

        assert ordered == ["0001-first", "0002-second"]

    def test_detects_new_artifact_without_git(self, tmp_path):
        """New artifact is detected and index rebuilds without git."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-first")

        index = ArtifactIndex(tmp_path)
        result1 = index.get_ordered(ArtifactType.CHUNK)
        assert result1 == ["0001-first"]

        # Add a new artifact
        _create_chunk(chunks_dir, "0002-second", created_after=["0001-first"])

        # Index should detect the new artifact and rebuild
        result2 = index.get_ordered(ArtifactType.CHUNK)
        assert result2 == ["0001-first", "0002-second"]

    def test_detects_deleted_artifact_without_git(self, tmp_path):
        """Deleted artifact is detected and index rebuilds without git."""
        import shutil

        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-first")
        _create_chunk(chunks_dir, "0002-second")

        index = ArtifactIndex(tmp_path)
        result1 = index.get_ordered(ArtifactType.CHUNK)
        assert len(result1) == 2

        # Delete an artifact
        shutil.rmtree(chunks_dir / "0002-second")

        # Index should detect the deletion and rebuild
        result2 = index.get_ordered(ArtifactType.CHUNK)
        assert result2 == ["0001-first"]

    def test_content_changes_do_not_trigger_rebuild(self, tmp_path):
        """Content changes don't trigger rebuild since created_after is immutable."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-first")

        index = ArtifactIndex(tmp_path)
        index.get_ordered(ArtifactType.CHUNK)

        # Get the index file content
        index_file = tmp_path / ".artifact-order.json"
        initial_content = index_file.read_text()

        # Modify the artifact content (but keep same directory)
        (chunks_dir / "0001-first" / "GOAL.md").write_text(
            """---
status: ACTIVE
created_after: []
---
# Modified content here
"""
        )

        # Query again - should use cached index (no rebuild)
        index.get_ordered(ArtifactType.CHUNK)

        # Index file should be unchanged
        assert index_file.read_text() == initial_content


# Chunk: docs/chunks/ordering_active_only - Status-aware tip filtering tests
class TestStatusFilteredTips:
    """Tests for status-aware tip filtering.

    Tips should only include artifacts with "active" statuses:
    - Chunks: ACTIVE or IMPLEMENTING (excludes FUTURE, SUPERSEDED, HISTORICAL)
    - Narratives: ACTIVE (excludes DRAFTING, COMPLETED)
    - Investigations: No filtering (all statuses)
    - Subsystems: No filtering (all statuses)
    """

    def test_find_tips_excludes_future_chunks(self, tmp_path):
        """FUTURE chunks are not returned as tips."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # IMPLEMENTING chunk is the "active" work
        _create_chunk(chunks_dir, "0001-active", status="IMPLEMENTING")

        # FUTURE chunks should be excluded from tips
        _create_chunk(
            chunks_dir, "0002-future_a", created_after=["0001-active"], status="FUTURE"
        )
        _create_chunk(
            chunks_dir, "0002-future_b", created_after=["0001-active"], status="FUTURE"
        )

        index = ArtifactIndex(tmp_path)
        tips = index.find_tips(ArtifactType.CHUNK)

        # Only the IMPLEMENTING chunk should be a tip
        assert tips == ["0001-active"]

    def test_find_tips_includes_active_and_implementing_chunks(self, tmp_path):
        """ACTIVE and IMPLEMENTING chunks are both valid tips."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-active", status="ACTIVE")
        _create_chunk(chunks_dir, "0002-implementing", status="IMPLEMENTING")

        index = ArtifactIndex(tmp_path)
        tips = sorted(index.find_tips(ArtifactType.CHUNK))

        # Both should be tips (neither references the other)
        assert tips == ["0001-active", "0002-implementing"]

    def test_find_tips_excludes_superseded_chunks(self, tmp_path):
        """SUPERSEDED chunks are not returned as tips."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-first", status="ACTIVE")
        _create_chunk(
            chunks_dir, "0002-superseded", created_after=["0001-first"], status="SUPERSEDED"
        )
        _create_chunk(
            chunks_dir, "0003-current", created_after=["0001-first"], status="IMPLEMENTING"
        )

        index = ArtifactIndex(tmp_path)
        tips = index.find_tips(ArtifactType.CHUNK)

        # Only IMPLEMENTING chunk is a tip, SUPERSEDED is excluded
        assert tips == ["0003-current"]

    def test_find_tips_excludes_historical_chunks(self, tmp_path):
        """HISTORICAL chunks are not returned as tips."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-old", status="HISTORICAL")
        _create_chunk(
            chunks_dir, "0002-current", created_after=["0001-old"], status="ACTIVE"
        )

        index = ArtifactIndex(tmp_path)
        tips = index.find_tips(ArtifactType.CHUNK)

        # HISTORICAL chunk is excluded from tips
        # Note: 0001-old is referenced by 0002-current, so it wouldn't be a tip anyway
        # But if it wasn't referenced, it still shouldn't be a tip
        assert tips == ["0002-current"]

    def test_multiple_future_chunks_get_same_created_after(self, tmp_path):
        """Multiple FUTURE chunks created in sequence all point to the same tip.

        When creating multiple FUTURE chunks, they should all have the same
        created_after (the IMPLEMENTING tip), not form a chain among themselves.
        """
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Current work
        _create_chunk(chunks_dir, "0001-implementing", status="IMPLEMENTING")

        # Simulate creating FUTURE chunks that would get tips
        # If FUTURE chunks were included in tips, 0002 would be tip after first create
        # and 0003 would point to 0002. We want both to point to 0001.
        _create_chunk(
            chunks_dir, "0002-future_a", created_after=["0001-implementing"], status="FUTURE"
        )
        _create_chunk(
            chunks_dir, "0003-future_b", created_after=["0001-implementing"], status="FUTURE"
        )

        index = ArtifactIndex(tmp_path)
        tips = index.find_tips(ArtifactType.CHUNK)

        # The IMPLEMENTING chunk is the only tip
        # FUTURE chunks don't become tips themselves
        assert tips == ["0001-implementing"]

    def test_find_tips_excludes_drafting_narratives(self, tmp_path):
        """DRAFTING narratives are not returned as tips."""
        narratives_dir = tmp_path / "docs" / "narratives"
        narratives_dir.mkdir(parents=True)

        # Create ACTIVE narrative
        (narratives_dir / "0001-active").mkdir()
        (narratives_dir / "0001-active" / "OVERVIEW.md").write_text(
            """---
status: ACTIVE
created_after: []
---
# Active Narrative
"""
        )

        # Create DRAFTING narrative (should be excluded from tips)
        (narratives_dir / "0002-drafting").mkdir()
        (narratives_dir / "0002-drafting" / "OVERVIEW.md").write_text(
            """---
status: DRAFTING
created_after: ["0001-active"]
---
# Drafting Narrative
"""
        )

        index = ArtifactIndex(tmp_path)
        tips = index.find_tips(ArtifactType.NARRATIVE)

        # Only ACTIVE narrative is a tip
        assert tips == ["0001-active"]

    def test_find_tips_excludes_completed_narratives(self, tmp_path):
        """COMPLETED narratives are not returned as tips."""
        narratives_dir = tmp_path / "docs" / "narratives"
        narratives_dir.mkdir(parents=True)

        # Create COMPLETED narrative
        (narratives_dir / "0001-completed").mkdir()
        (narratives_dir / "0001-completed" / "OVERVIEW.md").write_text(
            """---
status: COMPLETED
created_after: []
---
# Completed Narrative
"""
        )

        # Create ACTIVE narrative
        (narratives_dir / "0002-active").mkdir()
        (narratives_dir / "0002-active" / "OVERVIEW.md").write_text(
            """---
status: ACTIVE
created_after: ["0001-completed"]
---
# Active Narrative
"""
        )

        index = ArtifactIndex(tmp_path)
        tips = index.find_tips(ArtifactType.NARRATIVE)

        # Only ACTIVE narrative is a tip
        assert tips == ["0002-active"]

    def test_find_tips_includes_all_investigation_statuses(self, tmp_path):
        """Investigations are not filtered by status - all are potential tips."""
        investigations_dir = tmp_path / "docs" / "investigations"
        investigations_dir.mkdir(parents=True)

        # Create investigations with various statuses
        for name, status in [
            ("0001-ongoing", "ONGOING"),
            ("0002-solved", "SOLVED"),
            ("0003-noted", "NOTED"),
            ("0004-deferred", "DEFERRED"),
        ]:
            (investigations_dir / name).mkdir()
            (investigations_dir / name / "OVERVIEW.md").write_text(
                f"""---
status: {status}
created_after: []
---
# Investigation
"""
            )

        index = ArtifactIndex(tmp_path)
        tips = sorted(index.find_tips(ArtifactType.INVESTIGATION))

        # All investigations are tips (no status filtering)
        assert tips == ["0001-ongoing", "0002-solved", "0003-noted", "0004-deferred"]

    def test_find_tips_includes_all_subsystem_statuses(self, tmp_path):
        """Subsystems are not filtered by status - all are potential tips."""
        subsystems_dir = tmp_path / "docs" / "subsystems"
        subsystems_dir.mkdir(parents=True)

        # Create subsystems with various statuses
        for name, status in [
            ("0001-discovering", "DISCOVERING"),
            ("0002-documented", "DOCUMENTED"),
            ("0003-refactoring", "REFACTORING"),
            ("0004-stable", "STABLE"),
        ]:
            (subsystems_dir / name).mkdir()
            (subsystems_dir / name / "OVERVIEW.md").write_text(
                f"""---
status: {status}
created_after: []
---
# Subsystem
"""
            )

        index = ArtifactIndex(tmp_path)
        tips = sorted(index.find_tips(ArtifactType.SUBSYSTEM))

        # All subsystems are tips (no status filtering)
        assert tips == ["0001-discovering", "0002-documented", "0003-refactoring", "0004-stable"]

    def test_find_tips_excludes_missing_status_chunks(self, tmp_path):
        """Chunks with missing status are excluded from tips."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Valid chunk
        _create_chunk(chunks_dir, "0001-valid", status="ACTIVE")

        # Chunk with no status field
        (chunks_dir / "0002-no_status").mkdir()
        (chunks_dir / "0002-no_status" / "GOAL.md").write_text(
            """---
created_after: []
---
# No status chunk
"""
        )

        index = ArtifactIndex(tmp_path)
        tips = index.find_tips(ArtifactType.CHUNK)

        # Only the ACTIVE chunk is a tip
        assert tips == ["0001-valid"]

    def test_ordered_list_unchanged_by_status_filtering(self, tmp_path):
        """Status filtering only affects tips, not the ordered list."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-active", status="ACTIVE")
        _create_chunk(
            chunks_dir, "0002-future", created_after=["0001-active"], status="FUTURE"
        )
        _create_chunk(
            chunks_dir, "0003-implementing", created_after=["0001-active"], status="IMPLEMENTING"
        )

        index = ArtifactIndex(tmp_path)

        # Ordered list should include ALL chunks
        ordered = index.get_ordered(ArtifactType.CHUNK)
        assert len(ordered) == 3
        assert "0002-future" in ordered

        # Tips should exclude FUTURE
        tips = sorted(index.find_tips(ArtifactType.CHUNK))
        assert tips == ["0003-implementing"]


# Chunk: docs/chunks/external_chunk_causal - External chunk ordering tests
class TestExternalChunkOrdering:
    """Tests for external chunk handling in causal ordering.

    External chunks are referenced via external.yaml (no GOAL.md) and should
    participate in local causal ordering with their own created_after field.
    """

    def _create_external_chunk(
        self,
        chunks_dir: Path,
        name: str,
        repo: str = "org/external-repo",
        chunk: str = "external_chunk_name",
        created_after: list[str] | None = None,
    ):
        """Helper to create an external chunk reference."""
        import yaml

        chunk_dir = chunks_dir / name
        chunk_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "repo": repo,
            "chunk": chunk,
            "track": "main",
            "pinned": "a" * 40,
        }
        if created_after:
            data["created_after"] = created_after

        with open(chunk_dir / "external.yaml", "w") as f:
            yaml.dump(data, f)

    def test_external_chunks_included_in_enumeration(self, tmp_path):
        """External chunks are included when enumerating artifacts."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Local chunk
        _create_chunk(chunks_dir, "0001-local")

        # External chunk reference
        self._create_external_chunk(chunks_dir, "0002-external")

        result = _enumerate_artifacts(chunks_dir, ArtifactType.CHUNK)

        assert result == {"0001-local", "0002-external"}

    def test_external_chunks_included_in_ordered_list(self, tmp_path):
        """External chunks appear in get_ordered() output."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-local")
        self._create_external_chunk(chunks_dir, "0002-external")

        index = ArtifactIndex(tmp_path)
        ordered = index.get_ordered(ArtifactType.CHUNK)

        assert "0001-local" in ordered
        assert "0002-external" in ordered
        assert len(ordered) == 2

    def test_external_chunk_can_be_tip(self, tmp_path):
        """External chunk with no dependents is identified as tip."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-local")
        self._create_external_chunk(
            chunks_dir, "0002-external", created_after=["0001-local"]
        )

        index = ArtifactIndex(tmp_path)
        tips = index.find_tips(ArtifactType.CHUNK)

        # External chunk is the tip (nothing references it)
        assert tips == ["0002-external"]

    def test_mixed_local_and_external_ordering(self, tmp_path):
        """Local and external chunks are correctly ordered together."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Create a chain: local_a -> external -> local_b
        _create_chunk(chunks_dir, "0001-local_a")
        self._create_external_chunk(
            chunks_dir, "0002-external", created_after=["0001-local_a"]
        )
        _create_chunk(chunks_dir, "0003-local_b", created_after=["0002-external"])

        index = ArtifactIndex(tmp_path)
        ordered = index.get_ordered(ArtifactType.CHUNK)

        # Verify ordering constraints
        assert ordered.index("0001-local_a") < ordered.index("0002-external")
        assert ordered.index("0002-external") < ordered.index("0003-local_b")

    def test_external_chunk_created_after_respected(self, tmp_path):
        """External chunk's created_after field is used for ordering."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-first")
        _create_chunk(chunks_dir, "0002-second")
        # External chunk depends on both local chunks
        self._create_external_chunk(
            chunks_dir, "0003-external", created_after=["0001-first", "0002-second"]
        )

        index = ArtifactIndex(tmp_path)
        ordered = index.get_ordered(ArtifactType.CHUNK)

        # External chunk must come after both locals
        assert ordered.index("0001-first") < ordered.index("0003-external")
        assert ordered.index("0002-second") < ordered.index("0003-external")

    def test_staleness_detects_external_yaml_addition(self, tmp_path):
        """Adding external chunks triggers index rebuild."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-local")

        index = ArtifactIndex(tmp_path)
        result1 = index.get_ordered(ArtifactType.CHUNK)
        assert result1 == ["0001-local"]

        # Add external chunk
        self._create_external_chunk(chunks_dir, "0002-external")

        result2 = index.get_ordered(ArtifactType.CHUNK)
        assert len(result2) == 2
        assert "0002-external" in result2

    def test_staleness_detects_external_yaml_removal(self, tmp_path):
        """Removing external chunks triggers index rebuild."""
        import shutil

        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-local")
        self._create_external_chunk(chunks_dir, "0002-external")

        index = ArtifactIndex(tmp_path)
        result1 = index.get_ordered(ArtifactType.CHUNK)
        assert len(result1) == 2

        # Remove external chunk
        shutil.rmtree(chunks_dir / "0002-external")

        result2 = index.get_ordered(ArtifactType.CHUNK)
        assert result2 == ["0001-local"]

    def test_external_chunks_always_tip_eligible(self, tmp_path):
        """External chunks are always eligible to be tips (EXTERNAL pseudo-status)."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # Active local chunk
        _create_chunk(chunks_dir, "0001-active", status="ACTIVE")
        # External chunk (no explicit status, uses EXTERNAL pseudo-status)
        self._create_external_chunk(
            chunks_dir, "0002-external", created_after=["0001-active"]
        )

        index = ArtifactIndex(tmp_path)
        tips = index.find_tips(ArtifactType.CHUNK)

        # External chunk is a tip (it's tip-eligible)
        assert tips == ["0002-external"]

    def test_external_chunk_referenced_excludes_from_tips(self, tmp_path):
        """External chunk referenced by another tip-eligible artifact is not a tip."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-active", status="ACTIVE")
        self._create_external_chunk(
            chunks_dir, "0002-external", created_after=["0001-active"]
        )
        # Local chunk references the external chunk
        _create_chunk(
            chunks_dir, "0003-current", created_after=["0002-external"], status="IMPLEMENTING"
        )

        index = ArtifactIndex(tmp_path)
        tips = index.find_tips(ArtifactType.CHUNK)

        # Only 0003-current is a tip
        assert tips == ["0003-current"]

    def test_external_chunk_without_created_after_is_root(self, tmp_path):
        """External chunk without created_after is a root in the causal graph."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # External chunk with no created_after (legacy or intentional root)
        self._create_external_chunk(chunks_dir, "external_root")
        _create_chunk(
            chunks_dir, "0001-local", created_after=["external_root"]
        )

        index = ArtifactIndex(tmp_path)
        ordered = index.get_ordered(ArtifactType.CHUNK)

        # External root comes first
        assert ordered.index("external_root") < ordered.index("0001-local")

    def test_external_chunk_in_get_ancestors(self, tmp_path):
        """get_ancestors correctly handles external chunks in the ancestry."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-root")
        self._create_external_chunk(
            chunks_dir, "0002-external", created_after=["0001-root"]
        )
        _create_chunk(chunks_dir, "0003-leaf", created_after=["0002-external"])

        index = ArtifactIndex(tmp_path)
        ancestors = index.get_ancestors(ArtifactType.CHUNK, "0003-leaf")

        # Both root and external chunk are ancestors
        assert ancestors == {"0001-root", "0002-external"}

    def test_multiple_external_chunks_ordering(self, tmp_path):
        """Multiple external chunks are correctly ordered."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        _create_chunk(chunks_dir, "0001-base")
        self._create_external_chunk(
            chunks_dir, "ext_a", created_after=["0001-base"]
        )
        self._create_external_chunk(
            chunks_dir, "ext_b", created_after=["0001-base"]
        )
        self._create_external_chunk(
            chunks_dir, "ext_merge", created_after=["ext_a", "ext_b"]
        )

        index = ArtifactIndex(tmp_path)
        ordered = index.get_ordered(ArtifactType.CHUNK)

        # Verify ordering
        assert ordered.index("0001-base") < ordered.index("ext_a")
        assert ordered.index("0001-base") < ordered.index("ext_b")
        assert ordered.index("ext_a") < ordered.index("ext_merge")
        assert ordered.index("ext_b") < ordered.index("ext_merge")

        # Tips should only include ext_merge
        tips = index.find_tips(ArtifactType.CHUNK)
        assert tips == ["ext_merge"]
