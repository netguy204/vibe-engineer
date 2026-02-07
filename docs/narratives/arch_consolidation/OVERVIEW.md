---
status: DRAFTING
advances_trunk_goal: "Required Properties: Following the workflow must maintain the health of documents over time and should not grow more difficult over time."
proposed_chunks:
  - prompt: "Extract a shared frontmatter I/O utility module (`src/frontmatter.py`) that consolidates the ~10 duplicated YAML frontmatter parsing implementations across chunks.py, narratives.py, investigations.py, subsystems.py, friction.py, and artifact_ordering.py into a single parse/validate/update interface. Include the `_update_overview_frontmatter()` write pattern. All existing callers should be migrated to use the shared utility."
    chunk_directory: null
    depends_on: []
  - prompt: "Extract a generic base `ArtifactManager` class (or protocol) that captures the shared pattern across Chunks, Narratives, Investigations, and Subsystems: `__init__(project_dir)`, `enumerate_*()`, `find_duplicates()`, `create_*()`, `parse_*_frontmatter()`, `get_status()`, `update_status()`. Include a reusable `StateMachine` class for transition validation. Each concrete manager should subclass/implement the base, specifying only directory name, main filename, frontmatter model, and transition rules. Depends on the frontmatter I/O utility."
    chunk_directory: null
    depends_on: [0]
  - prompt: "Break up the `src/chunks.py` god module (1948 lines). Extract ML/clustering logic (suggest_prefix, cluster_chunks with sklearn) into `src/cluster_analysis.py` or a new `src/analysis/` module. Extract consolidation logic (consolidate_chunks, ConsolidationResult) into its own module. Extract backreference scanning (count_backreferences, update_backreferences, BackreferenceInfo) into `src/backreferences.py`. The core Chunks class should shrink to ~800 lines of CRUD and lifecycle management."
    chunk_directory: null
    depends_on: [1]
  - prompt: "Move pure computation functions out of `src/cli/orch.py` into the orchestrator domain layer. Specifically: `topological_sort_chunks` (Kahn's algorithm), `read_chunk_dependencies`, and `validate_external_dependencies` should move to `src/orchestrator/` since they have zero CLI dependency. The CLI module should only contain Click commands and presentation logic."
    chunk_directory: null
    depends_on: []
  - prompt: "Extract shared prune/merge/cleanup logic from `scheduler.py` and `api.py` into `worktree.py` to create a single source of truth for worktree lifecycle operations. Currently the prune logic is duplicated across `_advance_phase()` in scheduler.py, `prune_work_unit_endpoint()` in api.py, and `prune_all_endpoint()` in api.py, risking logic drift."
    chunk_directory: null
    depends_on: []
  - prompt: "Surface validation errors consistently across all artifact types. Currently only `parse_chunk_frontmatter_with_errors()` provides detailed Pydantic error messages; narratives, investigations, and subsystems silently swallow `ValidationError` and return `None`. Add `_with_errors` variants (or make error surfacing the default) for all artifact frontmatter parsers. Also fix the bare `except Exception` in `plan_has_content()` and standardize the return-None vs raise-ValueError convention across manager methods."
    chunk_directory: null
    depends_on: [0, 1]
  - prompt: "Add worktree cleanup on activation failure in the scheduler's `_run_work_unit()` method. Currently if `activate_chunk_in_worktree()` fails after worktree creation succeeds, the worktree is leaked. The `finally` block should clean up the worktree on failure, not just remove the chunk from `_running_agents`."
    chunk_directory: null
    depends_on: []
  - prompt: "Fix stale socket and port file cleanup in `stop_daemon()`. Currently after SIGKILL fallback, only the PID file is cleaned up but socket and port files are left behind. Also ensure `atexit` handlers account for the SIGKILL path. The daemon's `stop_daemon()` function should clean up all state files (PID, socket, port) regardless of how the daemon exits."
    chunk_directory: null
    depends_on: []
  - prompt: "Standardize CLI exit codes: use exit code 0 for 'no results found' (valid state) and exit code 1 for actual errors (missing files, invalid input, parse failures). Currently `ve chunk list` returns 1 for no chunks while `ve friction list` returns 0 for no entries. Audit all CLI commands and make empty-result handling consistent. Document the exit code convention."
    chunk_directory: null
    depends_on: []
  - prompt: "Add explicit SQLite transaction boundaries in `src/orchestrator/state.py` for multi-statement operations. With `isolation_level=None` (autocommit), operations like `update_work_unit()` that perform SELECT + UPDATE + INSERT can partially commit on crash. Wrap related statements in explicit `BEGIN`/`COMMIT` blocks to ensure atomicity."
    chunk_directory: null
    depends_on: []
  - prompt: "Add `--json` output option to artifact list commands: `ve chunk list`, `ve narrative list`, `ve investigation list`, `ve subsystem list`, and `ve friction list`. The orchestrator commands already have `--json` consistently. JSON output should include all fields visible in the text output plus frontmatter metadata, enabling agent and script integration."
    chunk_directory: null
    depends_on: []
  - prompt: "Deduplicate task-context branching across CLI modules. Currently 6+ modules repeat the same `if is_task_directory(project_dir): _task_handler(...); return` pattern. Extract a decorator or context manager (e.g., `@task_aware`) that handles the branching, reducing boilerplate and ensuring consistent task-context behavior."
    chunk_directory: null
    depends_on: []
  - prompt: "Enrich CLI group-level help text so `ve --help` is self-documenting for new users. Currently groups have terse descriptions like 'Chunk commands'. Add one-sentence descriptions explaining what chunks, narratives, investigations, and subsystems ARE. Also add 'not found' suggestions (e.g., 'Run ve chunk list to see available chunks') to improve error actionability."
    chunk_directory: null
    depends_on: []
  - prompt: "Address `git checkout` during orchestrator merge operations. Currently `merge_to_base` in `worktree.py` does `git checkout` on the main repo, which disrupts the user's working tree if they're actively working there. Investigate alternatives like `git merge --no-checkout`, bare-repo merge, or `git worktree`-based merge to avoid modifying the main working tree."
    chunk_directory: null
    depends_on: []
  - prompt: "Add subsystem bidirectional integrity check to `src/integrity.py`. Currently chunk<->narrative and chunk<->investigation bidirectionality are validated, but chunk<->subsystem is not. A chunk can reference a subsystem in its `subsystems` field while the subsystem's `chunks` field doesn't list it back (or vice versa), and no warning is emitted."
    chunk_directory: null
    depends_on: []
  - prompt: "Fix the off-by-one confusion in `validate_identifier()` length check error message in `src/validation.py:27`. The condition `len(value) >= max_length + 1` is equivalent to `len(value) > max_length` but the error message says 'must be less than {max_length + 1} characters' when it means 'must be at most {max_length} characters'. Simplify the condition and clarify the message."
    chunk_directory: null
    depends_on: []
created_after: ["explicit_chunk_deps"]
---

## Advances Trunk Goal

**Required Properties**: "Following the workflow must maintain the health of documents over time and should not grow more difficult over time."

The vibe-engineer codebase has accumulated structural debt through copy-paste patterns as new artifact types were added. This makes the tooling progressively harder to maintain and extend — directly undermining the property that the workflow should not grow more difficult over time. Each new artifact type currently requires touching 9+ files with copy-pasted boilerplate. Consolidating shared patterns makes the codebase sustainable as the artifact vocabulary grows.

## Driving Ambition

A team of four senior reviewers independently analyzed the vibe-engineer architecture and converged on the same core finding: **as artifact types were added (chunks, narratives, investigations, subsystems, friction, migrations), patterns were copy-pasted rather than abstracted.** This has produced ~10 copies of frontmatter parsing, 4 near-identical artifact managers, 3+ duplicated state machine validators, and several god modules mixing unrelated concerns.

The goal of this narrative is to consolidate these patterns into shared abstractions, clean up module boundaries, fix operational issues in the orchestrator, and improve CLI consistency — all without changing external behavior. This is a pure structural improvement initiative.

The work decomposes into three tiers:

**Tier 1 — Structural consolidation (chunks 0-5):** Extract shared utilities, base classes, and break up god modules. These have the highest ROI and form a dependency chain.

**Tier 2 — Correctness and consistency (chunks 6-9):** Fix error handling gaps, resource leaks, exit code inconsistencies, and crash resilience. These are independent of each other and of tier 1.

**Tier 3 — Polish and completeness (chunks 10-15):** Add JSON output, reduce CLI boilerplate, improve help text, fix edge cases. These are independent leaf tasks.

## Chunks

0. **frontmatter_io** — Extract shared frontmatter I/O utility from ~10 duplicated parsing implementations
1. **artifact_manager_base** — Extract generic base ArtifactManager class with reusable StateMachine (depends on 0)
2. **chunks_decompose** — Break up chunks.py god module: extract ML, consolidation, backreference scanning (depends on 1)
3. **orch_cli_extract** — Move pure algorithms (topo sort, dependency reading) from CLI to domain layer
4. **orch_prune_consolidate** — Extract shared prune/merge logic into worktree.py
5. **validation_error_surface** — Surface validation errors consistently across all artifact types (depends on 0, 1)
6. **orch_worktree_cleanup** — Add worktree cleanup on activation failure
7. **orch_daemon_stale_files** — Fix stale socket/port file cleanup after SIGKILL
8. **cli_exit_codes** — Standardize exit codes: 0 for no results, 1 for errors
9. **orch_state_transactions** — Add explicit SQLite transaction boundaries
10. **cli_json_output** — Add --json to artifact list commands
11. **cli_task_context_dedup** — Deduplicate task-context branching with decorator
12. **cli_help_text** — Enrich group-level help text and error suggestions
13. **orch_merge_safety** — Address git checkout during merge (don't disrupt main working tree)
14. **integrity_subsystem_bidir** — Add subsystem bidirectional integrity check
15. **validation_length_msg** — Fix validate_identifier() off-by-one error message

## Completion Criteria

When this narrative is complete:

1. **Adding a new artifact type** requires defining only a Pydantic model, a manager subclass with ~50 lines of configuration, a CLI module, and a template — no copy-pasting of frontmatter parsing, status transitions, or update logic.
2. **No module exceeds ~800 lines** of mixed concerns — chunks.py, cli/orch.py, and cli/chunk.py are decomposed into focused modules.
3. **All CLI commands** use consistent exit codes (0 for empty results, 1 for errors) and offer `--json` output for machine consumption.
4. **The orchestrator** handles all identified failure modes: worktree leaks on activation failure, stale files after unclean shutdown, partial SQLite writes, and merge operations that don't disrupt the user's working tree.
5. **Validation errors** are surfaced with actionable detail for all artifact types, not just chunks.
6. **All tests pass** with no behavioral changes — this is a pure structural improvement.