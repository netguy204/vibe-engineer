---
decision: APPROVE
summary: All success criteria satisfied - _run_git and _with_fetch_retry helpers exist, all call sites migrated, tests pass, retry pattern appears exactly once
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: A private `_run_git(*args, cwd, error_msg)` helper (or equivalent) exists in `src/repo_cache.py` that wraps `subprocess.run` with `check=True`, `capture_output=True`, `text=True`, catches `CalledProcessError`, and re-raises as `ValueError` with the provided error message. All `subprocess.run` call sites in the module that follow this pattern use the helper instead of inlining the boilerplate.

- **Status**: satisfied
- **Evidence**: `_run_git` exists at lines 19-50 with proper signature `(*args, cwd, error_msg)`. It wraps `subprocess.run` with the required arguments and catches `CalledProcessError` to re-raise as `ValueError`. All call sites that follow this pattern now use the helper:
  - `ensure_cached` uses `_run_git` at lines 191, 196, and 205 (for fetch, reset, and clone)
  - `try_read()` in `get_file_at_ref` uses `_run_git` at line 246
  - `try_resolve()` in `resolve_ref` uses `_run_git` at line 272
  - `try_list()` in `list_directory_at_ref` uses `_run_git` at line 305

### Criterion 2: A private `_with_fetch_retry(fn, cache_path)` helper (or equivalent) exists that implements the try/catch/fetch/retry pattern exactly once. `get_file_at_ref`, `resolve_ref`, and `list_directory_at_ref` each delegate to this helper rather than duplicating the retry logic.

- **Status**: satisfied
- **Evidence**: `_with_fetch_retry` exists at lines 53-89 with proper signature `(fn: Callable[[], T], cache_path: Path) -> T`. All three target functions delegate to it:
  - `get_file_at_ref` at line 253: `return _with_fetch_retry(try_read, cache_path)`
  - `resolve_ref` at line 282: `return _with_fetch_retry(try_resolve, cache_path)`
  - `list_directory_at_ref` at line 320: `return _with_fetch_retry(try_list, cache_path)`

### Criterion 3: The public API of `repo_cache.py` is unchanged: all existing functions retain the same signatures, return types, and exception behavior. No caller needs modification.

- **Status**: satisfied
- **Evidence**: All public function signatures are unchanged:
  - `get_cache_dir() -> Path`
  - `repo_to_cache_path(repo: str) -> Path`
  - `ensure_cached(repo: str) -> Path`
  - `get_repo_path(repo: str) -> Path`
  - `get_file_at_ref(repo: str, ref: str, file_path: str) -> str`
  - `resolve_ref(repo: str, ref: str) -> str`
  - `list_directory_at_ref(repo: str, ref: str, dir_path: str) -> list[str]`
  All 33 tests pass, confirming behavioral compatibility.

### Criterion 4: All existing tests in `tests/test_repo_cache.py` pass without modification (or with only import-path adjustments if the test file directly references now-internal helpers).

- **Status**: satisfied
- **Evidence**: `pytest tests/test_repo_cache.py` runs 33 tests and all pass. The test file imports the new helpers (`_run_git`, `_with_fetch_retry`) to test them directly, which is an expected import-path addition. Pre-existing tests for public functions pass without modification.

### Criterion 5: The retry-after-fetch block (try operation / catch / fetch / retry) appears exactly once in the module, inside the extracted helper.

- **Status**: satisfied
- **Evidence**: Grep for `git fetch --all` shows only one occurrence at line 79, inside `_with_fetch_retry`. The pattern (try fn → catch ValueError → fetch → retry fn) is fully contained in lines 70-89. No other functions contain duplicate retry logic.

### Criterion 6: The `subprocess.run` + `CalledProcessError` catch + `ValueError` re-raise boilerplate appears at most once in the module, inside the `_run_git` helper. Call sites that intentionally deviate from the standard pattern (e.g., `_is_bare_repo`, which returns a boolean instead of raising) may remain inline but should have a comment explaining why.

- **Status**: satisfied
- **Evidence**: The `CalledProcessError` → `ValueError` pattern appears in:
  1. `_run_git` (lines 47-50) - the intended single location
  2. `_is_bare_repo` (line 148-149) - correctly documented deviation (lines 129-131 explain: "Note: This function intentionally does not use _run_git because its error-handling semantics differ. Instead of raising ValueError on failure, it returns False")
  3. `_with_fetch_retry` (line 85) - catches `CalledProcessError` but does NOT re-raise as ValueError; it silently swallows fetch failures, which is intentional and documented (lines 74-76)

  All three usages are either the canonical location or properly documented deviations.
