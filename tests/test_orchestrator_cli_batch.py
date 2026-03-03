# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/test_file_split - CLI batch operation tests extracted from test_orchestrator_cli.py
"""Tests for the orchestrator CLI batch commands.

Tests the CLI layer using Click's test runner. These tests mock the daemon
to test the CLI behavior without starting actual daemon processes.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from ve import cli
from orchestrator.models import OrchestratorState, WorkUnit, WorkUnitPhase, WorkUnitStatus
from orchestrator.daemon import DaemonError
from orchestrator.client import OrchestratorClientError, DaemonNotRunningError


@pytest.fixture
def runner():
    """Create a Click CLI test runner."""
    return CliRunner()


# Chunk: docs/chunks/explicit_deps_batch_inject - Batch injection with dependency ordering
class TestOrchInjectBatch:
    """Tests for ve orch inject command with multiple chunks."""

    def test_inject_multiple_chunks_no_dependencies(self, runner, tmp_path):
        """Inject multiple chunks without dependencies."""
        # Create chunk directories with GOAL.md files
        chunks_dir = tmp_path / "docs" / "chunks"
        for name in ["chunk_a", "chunk_b", "chunk_c"]:
            chunk_dir = chunks_dir / name
            chunk_dir.mkdir(parents=True)
            (chunk_dir / "GOAL.md").write_text(
                f"""---
status: FUTURE
depends_on: []
---

# {name}
"""
            )

        injected_chunks = []

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    injected_chunks.append(json["chunk"])
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": json.get("priority", 0),
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                        "explicit_deps": json.get("explicit_deps", False),
                    }
                elif path == "/work-units":
                    # List work units - return empty initially
                    return {"work_units": [], "count": 0}
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "chunk_a", "chunk_b", "chunk_c", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert len(injected_chunks) == 3
            assert "chunk_a" in injected_chunks
            assert "chunk_b" in injected_chunks
            assert "chunk_c" in injected_chunks

    def test_inject_single_chunk_backward_compatible(self, runner, tmp_path):
        """Single-chunk usage remains backward compatible."""
        # Create a chunk directory
        chunks_dir = tmp_path / "docs" / "chunks"
        chunk_dir = chunks_dir / "my_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on: []
---

# my_chunk
"""
        )

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.return_value = {
                "chunk": "my_chunk",
                "phase": "PLAN",
                "priority": 0,
                "status": "READY",
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "my_chunk", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert "Injected" in result.output
            assert "my_chunk" in result.output

    def test_inject_topological_ordering(self, runner, tmp_path):
        """Chunks with depends_on are injected after their dependencies."""
        # Create chunk directories with dependencies
        chunks_dir = tmp_path / "docs" / "chunks"

        # chunk_a has no dependencies
        chunk_a_dir = chunks_dir / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on: []
---

# chunk_a
"""
        )

        # chunk_b depends on chunk_a
        chunk_b_dir = chunks_dir / "chunk_b"
        chunk_b_dir.mkdir(parents=True)
        (chunk_b_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on:
  - chunk_a
---

# chunk_b
"""
        )

        # chunk_c depends on chunk_b (transitive dep on chunk_a)
        chunk_c_dir = chunks_dir / "chunk_c"
        chunk_c_dir.mkdir(parents=True)
        (chunk_c_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on:
  - chunk_b
---

# chunk_c
"""
        )

        injection_order = []

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    injection_order.append(json["chunk"])
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": json.get("priority", 0),
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                        "explicit_deps": json.get("explicit_deps", False),
                    }
                elif path == "/work-units":
                    return {"work_units": [], "count": 0}
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            # Inject in reverse order to verify topological sort works
            result = runner.invoke(
                cli,
                ["orch", "inject", "chunk_c", "chunk_b", "chunk_a", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            # chunk_a must be before chunk_b, chunk_b must be before chunk_c
            assert injection_order.index("chunk_a") < injection_order.index("chunk_b")
            assert injection_order.index("chunk_b") < injection_order.index("chunk_c")

    def test_inject_cycle_detection(self, runner, tmp_path):
        """Error when chunks form a dependency cycle."""
        chunks_dir = tmp_path / "docs" / "chunks"

        # chunk_a depends on chunk_b
        chunk_a_dir = chunks_dir / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on:
  - chunk_b
---

# chunk_a
"""
        )

        # chunk_b depends on chunk_a (cycle!)
        chunk_b_dir = chunks_dir / "chunk_b"
        chunk_b_dir.mkdir(parents=True)
        (chunk_b_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on:
  - chunk_a
---

# chunk_b
"""
        )

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "chunk_a", "chunk_b", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 1
            assert "cycle" in result.output.lower()

    def test_inject_external_dependency_validation(self, runner, tmp_path):
        """Error when depends_on references a chunk not in batch and not an existing work unit."""
        chunks_dir = tmp_path / "docs" / "chunks"

        # chunk_a depends on missing_chunk (not in batch)
        chunk_a_dir = chunks_dir / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on:
  - missing_chunk
---

# chunk_a
"""
        )

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units":
                    # No existing work units
                    return {"work_units": [], "count": 0}
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "chunk_a", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 1
            assert "missing_chunk" in result.output
            # Should mention it's not in batch and not existing work unit
            assert "not" in result.output.lower()

    def test_inject_blocked_by_populated(self, runner, tmp_path):
        """Work units have blocked_by populated from depends_on."""
        chunks_dir = tmp_path / "docs" / "chunks"

        # chunk_a has no dependencies
        chunk_a_dir = chunks_dir / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on: []
---

# chunk_a
"""
        )

        # chunk_b depends on chunk_a
        chunk_b_dir = chunks_dir / "chunk_b"
        chunk_b_dir.mkdir(parents=True)
        (chunk_b_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on:
  - chunk_a
---

# chunk_b
"""
        )

        inject_calls = []

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    inject_calls.append(json)
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": 0,
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                        "explicit_deps": json.get("explicit_deps", False),
                    }
                elif path == "/work-units":
                    return {"work_units": [], "count": 0}
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "chunk_a", "chunk_b", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            # Find the chunk_b injection call
            chunk_b_call = next(c for c in inject_calls if c["chunk"] == "chunk_b")
            assert "chunk_a" in chunk_b_call["blocked_by"]

    def test_inject_explicit_deps_flag_set(self, runner, tmp_path):
        """Work units with explicit depends_on declaration have explicit_deps=True.

        Both empty list [] and populated list have explicit_deps=True (agent knows deps).
        Only null/omitted has explicit_deps=False (agent doesn't know deps).
        """
        chunks_dir = tmp_path / "docs" / "chunks"

        # chunk_a has explicit empty depends_on (explicitly no deps)
        chunk_a_dir = chunks_dir / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on: []
---

# chunk_a
"""
        )

        # chunk_b depends on chunk_a (explicit deps)
        chunk_b_dir = chunks_dir / "chunk_b"
        chunk_b_dir.mkdir(parents=True)
        (chunk_b_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on:
  - chunk_a
---

# chunk_b
"""
        )

        inject_calls = []

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    inject_calls.append(json)
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": 0,
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                        "explicit_deps": json.get("explicit_deps", False),
                    }
                elif path == "/work-units":
                    return {"work_units": [], "count": 0}
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "chunk_a", "chunk_b", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            # chunk_a has depends_on: [] (explicit empty list), so explicit_deps should be True
            chunk_a_call = next(c for c in inject_calls if c["chunk"] == "chunk_a")
            assert chunk_a_call.get("explicit_deps") is True

            # chunk_b has depends_on with items, so explicit_deps should be True
            chunk_b_call = next(c for c in inject_calls if c["chunk"] == "chunk_b")
            assert chunk_b_call.get("explicit_deps") is True

    def test_inject_external_dependency_exists_as_work_unit(self, runner, tmp_path):
        """Dependencies outside the batch are allowed if they exist as work units."""
        chunks_dir = tmp_path / "docs" / "chunks"

        # chunk_b depends on external_chunk (not in batch but exists as work unit)
        chunk_b_dir = chunks_dir / "chunk_b"
        chunk_b_dir.mkdir(parents=True)
        (chunk_b_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on:
  - external_chunk
---

# chunk_b
"""
        )

        inject_calls = []

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    inject_calls.append(json)
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": 0,
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                        "explicit_deps": json.get("explicit_deps", False),
                    }
                elif path == "/work-units":
                    # external_chunk exists as a work unit
                    return {
                        "work_units": [
                            {"chunk": "external_chunk", "status": "RUNNING"}
                        ],
                        "count": 1,
                    }
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "chunk_b", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert len(inject_calls) == 1
            assert inject_calls[0]["chunk"] == "chunk_b"
            assert "external_chunk" in inject_calls[0]["blocked_by"]

    def test_inject_batch_output_format(self, runner, tmp_path):
        """Batch injection shows progress for each chunk."""
        chunks_dir = tmp_path / "docs" / "chunks"

        for name in ["chunk_a", "chunk_b"]:
            chunk_dir = chunks_dir / name
            chunk_dir.mkdir(parents=True)
            deps = "[]" if name == "chunk_a" else "[chunk_a]"
            (chunk_dir / "GOAL.md").write_text(
                f"""---
status: FUTURE
depends_on: {deps}
---

# {name}
"""
            )

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": 0,
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                    }
                elif path == "/work-units":
                    return {"work_units": [], "count": 0}
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "chunk_b", "chunk_a", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            # Should mention both chunks were injected
            assert "chunk_a" in result.output
            assert "chunk_b" in result.output
            # Should show blocked_by info for chunk_b
            assert "blocked_by" in result.output.lower() or "Injected 2" in result.output

    def test_inject_batch_json_output(self, runner, tmp_path):
        """Batch injection with --json outputs array of results."""
        chunks_dir = tmp_path / "docs" / "chunks"

        for name in ["chunk_a", "chunk_b"]:
            chunk_dir = chunks_dir / name
            chunk_dir.mkdir(parents=True)
            (chunk_dir / "GOAL.md").write_text(
                f"""---
status: FUTURE
depends_on: []
---

# {name}
"""
            )

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": 0,
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                    }
                elif path == "/work-units":
                    return {"work_units": [], "count": 0}
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "chunk_a", "chunk_b", "--json", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "results" in data
            assert len(data["results"]) == 2

    def test_inject_empty_depends_on_sets_explicit_deps_true(self, runner, tmp_path):
        """A chunk with depends_on: [] should have explicit_deps=True when injected.

        The empty list means the agent explicitly declares no dependencies,
        which is different from null/omitted (unknown dependencies).
        """
        chunks_dir = tmp_path / "docs" / "chunks"

        # Create chunk with explicit empty depends_on
        chunk_dir = chunks_dir / "independent_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on: []
---

# independent_chunk
"""
        )

        inject_calls = []

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    inject_calls.append(json)
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": 0,
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                        "explicit_deps": json.get("explicit_deps", False),
                    }
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "independent_chunk", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert len(inject_calls) == 1

            # Empty depends_on means explicit declaration of no deps
            # So explicit_deps should be True
            call = inject_calls[0]
            assert call.get("explicit_deps") is True, (
                f"Expected explicit_deps=True for depends_on: [], got {call}"
            )

    def test_inject_null_depends_on_sets_explicit_deps_false(self, runner, tmp_path):
        """A chunk with depends_on: null should have explicit_deps=False.

        Null means the agent doesn't know dependencies, so oracle should be consulted.
        """
        chunks_dir = tmp_path / "docs" / "chunks"

        # Create chunk with null depends_on
        chunk_dir = chunks_dir / "unknown_deps_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on: null
---

# unknown_deps_chunk
"""
        )

        inject_calls = []

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    inject_calls.append(json)
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": 0,
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                        "explicit_deps": json.get("explicit_deps", False),
                    }
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "unknown_deps_chunk", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert len(inject_calls) == 1

            # null depends_on means unknown deps - consult oracle
            # So explicit_deps should be False
            call = inject_calls[0]
            assert call.get("explicit_deps", False) is False, (
                f"Expected explicit_deps=False for depends_on: null, got {call}"
            )

    def test_inject_omitted_depends_on_sets_explicit_deps_false(self, runner, tmp_path):
        """A chunk with no depends_on field should have explicit_deps=False.

        Omitted field means the agent doesn't know dependencies (same as null).
        """
        chunks_dir = tmp_path / "docs" / "chunks"

        # Create chunk with omitted depends_on
        chunk_dir = chunks_dir / "no_depends_field_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text(
            """---
status: FUTURE
---

# no_depends_field_chunk
"""
        )

        inject_calls = []

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    inject_calls.append(json)
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": 0,
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                        "explicit_deps": json.get("explicit_deps", False),
                    }
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "no_depends_field_chunk", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert len(inject_calls) == 1

            # omitted depends_on means unknown deps - consult oracle
            # So explicit_deps should be False
            call = inject_calls[0]
            assert call.get("explicit_deps", False) is False, (
                f"Expected explicit_deps=False for omitted depends_on, got {call}"
            )
