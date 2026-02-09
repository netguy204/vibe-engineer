---
decision: FEEDBACK
summary: "_run_git helper exists and is used in ensure_cached, but try_read/try_resolve/try_list still inline the CalledProcessError→ValueError pattern instead of using the helper"
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: A private `_run_git(*args, cwd, error_msg)` helper (or equivalent) exists in `src/repo_cache.py` that wraps `subprocess.run` with `check=True`, `capture_output=True`, `text=True`, catches `CalledProcessError`, and re-raises as `ValueError` with the provided error message. All `subprocess.run` call sites in the module that follow this pattern use the helper instead of inlining the boilerplate.

- **Status**: gap
- **Evidence**: `_run_git` exists at lines 19-50 and properly wraps subprocess.run with error handling. However, not all call sites use it. `ensure_cached` uses `_run_git` (lines 188, 193, 202), but `get_file_at_ref`, `resolve_ref`, and `list_directory_at_ref` still call subprocess.run directly inside nested `try_read()`, `try_resolve()`, and `try_list()` functions (lines 244, 278, 319).

### Criterion 2: A private `_with_fetch_retry(fn, cache_path)` helper (or equivalent) exists that implements the try/catch/fetch/retry pattern exactly once. `get_file_at_ref`, `resolve_ref`, and `list_directory_at_ref` each delegate to this helper rather than duplicating the retry logic.

- **Status**: satisfied
- **Evidence**: `_with_fetch_retry` exists at lines 53-86. All three functions delegate to it: `get_file_at_ref` at line 258, `resolve_ref` at line 295, `list_directory_at_ref` at line 341.

### Criterion 3: The public API of `repo_cache.py` is unchanged: all existing functions retain the same signatures, return types, and exception behavior. No caller needs modification.

- **Status**: satisfied
- **Evidence**: All public function signatures (`get_cache_dir`, `repo_to_cache_path`, `ensure_cached`, `get_repo_path`, `get_file_at_ref`, `resolve_ref`, `list_directory_at_ref`) are unchanged. Tests pass without modification to calling code.

### Criterion 4: All existing tests in `tests/test_repo_cache.py` pass without modification (or with only import-path adjustments if the test file directly references now-internal helpers).

- **Status**: satisfied
- **Evidence**: All 33 tests pass. The test file imports the new helpers `_run_git` and `_with_fetch_retry` to test them directly, which is expected. Pre-existing tests for public functions pass unchanged.

### Criterion 5: The retry-after-fetch block (try operation / catch / fetch / retry) appears exactly once in the module, inside the extracted helper.

- **Status**: satisfied
- **Evidence**: The retry-after-fetch pattern (try fn → catch ValueError → fetch → retry fn) appears only in `_with_fetch_retry` at lines 70-86. `get_file_at_ref`, `resolve_ref`, and `list_directory_at_ref` all delegate to this helper.

### Criterion 6: The `subprocess.run` + `CalledProcessError` catch + `ValueError` re-raise boilerplate appears at most once in the module, inside the `_run_git` helper. Call sites that intentionally deviate from the standard pattern (e.g., `_is_bare_repo`, which returns a boolean instead of raising) may remain inline but should have a comment explaining why.

- **Status**: gap
- **Evidence**: The pattern appears in 4 places:
  1. `_run_git` (lines 47-50) - the intended single location ✓
  2. `try_read` in `get_file_at_ref` (lines 252-256) - inlined, not using `_run_git`
  3. `try_resolve` in `resolve_ref` (lines 289-293) - inlined, not using `_run_git`
  4. `try_list` in `list_directory_at_ref` (lines 335-339) - inlined, not using `_run_git`

  `_is_bare_repo` (line 145-146) is correctly documented as an intentional deviation. However, the three nested functions are NOT documented deviations - they follow the standard pattern but inline it rather than using `_run_git`.

## Feedback Items

### Issue 1: Nested functions don't use `_run_git`

- **ID**: issue-run-git-not-used
- **Location**: src/repo_cache.py lines 243-256, 276-293, 317-339
- **Concern**: The nested `try_read()`, `try_resolve()`, and `try_list()` functions inline the `subprocess.run` + `CalledProcessError` + `ValueError` pattern instead of using `_run_git`. This leaves 3 additional copies of the boilerplate, defeating the DRY goal stated in criterion 6.
- **Suggestion**: Modify `_run_git` to accept either a string or a callable for `error_msg` so it can generate context-aware error messages. Then have the nested functions use `_run_git`. Example:
  ```python
  def try_read() -> str:
      result = _run_git(
          "show", f"{ref}:{file_path}",
          cwd=cache_path,
          error_msg=f"Cannot read '{file_path}' at ref '{ref}' in '{repo}'"
      )
      return result.stdout
  ```
- **Severity**: functional
- **Confidence**: high
