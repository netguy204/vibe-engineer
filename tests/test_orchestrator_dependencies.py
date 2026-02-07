# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_cli_extract - Unit tests for extracted dependency resolution functions
"""Tests for the orchestrator dependencies module.

Tests the extracted dependency resolution functions:
- topological_sort_chunks: Kahn's algorithm for dependency ordering
- read_chunk_dependencies: Reading depends_on from chunk frontmatter
- validate_external_dependencies: Validating external dependencies exist as work units

These tests focus on the pure domain logic, independent of CLI presentation.
"""

import pytest
from unittest.mock import MagicMock

from orchestrator.dependencies import (
    topological_sort_chunks,
    read_chunk_dependencies,
    validate_external_dependencies,
)


class TestTopologicalSortChunks:
    """Tests for topological_sort_chunks function."""

    def test_empty_list_returns_empty(self):
        """Empty input returns empty output."""
        result = topological_sort_chunks([], {})
        assert result == []

    def test_single_chunk_no_deps(self):
        """Single chunk with no dependencies returns that chunk."""
        result = topological_sort_chunks(["chunk_a"], {"chunk_a": []})
        assert result == ["chunk_a"]

    def test_single_chunk_unknown_deps(self):
        """Single chunk with None (unknown) dependencies returns that chunk."""
        result = topological_sort_chunks(["chunk_a"], {"chunk_a": None})
        assert result == ["chunk_a"]

    def test_linear_chain(self):
        """Linear dependency chain A -> B -> C returns correct order."""
        chunks = ["chunk_c", "chunk_b", "chunk_a"]  # Input in reverse order
        deps = {
            "chunk_a": [],
            "chunk_b": ["chunk_a"],
            "chunk_c": ["chunk_b"],
        }
        result = topological_sort_chunks(chunks, deps)
        # chunk_a must come before chunk_b, chunk_b before chunk_c
        assert result.index("chunk_a") < result.index("chunk_b")
        assert result.index("chunk_b") < result.index("chunk_c")

    def test_diamond_shape(self):
        """Diamond dependency shape is handled correctly.

        A is the root, B and C depend on A, D depends on both B and C.
        """
        chunks = ["chunk_d", "chunk_c", "chunk_b", "chunk_a"]
        deps = {
            "chunk_a": [],
            "chunk_b": ["chunk_a"],
            "chunk_c": ["chunk_a"],
            "chunk_d": ["chunk_b", "chunk_c"],
        }
        result = topological_sort_chunks(chunks, deps)
        # A must be first
        assert result[0] == "chunk_a"
        # D must be last
        assert result[-1] == "chunk_d"
        # B and C must be between A and D
        assert result.index("chunk_b") > result.index("chunk_a")
        assert result.index("chunk_c") > result.index("chunk_a")
        assert result.index("chunk_b") < result.index("chunk_d")
        assert result.index("chunk_c") < result.index("chunk_d")

    def test_cycle_detection_simple(self):
        """Detects simple A <-> B cycle."""
        chunks = ["chunk_a", "chunk_b"]
        deps = {
            "chunk_a": ["chunk_b"],
            "chunk_b": ["chunk_a"],
        }
        with pytest.raises(ValueError) as exc_info:
            topological_sort_chunks(chunks, deps)
        assert "cycle" in str(exc_info.value).lower()
        # Error message should mention the chunks involved
        assert "chunk_a" in str(exc_info.value) or "chunk_b" in str(exc_info.value)

    def test_cycle_detection_longer(self):
        """Detects longer A -> B -> C -> A cycle."""
        chunks = ["chunk_a", "chunk_b", "chunk_c"]
        deps = {
            "chunk_a": ["chunk_c"],
            "chunk_b": ["chunk_a"],
            "chunk_c": ["chunk_b"],
        }
        with pytest.raises(ValueError) as exc_info:
            topological_sort_chunks(chunks, deps)
        assert "cycle" in str(exc_info.value).lower()

    def test_none_dependencies_treated_as_empty(self):
        """None (unknown) dependencies are treated as empty for sorting."""
        chunks = ["chunk_a", "chunk_b"]
        deps = {
            "chunk_a": None,  # Unknown, treated as []
            "chunk_b": ["chunk_a"],  # Depends on chunk_a
        }
        result = topological_sort_chunks(chunks, deps)
        # chunk_a should come before chunk_b
        assert result.index("chunk_a") < result.index("chunk_b")

    def test_deterministic_ordering(self):
        """Chunks with equal in-degree are sorted alphabetically for determinism."""
        # Multiple independent chunks should be sorted alphabetically
        chunks = ["zebra", "apple", "mango"]
        deps = {
            "zebra": [],
            "apple": [],
            "mango": [],
        }
        result = topological_sort_chunks(chunks, deps)
        # All have in-degree 0, so should be alphabetically sorted
        assert result == ["apple", "mango", "zebra"]

    def test_external_deps_ignored(self):
        """Dependencies outside the batch are ignored for in-degree calculation."""
        chunks = ["chunk_a", "chunk_b"]
        deps = {
            "chunk_a": [],
            "chunk_b": ["external_chunk"],  # external_chunk not in batch
        }
        result = topological_sort_chunks(chunks, deps)
        # chunk_b has no in-batch dependencies, so order is alphabetical
        assert result == ["chunk_a", "chunk_b"]

    def test_missing_dependency_in_map(self):
        """Handles chunk not present in dependencies map."""
        chunks = ["chunk_a"]
        deps = {}  # No entry for chunk_a
        result = topological_sort_chunks(chunks, deps)
        # Treats missing as None (unknown), which means no deps
        assert result == ["chunk_a"]

    def test_multiple_roots(self):
        """Multiple independent roots are processed correctly."""
        chunks = ["root_a", "root_b", "dependent"]
        deps = {
            "root_a": [],
            "root_b": [],
            "dependent": ["root_a", "root_b"],
        }
        result = topological_sort_chunks(chunks, deps)
        # dependent must be last
        assert result[-1] == "dependent"
        # Both roots must come before dependent
        assert result.index("root_a") < result.index("dependent")
        assert result.index("root_b") < result.index("dependent")


class TestReadChunkDependencies:
    """Tests for read_chunk_dependencies function."""

    def test_reads_empty_deps_as_empty_list(self, tmp_path):
        """Chunk with depends_on: [] returns empty list."""
        chunks_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on: []
---

# test_chunk
"""
        )

        result = read_chunk_dependencies(tmp_path, ["test_chunk"])
        assert result == {"test_chunk": []}

    def test_reads_populated_deps(self, tmp_path):
        """Chunk with depends_on list returns that list."""
        chunks_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on:
  - dep_a
  - dep_b
---

# test_chunk
"""
        )

        result = read_chunk_dependencies(tmp_path, ["test_chunk"])
        assert result == {"test_chunk": ["dep_a", "dep_b"]}

    def test_reads_null_deps_as_none(self, tmp_path):
        """Chunk with depends_on: null returns None."""
        chunks_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on: null
---

# test_chunk
"""
        )

        result = read_chunk_dependencies(tmp_path, ["test_chunk"])
        assert result == {"test_chunk": None}

    def test_missing_chunk_returns_none(self, tmp_path):
        """Chunk directory that doesn't exist returns None for that chunk."""
        # Create the docs/chunks directory but not the actual chunk
        (tmp_path / "docs" / "chunks").mkdir(parents=True)

        result = read_chunk_dependencies(tmp_path, ["nonexistent_chunk"])
        # Missing chunk means we couldn't parse frontmatter
        assert result == {"nonexistent_chunk": None}

    def test_reads_multiple_chunks(self, tmp_path):
        """Reads dependencies from multiple chunks."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        # chunk_a with empty deps
        (chunks_dir / "chunk_a").mkdir()
        (chunks_dir / "chunk_a" / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on: []
---

# chunk_a
"""
        )

        # chunk_b with deps
        (chunks_dir / "chunk_b").mkdir()
        (chunks_dir / "chunk_b" / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on:
  - chunk_a
---

# chunk_b
"""
        )

        result = read_chunk_dependencies(tmp_path, ["chunk_a", "chunk_b"])
        assert result == {
            "chunk_a": [],
            "chunk_b": ["chunk_a"],
        }

    def test_omitted_depends_on_returns_none(self, tmp_path):
        """Chunk with no depends_on field returns None."""
        chunks_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "GOAL.md").write_text(
            """---
status: FUTURE
---

# test_chunk
"""
        )

        result = read_chunk_dependencies(tmp_path, ["test_chunk"])
        # Omitted field should be treated as None (unknown)
        assert result == {"test_chunk": None}


class TestValidateExternalDependencies:
    """Tests for validate_external_dependencies function."""

    def test_no_external_deps_returns_empty(self):
        """No external dependencies returns empty error list."""
        mock_client = MagicMock()
        batch_chunks = {"chunk_a", "chunk_b"}
        deps = {
            "chunk_a": [],
            "chunk_b": ["chunk_a"],  # chunk_a is in batch
        }

        result = validate_external_dependencies(mock_client, batch_chunks, deps)
        assert result == []

    def test_external_dep_exists_as_work_unit(self):
        """External dependency that exists as work unit returns no error."""
        mock_client = MagicMock()
        mock_client._request.return_value = {
            "work_units": [
                {"chunk": "external_chunk", "status": "RUNNING"},
            ]
        }
        batch_chunks = {"chunk_a"}
        deps = {
            "chunk_a": ["external_chunk"],  # external_chunk not in batch
        }

        result = validate_external_dependencies(mock_client, batch_chunks, deps)
        assert result == []
        mock_client._request.assert_called_once_with("GET", "/work-units")

    def test_missing_external_dep_returns_error(self):
        """External dependency not in batch and not a work unit returns error."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"work_units": []}
        batch_chunks = {"chunk_a"}
        deps = {
            "chunk_a": ["missing_chunk"],
        }

        result = validate_external_dependencies(mock_client, batch_chunks, deps)
        assert len(result) == 1
        assert "chunk_a" in result[0]
        assert "missing_chunk" in result[0]

    def test_none_deps_skipped(self):
        """Chunks with None (unknown) dependencies are skipped."""
        mock_client = MagicMock()
        batch_chunks = {"chunk_a"}
        deps = {
            "chunk_a": None,  # Unknown deps, no validation
        }

        result = validate_external_dependencies(mock_client, batch_chunks, deps)
        assert result == []
        # Should not even query work units
        mock_client._request.assert_not_called()

    def test_multiple_chunks_same_missing_dep(self):
        """Multiple chunks depending on same missing dep generate one error each."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"work_units": []}
        batch_chunks = {"chunk_a", "chunk_b"}
        deps = {
            "chunk_a": ["missing_chunk"],
            "chunk_b": ["missing_chunk"],
        }

        result = validate_external_dependencies(mock_client, batch_chunks, deps)
        assert len(result) == 2
        # Both chunks should be mentioned
        assert any("chunk_a" in err for err in result)
        assert any("chunk_b" in err for err in result)

    def test_client_error_handled_gracefully(self):
        """Client error when querying work units is handled gracefully."""
        mock_client = MagicMock()
        mock_client._request.side_effect = Exception("Connection failed")
        batch_chunks = {"chunk_a"}
        deps = {
            "chunk_a": ["external_chunk"],
        }

        # Should not raise, but treat as if no work units exist
        result = validate_external_dependencies(mock_client, batch_chunks, deps)
        assert len(result) == 1
        assert "external_chunk" in result[0]

    def test_mixed_valid_and_invalid_deps(self):
        """Mix of valid and invalid external deps returns only errors for invalid."""
        mock_client = MagicMock()
        mock_client._request.return_value = {
            "work_units": [
                {"chunk": "existing_chunk", "status": "DONE"},
            ]
        }
        batch_chunks = {"chunk_a", "chunk_b"}
        deps = {
            "chunk_a": ["existing_chunk"],  # Valid: exists as work unit
            "chunk_b": ["missing_chunk"],  # Invalid: doesn't exist
        }

        result = validate_external_dependencies(mock_client, batch_chunks, deps)
        assert len(result) == 1
        assert "chunk_b" in result[0]
        assert "missing_chunk" in result[0]

    def test_empty_deps_returns_empty(self):
        """Empty dependencies dict returns empty error list."""
        mock_client = MagicMock()
        batch_chunks = set()
        deps = {}

        result = validate_external_dependencies(mock_client, batch_chunks, deps)
        assert result == []
