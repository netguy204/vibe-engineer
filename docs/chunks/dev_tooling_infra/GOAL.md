---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- pyproject.toml
- tests/conftest.py
- tests/test_git_utils.py
code_references:
  - ref: pyproject.toml
    implements: "Click >=8.0 pin, network marker registration, pytest-cov dev dep, coverage config"
  - ref: tests/test_git_utils.py#TestResolveRemoteRef
    implements: "Network marker on remote-ref tests for offline/CI exclusion"
  - ref: tests/conftest.py
    implements: "Removed redundant sys.path manipulation (pythonpath in pyproject.toml suffices)"
narrative: arch_review_gaps
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- cli_decompose
- integrity_deprecate_standalone
- low_priority_cleanup
- optimistic_locking
- spec_and_adr_update
- test_file_split
- orch_session_auto_resume
---
# Chunk Goal

## Minor Goal

Harden the project's development tooling and test infrastructure by addressing four gaps identified during architecture review:

1. **Pin click lower bound** -- The `click` dependency in `pyproject.toml` is currently unpinned. It should declare `click>=8.0` to guarantee the Click features the codebase relies on (e.g., `CliRunner` in tests, decorator-based CLI construction).

2. **Mark network-dependent tests** -- The `TestResolveRemoteRef` test class in `tests/test_git_utils.py` makes live HTTP requests to `github.com`. These tests should be marked with `@pytest.mark.network` so they can be excluded in CI or offline environments via `pytest -m "not network"`. The custom marker must be registered in `pyproject.toml` under `[tool.pytest.ini_options]` to avoid marker warnings.

3. **Remove redundant `sys.path` manipulation** -- `tests/conftest.py` contains a `sys.path.insert(0, ...)` call that adds `src/` to the Python path. This is redundant because `pyproject.toml` already sets `pythonpath = ["src"]` in `[tool.pytest.ini_options]`. The manual insertion should be removed to avoid confusion and eliminate a maintenance hazard.

4. **Add pytest-cov and configure coverage** -- Add `pytest-cov` to the dev dependency group and configure basic coverage reporting in `pyproject.toml` so developers can run `uv run pytest --cov` to see which code paths are exercised by the test suite.

## Success Criteria

- `pyproject.toml` declares `click>=8.0` in the `dependencies` list instead of the bare `click` specifier.
- Every test method in the `TestResolveRemoteRef` class in `tests/test_git_utils.py` is decorated with `@pytest.mark.network`.
- Running `uv run pytest -m "not network"` completes successfully, skipping the network-dependent tests without producing "unknown marker" warnings.
- The `network` marker is registered under `[tool.pytest.ini_options]` `markers` in `pyproject.toml`.
- The `sys.path.insert(0, ...)` line is removed from `tests/conftest.py`. All existing tests still pass, confirming the `pythonpath` setting in `pyproject.toml` is sufficient.
- `pytest-cov` is listed in the `[dependency-groups]` `dev` array in `pyproject.toml`.
- `pyproject.toml` includes `--cov=src` (or equivalent) in `addopts` under `[tool.pytest.ini_options]`, or at minimum a `[tool.coverage.run]` section with `source = ["src"]` so that `uv run pytest --cov` produces meaningful output.
- `uv run pytest` continues to pass with all changes applied.
