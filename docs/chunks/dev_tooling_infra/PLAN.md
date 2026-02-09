# Implementation Plan

## Approach

This chunk addresses four independent development infrastructure improvements
identified in the architecture review. The changes are all configuration and
cleanup — no new feature code is required.

The strategy:
1. Make minimal, targeted edits to `pyproject.toml` for dependency pins, markers,
   coverage config, and dev dependencies
2. Remove dead code from `tests/conftest.py` (the redundant `sys.path` hack)
3. Add `@pytest.mark.network` decorators to the `TestResolveRemoteRef` class

Each change is independently verifiable. The final validation step confirms all
tests still pass.

Per docs/trunk/TESTING_PHILOSOPHY.md, this chunk does not add new tests because:
- The click pin is a constraint, not behavior
- The marker registration is verified by running pytest with marker exclusion
- The sys.path removal is validated by existing tests passing
- The coverage config is validated by running pytest --cov

## Sequence

### Step 1: Pin click dependency to >=8.0

Edit `pyproject.toml` line 9 to change `"click"` to `"click>=8.0"`.

**Rationale**: The codebase uses Click features available since 8.0 (e.g.,
`CliRunner`, modern decorator patterns). Pinning the lower bound prevents
installation of incompatible older versions.

Location: `pyproject.toml`

---

### Step 2: Register the `network` marker in pytest configuration

Add a `markers` list to `[tool.pytest.ini_options]` in `pyproject.toml`:

```toml
markers = [
    "network: marks tests as requiring network access (deselect with '-m \"not network\"')",
]
```

This must be done before adding the marker to tests, as pytest will warn about
unknown markers.

Location: `pyproject.toml`

---

### Step 3: Add pytest-cov to dev dependencies

Add `"pytest-cov"` to the `[dependency-groups]` `dev` array in `pyproject.toml`.

Location: `pyproject.toml`

---

### Step 4: Configure coverage reporting

Add coverage configuration to `pyproject.toml`. Two options:

**Option A** (recommended): Add to `[tool.pytest.ini_options]` addopts:
```toml
addopts = "--cov=src --cov-report=term-missing"
```

**Option B**: Add a separate `[tool.coverage.run]` section:
```toml
[tool.coverage.run]
source = ["src"]
```

Option A is preferred because it means `uv run pytest` automatically produces
coverage output without requiring the user to remember `--cov`. However, this
may be noisy for quick test runs. We'll use Option B (explicit `--cov` flag)
to keep default test runs fast while still enabling coverage on demand.

Location: `pyproject.toml`

---

### Step 5: Mark network-dependent tests

Add `@pytest.mark.network` decorator to all test methods in the
`TestResolveRemoteRef` class (lines 290-339 in `tests/test_git_utils.py`).

The class contains 6 test methods that make live HTTP requests to github.com:
- `test_resolves_head_from_remote`
- `test_resolves_branch_from_remote`
- `test_raises_for_inaccessible_remote`
- `test_raises_for_nonexistent_ref`
- `test_sha_is_exactly_40_characters`
- `test_expands_github_shorthand`

Apply the decorator at the class level to mark all methods at once:

```python
@pytest.mark.network
class TestResolveRemoteRef:
    """Tests for resolve_remote_ref function."""
```

Location: `tests/test_git_utils.py`

---

### Step 6: Remove redundant sys.path manipulation

Delete line 14 from `tests/conftest.py`:
```python
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
```

Also remove `sys` from imports (line 6) if it's no longer used elsewhere.

**Rationale**: `pyproject.toml` line 35 already sets `pythonpath = ["src"]` in
`[tool.pytest.ini_options]`, making the manual path insertion redundant.

Location: `tests/conftest.py`

---

### Step 7: Verify all changes

Run the following commands to verify the changes:

1. `uv run pytest -m "not network"` — Should pass with no "unknown marker" warnings
2. `uv run pytest` — All tests should still pass
3. `uv run pytest --cov` — Should produce coverage output for `src/`

## Risks and Open Questions

- **Click version compatibility**: The codebase uses Click features from 8.0+.
  If tests fail after pinning, it would indicate the codebase needs older Click
  features — unlikely but possible.

- **sys.path removal side effects**: The `pythonpath` setting in pyproject.toml
  should be sufficient. If imports fail after removal, it means pytest isn't
  using the pyproject.toml config (which would be a deeper configuration issue).

- **Coverage report format**: The default `term-missing` format is verbose. If
  the team prefers a different format (e.g., `html`, `xml` for CI), this can be
  adjusted in follow-up work.

## Deviations

*To be populated during implementation.*