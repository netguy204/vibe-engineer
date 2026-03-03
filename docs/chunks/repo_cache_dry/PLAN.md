<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a pure refactoring chunk that extracts two copy-pasted patterns in `src/repo_cache.py` into reusable internal helpers:

1. **`_run_git(*args, cwd, error_msg)`** - Wraps `subprocess.run` with the standard arguments (`check=True`, `capture_output=True`, `text=True`) and error translation (catch `CalledProcessError`, re-raise as `ValueError` with formatted message).

2. **`_with_fetch_retry(fn, cache_path)`** - Encapsulates the try/catch/fetch/retry pattern that appears identically in `get_file_at_ref`, `resolve_ref`, and `list_directory_at_ref`.

The refactor follows the DRY principle: each pattern should have a single authoritative implementation. This makes future changes safer (fix in one place, applied everywhere) and reduces the module's surface area.

**Testing strategy**: Per `docs/trunk/TESTING_PHILOSOPHY.md`, this is pure refactoring with no behavioral changes. All existing tests in `tests/test_repo_cache.py` should pass without modification. We'll add targeted unit tests for the new helpers to verify their contracts, but the primary verification is that existing tests continue to pass.

## Subsystem Considerations

The module header references `docs/subsystems/cross_repo_operations`. This chunk does not change the subsystem's public interface or patterns—it only consolidates internal implementation details. No subsystem updates are required.

## Sequence

### Step 1: Add `_run_git` helper

Create a private `_run_git(*args, cwd, error_msg)` helper that:
- Accepts variable git command arguments, a `cwd` path, and an `error_msg` string
- Calls `subprocess.run` with `check=True`, `capture_output=True`, `text=True`
- Catches `subprocess.CalledProcessError` and re-raises as `ValueError` using the provided `error_msg` (with `stderr` appended if available)
- Returns the `CompletedProcess` result on success

Location: `src/repo_cache.py`, after the import block and before `get_cache_dir`.

**Note on `_is_bare_repo`**: This function intentionally deviates from the standard pattern—it catches `CalledProcessError` and returns `False` instead of raising. Add a comment explaining this deviation. The function remains inline because its error-handling semantics differ from `_run_git`.

### Step 2: Migrate `ensure_cached` to use `_run_git`

Replace the three `subprocess.run` call sites in `ensure_cached`:
1. `git fetch --all --quiet` (lines 112-118)
2. `git reset --hard origin/HEAD` (lines 120-126)
3. `git clone --quiet` (lines 136-141)

Each site currently has its own try/except block. After migration, these become single `_run_git` calls with appropriate error messages.

Verify existing tests pass: `pytest tests/test_repo_cache.py -k TestEnsureCached`

### Step 3: Add `_with_fetch_retry` helper

Create a private `_with_fetch_retry(fn, cache_path)` helper that:
- Takes a callable `fn` (that may raise `ValueError`) and a `cache_path`
- Tries calling `fn()`
- On `ValueError`, attempts `git fetch --all --quiet` at `cache_path`
- If fetch succeeds, retries `fn()` and returns its result (letting any exception propagate)
- If fetch fails, re-raises the original `ValueError`

This encapsulates the identical logic currently in:
- `get_file_at_ref` (lines 198-214)
- `resolve_ref` (lines 251-267)
- `list_directory_at_ref` (lines 313-329)

Location: `src/repo_cache.py`, after `_run_git`.

### Step 4: Migrate `get_file_at_ref` to use `_with_fetch_retry`

Replace the try/fetch/retry block (lines 198-214) with a single call to `_with_fetch_retry`.

The nested `try_read()` function remains as the inner callable passed to `_with_fetch_retry`.

Verify existing tests pass: `pytest tests/test_repo_cache.py -k TestGetFileAtRef`

### Step 5: Migrate `resolve_ref` to use `_with_fetch_retry`

Replace the try/fetch/retry block (lines 251-267) with a single call to `_with_fetch_retry`.

The nested `try_resolve()` function remains as the inner callable.

Verify existing tests pass: `pytest tests/test_repo_cache.py -k TestResolveRef`

### Step 6: Migrate `list_directory_at_ref` to use `_with_fetch_retry`

Replace the try/fetch/retry block (lines 313-329) with a single call to `_with_fetch_retry`.

The nested `try_list()` function remains as the inner callable.

Verify existing tests pass: `pytest tests/test_repo_cache.py -k TestListDirectoryAtRef`

### Step 7: Add unit tests for new helpers

Add targeted tests for the extracted helpers in `tests/test_repo_cache.py`:

**For `_run_git`:**
- `test_run_git_returns_result_on_success`: Verify successful command returns `CompletedProcess`
- `test_run_git_raises_valueerror_with_message`: Verify failed command raises `ValueError` with the provided error message and stderr content

**For `_with_fetch_retry`:**
- `test_with_fetch_retry_returns_on_first_success`: When `fn()` succeeds immediately, return its value without fetching
- `test_with_fetch_retry_fetches_and_retries_on_error`: When `fn()` fails, fetch, then retry and return the retried value
- `test_with_fetch_retry_propagates_error_after_retry_fails`: When retry also fails, propagate the error from the retry (not the original)

Location: `tests/test_repo_cache.py`

### Step 8: Run full test suite and verify

Run `uv run pytest tests/test_repo_cache.py` to verify:
- All existing tests pass without modification
- New helper tests pass
- No regressions in behavior

## Risks and Open Questions

- **Error message consistency**: The new helpers must preserve the exact error messages from the current implementation to avoid breaking any code that parses or logs these messages. Each migration step should verify error message content in tests.

- **Fetch failure handling**: The current pattern silently swallows fetch failures and retries the original operation. This is intentional (the fetch might fail for network reasons, but the ref might already be local). The `_with_fetch_retry` helper must preserve this behavior.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->