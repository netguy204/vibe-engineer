---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/repo_cache.py
- tests/test_repo_cache.py
code_references:
  - ref: src/repo_cache.py#_run_git
    implements: "Private helper that wraps subprocess.run with standard git arguments (check=True, capture_output=True, text=True) and error translation (CalledProcessError → ValueError)"
  - ref: src/repo_cache.py#_with_fetch_retry
    implements: "Private helper that encapsulates the try/catch/fetch/retry pattern for git operations that may fail due to unknown refs"
  - ref: src/repo_cache.py#ensure_cached
    implements: "Uses _run_git for fetch, reset, and clone operations instead of inline subprocess.run boilerplate"
  - ref: src/repo_cache.py#get_file_at_ref
    implements: "Uses _with_fetch_retry to delegate retry logic instead of duplicating try/fetch/retry block"
  - ref: src/repo_cache.py#resolve_ref
    implements: "Uses _with_fetch_retry to delegate retry logic instead of duplicating try/fetch/retry block"
  - ref: src/repo_cache.py#list_directory_at_ref
    implements: "Uses _with_fetch_retry to delegate retry logic instead of duplicating try/fetch/retry block"
  - ref: tests/test_repo_cache.py#TestRunGit
    implements: "Unit tests verifying _run_git success/failure behavior and error message format"
  - ref: tests/test_repo_cache.py#TestWithFetchRetry
    implements: "Unit tests verifying _with_fetch_retry success/retry/propagation behavior"
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

The `repo_cache` module contains two copy-pasted patterns that inflate its surface area and make future changes error-prone:

1. **Retry-after-fetch pattern** -- `get_file_at_ref`, `resolve_ref`, and `list_directory_at_ref` each contain an identical block: try an operation, catch the failure, run `git fetch --all --quiet`, then retry the same operation. The three copies are structurally identical and differ only in the inner callable.

2. **subprocess.run + error wrapping** -- Roughly ten call sites across the module invoke `subprocess.run` with the same set of keyword arguments (`check=True`, `capture_output=True`, `text=True`), catch `CalledProcessError`, and re-raise as `ValueError` with a formatted message. Each site repeats this boilerplate.

This chunk extracts both patterns into reusable internal helpers:

- A `_with_fetch_retry(fn, cache_path)` wrapper (or equivalent) that encapsulates the try/fetch/retry logic so the three public functions each reduce to a single call.
- A `_run_git(*args, cwd, error_msg)` helper that wraps `subprocess.run` with the standard arguments and error translation, replacing the repeated boilerplate across the module.

This is a pure refactor with no behavioral changes. It advances the project goal of keeping the codebase maintainable by agents: when patterns are duplicated, agents risk applying a fix to one copy and missing the others. Consolidation makes the module easier to evolve correctly.

## Success Criteria

- A private `_run_git(*args, cwd, error_msg)` helper (or equivalent) exists in `src/repo_cache.py` that wraps `subprocess.run` with `check=True`, `capture_output=True`, `text=True`, catches `CalledProcessError`, and re-raises as `ValueError` with the provided error message. All `subprocess.run` call sites in the module that follow this pattern use the helper instead of inlining the boilerplate.
- A private `_with_fetch_retry(fn, cache_path)` helper (or equivalent) exists that implements the try/catch/fetch/retry pattern exactly once. `get_file_at_ref`, `resolve_ref`, and `list_directory_at_ref` each delegate to this helper rather than duplicating the retry logic.
- The public API of `repo_cache.py` is unchanged: all existing functions retain the same signatures, return types, and exception behavior. No caller needs modification.
- All existing tests in `tests/test_repo_cache.py` pass without modification (or with only import-path adjustments if the test file directly references now-internal helpers).
- The retry-after-fetch block (try operation / catch / fetch / retry) appears exactly once in the module, inside the extracted helper.
- The `subprocess.run` + `CalledProcessError` catch + `ValueError` re-raise boilerplate appears at most once in the module, inside the `_run_git` helper. Call sites that intentionally deviate from the standard pattern (e.g., `_is_bare_repo`, which returns a boolean instead of raising) may remain inline but should have a comment explaining why.

