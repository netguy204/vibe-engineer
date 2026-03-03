---
status: DRAFTING
advances_trunk_goal: "Required Properties: Following the workflow must maintain the health of documents over time and should not grow more difficult over time."
proposed_chunks:
  - prompt: >
      Fix the TOCTOU race condition in the orchestrator dispatch loop
      (`src/orchestrator/scheduler.py`). The dispatch loop reads the ready queue,
      then iterates and starts agents. Between reading the queue and transitioning
      a work unit to RUNNING, an API-driven status change could modify the work
      unit. The asyncio lock protects against concurrent dispatch ticks but not
      API mutations. Add a guard in `_dispatch_tick()` (or the transition helper
      it calls) that verifies the work unit is still in READY status immediately
      before transitioning to RUNNING. If the status has changed, skip the unit
      and log a warning.
    chunk_directory: dispatch_toctou_guard
    depends_on: []
  - prompt: >
      Add incomplete finalization recovery to the orchestrator daemon startup.
      In `src/orchestrator/worktree.py`, `finalize_work_unit()` commits, removes
      the worktree, then merges. If the daemon crashes after worktree removal but
      before merge, committed changes exist only in the branch ref with no
      automated recovery. On daemon startup (in `src/orchestrator/daemon.py` or
      `scheduler.py` initialization), check for work units that were in RUNNING
      status with committed branches but where the merge to the base branch was
      never completed. Log warnings for each and either auto-recover the merge or
      transition the work unit to NEEDS_ATTENTION with a descriptive message.
    chunk_directory: finalization_recovery
    depends_on: []
  - prompt: >
      Persist retry-at timestamps in the orchestrator work unit record so that
      daemon restarts preserve backoff behavior. Currently retry scheduling in
      `src/orchestrator/scheduler.py` uses `asyncio.get_event_loop().call_later()`
      which is in-memory only. If the daemon restarts, work units in READY status
      with `api_retry_count > 0` dispatch immediately without backoff. Add a
      `retry_after` datetime field to the work unit model in
      `src/orchestrator/state.py`. When scheduling retries, persist the target
      time. On daemon startup, check READY work units with a future `retry_after`
      and schedule them appropriately rather than dispatching immediately.
    chunk_directory: persist_retry_state
    depends_on: []
  - prompt: >
      Extract the retry-after-fetch pattern in `src/repo_cache.py` into a
      reusable helper. The pattern (try operation, catch failure, fetch from
      remote, retry operation) is copy-pasted identically in `get_file_at_ref`
      (lines ~198-214), `resolve_ref` (lines ~251-267), and
      `list_directory_at_ref` (lines ~313-329). Extract a
      `_with_fetch_retry(fn, *args)` wrapper or decorator that encapsulates
      this pattern. Also extract the repeated `subprocess.run` + error wrapping
      into a `_run_git(*args, cwd, error_msg)` helper to reduce boilerplate
      across the module's ~10 call sites.
    chunk_directory: repo_cache_dry
    depends_on: []
  - prompt: >
      Extract `narrative compact` file manipulation from the CLI layer into a
      domain method. Currently `src/cli/narrative.py:233-304` (the `compact`
      command) directly reads OVERVIEW.md, regex-parses frontmatter, modifies
      the YAML dict, re-serializes it, and writes the file. This is the only
      CLI command that directly manipulates file content instead of delegating
      to a domain method. Create a `Narratives.compact(chunk_ids, name,
      description)` method in `src/narratives.py` that handles the file
      manipulation, and have the CLI command delegate to it.
    chunk_directory: narrative_compact_extract
    depends_on: []
  - prompt: >
      Extract the merge strategy logic from `src/orchestrator/worktree.py`
      (~1,439 lines) into a dedicated `src/orchestrator/merge.py` module.
      The checkout-free merge strategy (`_merge_without_checkout`) and the
      fallback temporary index merge are complex enough (~200 lines combined)
      to warrant their own module. The worktree module should focus on worktree
      lifecycle (create, remove, lock, unlock, list) while merge.py handles
      the merge strategies. Keep the public API surface unchanged - worktree.py
      should delegate to merge.py internally.
    chunk_directory: worktree_merge_extract
    depends_on: []
  - prompt: >
      Add development tooling infrastructure to the project. (1) Add a lower
      bound to the click dependency in `pyproject.toml` - should be `click>=8.0`
      at minimum. (2) Mark network-dependent tests in
      `tests/test_git_utils.py:290-339` (class `TestResolveRemoteRef`) with a
      `@pytest.mark.network` marker so they can be excluded in CI or offline
      environments. Register the marker in `pyproject.toml` under
      `[tool.pytest.ini_options]` markers. (3) Remove the redundant
      `sys.path.insert` from `tests/conftest.py:14` since `pyproject.toml:35`
      already sets `pythonpath = ["src"]`. (4) Add `pytest-cov` to dev
      dependencies and configure basic coverage reporting in `pyproject.toml`.
    chunk_directory: dev_tooling_infra
    depends_on: []
  - prompt: >
      Deduplicate the `reviewer decisions` CLI implementation. In
      `src/cli/reviewer.py`, the group handler's `--recent` path (lines ~77-128)
      and the `decisions list` subcommand (lines ~186-274) implement nearly
      identical logic: glob decision files, parse frontmatter, filter curated,
      sort by mtime, format output. Extract a shared helper function (e.g.,
      `_list_decisions(project_dir, recent, pending, curated_only)`) and have
      both the group handler and the subcommand delegate to it. Also fix the
      overlap between `--recent` on the group and `--recent` on the subcommand.
    chunk_directory: reviewer_decisions_dedup
    depends_on: []
  - prompt: >
      Remove dead code identified in the architecture review. (1) Delete the
      `_start_task_chunk` function at `src/cli/chunk.py:220-253` - it is defined
      but never called (the batch version `_start_task_chunks` handles both
      single and multi-chunk cases). (2) Remove or simplify
      `validate_combined_chunk_name` at `src/cli/utils.py:30-54` - it accepts
      a `ticket_id` parameter but ignores it (line 47: `combined_name =
      short_name`), making it equivalent to `validate_short_name`. (3) Plan
      removal of the `task_utils.py` re-export shim (163 lines) - migrate any
      remaining callers to import from the `task` package directly.
    chunk_directory: dead_code_removal
    depends_on: []
  - prompt: >
      Make orchestrator crash recovery phase-aware. Currently
      `_recover_from_crash()` treats all RUNNING work units identically,
      clearing the worktree reference and resetting to READY. When
      re-dispatched, `_run_work_unit()` unconditionally calls
      `activate_chunk_in_worktree()` which expects FUTURE status. This only
      works for PLAN phase -- all later phases have the chunk in
      IMPLEMENTING, ACTIVE, or HISTORICAL on the branch. Fix
      `_run_work_unit()` to only call activation during PLAN phase, and fix
      recovery to preserve the worktree reference when the worktree
      directory still exists.
    chunk_directory: phase_aware_recovery
    depends_on: []
created_after: ["explicit_chunk_deps"]
---

## Advances Trunk Goal

**Required Properties** (line 35-36): "Following the workflow must maintain the health of documents over time and should not grow more difficult over time."

A February 2026 architecture review by four senior reviewers identified findings that fall outside the scope of three existing remediation narratives (`arch_review_remediation`, `arch_decompose`, `arch_consolidation`). These gaps include concurrency bugs, missing recovery mechanisms, DRY violations, dead code, and missing development tooling -- all of which increase the cost of future change if left unaddressed.

## Driving Ambition

Three prior architecture narratives addressed the bulk of findings from a comprehensive codebase review. This narrative captures the **remaining gaps**: issues that were either not covered at all or only partially addressed by existing narratives.

The findings fall into three categories:

**Correctness** (chunks 1-3): A TOCTOU race in orchestrator dispatch, missing crash recovery for incomplete work unit finalization, and in-memory-only retry state that doesn't survive daemon restarts.

**Structural cleanup** (chunks 4-6, 8-9): DRY violations in repo_cache.py, domain logic trapped in the CLI layer (narrative compact), an oversized worktree module that mixes lifecycle management with merge strategy, duplicated reviewer decisions logic, and dead code.

**Infrastructure** (chunk 7): Missing dependency version pins, network-dependent tests without skip markers, redundant test config, and no coverage tooling.

## Chunks

1. **Fix TOCTOU race in dispatch** -- Add a status guard before transitioning work units to RUNNING. Independent.

2. **Add finalization recovery on daemon startup** -- Detect work units with committed branches but incomplete merges. Independent.

3. **Persist retry-at timestamps** -- Store retry schedule in the work unit record so daemon restarts preserve backoff. Independent.

4. **DRY up repo_cache.py** -- Extract retry-after-fetch wrapper and git subprocess helper. Independent.

5. **Extract narrative compact to domain layer** -- Move file manipulation from CLI to `Narratives.compact()`. Independent.

6. **Extract worktree merge logic** -- Split merge strategies into `orchestrator/merge.py`. Independent.

7. **Add dev tooling infrastructure** -- Pin click, mark network tests, remove sys.path hack, add coverage config. Independent.

8. **Deduplicate reviewer decisions** -- Extract shared listing logic from group handler and subcommand. Independent.

9. **Remove dead code** -- Delete `_start_task_chunk`, simplify `validate_combined_chunk_name`, plan `task_utils.py` removal. Independent.

10. **Phase-aware crash recovery** -- Make `_run_work_unit()` skip activation for non-PLAN phases; preserve worktree references during recovery. Independent.

## Completion Criteria

When this narrative is complete:

- The orchestrator dispatch loop is protected against TOCTOU races between queue reads and status transitions
- Daemon restart after a crash during work unit finalization either auto-recovers the merge or flags the work unit for operator attention
- Retry backoff behavior survives daemon restarts
- `repo_cache.py` has no copy-pasted retry blocks or boilerplate subprocess handling
- No CLI command directly manipulates artifact file content -- all delegate to domain methods
- `worktree.py` is focused on worktree lifecycle; merge strategies live in their own module
- Network-dependent tests can be skipped in offline/CI environments
- The click dependency has a lower version bound
- No dead or unreachable code identified by the review remains in the codebase
- Daemon restarts correctly resume work units at any phase without activation failures
- All existing tests continue to pass