---
status: DRAFTING
advances_trunk_goal: 'Required Properties: Following the workflow must maintain the
  health of documents over time and should not grow more difficult over time.'
proposed_chunks:
- prompt: 'Delete the four deprecated standalone validation functions in src/integrity.py
    (lines 772-914): validate_chunk_subsystem_refs, validate_chunk_investigation_ref,
    validate_chunk_narrative_ref, validate_chunk_friction_entries_ref. Remove their
    tests. No backward compatibility needed.'
  chunk_directory: null
  depends_on: []
- prompt: 'Delete the two dead-code hook functions in src/orchestrator/agent.py: create_question_intercept_hook
    (lines 289-367) and create_review_decision_hook (lines 371-441). Their own docstrings
    document they are non-functional. Remove any registration sites that reference
    them. Remove their tests.'
  chunk_directory: null
  depends_on: []
- prompt: Replace the four nearly-identical validate_*_ref wrapper methods on the
    Chunks class (src/chunks.py:899-985) with a single validate_refs method that calls
    IntegrityValidator.validate_chunk() once and partitions results by link_type.
    Update chunk_validation.py (lines 373-390) to call the single method. This eliminates
    four redundant Project+IntegrityValidator instantiations per chunk completion.
  chunk_directory: null
  depends_on:
  - 0
- prompt: Make backreference scanning language-agnostic. In src/integrity.py _validate_code_backreferences
    (line 658-663), replace the hardcoded src/**/*.py glob with a strategy that uses
    git ls-files (--cached --others --exclude-standard) to enumerate user source files,
    automatically respecting .gitignore to exclude package/dependency directories
    (node_modules, vendor, dist, .venv, etc.) without maintaining a hardcoded exclusion
    list. Filter the git-tracked files by known source extensions (py, js, ts, jsx,
    tsx, rb, go, rs, java, kt, swift, c, cpp, h, cs, etc.). For non-git projects (VE
    supports working outside git repos), fall back to a simple recursive glob with
    a minimal exclusion set (.git, __pycache__). Apply the same fix to src/backreferences.py
    count_backreferences (line 58-59) which also defaults to src/**/*.py. Extract
    the shared file-enumeration logic into a common utility so both modules use the
    same strategy. Also fix the filter bug at src/backreferences.py:79 where files
    with only subsystem or narrative refs (but no chunk refs) are silently excluded.
  chunk_directory: null
  depends_on: []
- prompt: 'Fix update_working_tree_if_on_branch in src/orchestrator/merge.py (lines
    308-348) to not silently discard uncommitted changes. The function runs git checkout
    -- . which destroys unstaged modifications. Change it to: check for uncommitted
    changes first (git status --porcelain), and if any exist, skip the working tree
    update and log a warning that the user''s working tree is behind the branch tip.
    The user can then manually reconcile.'
  chunk_directory: null
  depends_on: []
- prompt: 'Replace the __import__(''datetime'') usage in src/orchestrator/review_routing.py
    (lines 224-225, 245-246) with a normal top-level import. Move the 12 scattered
    local import json statements in src/cli/orch.py to a single top-level import.
    Fix the inconsistent argument naming: rename shortname to short_name in src/cli/subsystem.py:114.
    Replace the manual rsplit(''/'') path stripping in src/cli/narrative.py:197-198
    with strip_artifact_path_prefix(). Remove the emoji at src/cli/friction.py:366.'
  chunk_directory: null
  depends_on: []
- prompt: Run oracle analysis off the async event loop. In src/orchestrator/scheduler.py:1106,
    oracle.analyze_conflict() is called synchronously while holding self._lock, blocking
    the dispatch tick with file I/O. Wrap the oracle analysis call in asyncio.to_thread()
    so it runs in a thread pool. Ensure the lock is released during the thread execution
    and re-acquired after, or restructure so conflict analysis runs as a pre-computation
    step outside the locked dispatch tick.
  chunk_directory: null
  depends_on: []
- prompt: 'Promote the 6+ private client._request() call sites in src/cli/orch.py
    to typed public methods on the orchestrator client (src/orchestrator/client.py).
    Create methods: inject_work_unit(), get_queue(), set_priority(), get_config(),
    update_config(), list_worktrees(), remove_worktree(). Update all call sites in
    orch.py to use the new methods. Also extract the duplicated prune result display
    logic (shared between worktree prune at lines 949-996 and orch prune at lines
    999-1073) into a shared helper.'
  chunk_directory: null
  depends_on: []
- prompt: Decompose the list_chunks function in src/cli/chunk.py (lines 291-497, 206
    lines). Extract the mutual exclusivity checking (lines 314-344) into a Click callback
    or validation helper. Extract the full-list rendering branch (lines 402-497) into
    its own function. Extract the duplicated status_matches closure from src/cli/formatters.py
    (lines 81-92 and 163-175) into a module-level function.
  chunk_directory: null
  depends_on: []
- prompt: 'Add migration state machine test coverage. The VALID_MIGRATION_TRANSITIONS
    dict (src/migrations.py:49-76), update_status, update_phase, get_status, and parse_migration_frontmatter
    are completely untested. Add tests covering: valid transitions succeed, invalid
    transitions are rejected, terminal states have no outgoing transitions, phase
    updates persist correctly, and frontmatter round-trips cleanly. Also fix the YAML
    round-trip issue: _update_migration_frontmatter (line 420-433) uses yaml.safe_load/dump
    which destroys comments; switch to ruamel.yaml consistent with the rest of the
    codebase (DEC-008).'
  chunk_directory: null
  depends_on: []
- prompt: Add file locking to repo cache concurrent access. In src/repo_cache.py ensure_cached
    (line 163), two concurrent ve processes can corrupt the git index by both running
    fetch+reset simultaneously. Add a per-repo lockfile (e.g., .ve-lock in the cached
    repo dir) that is acquired before fetch/reset and released after. Use fcntl.flock
    or a similar mechanism. Also add a timeout parameter to resolve_remote_ref in
    src/git_utils.py (line 100-105) to prevent indefinite hangs on git ls-remote.
  chunk_directory: null
  depends_on: []
- prompt: Make backreference scanning work for any programming language, not just
    Python. Currently, both `src/integrity.py` `_validate_code_backreferences` (line
    658-663) and `src/backreferences.py` `count_backreferences` (line 58-59) hardcode
    `src/**/*.py` as the only glob pattern for discovering source files with backreference
    comments. This means projects using JavaScript, TypeScript, Go, Rust, or any other
    language get zero backreference validation or counting.
  chunk_directory: backref_language_agnostic
  depends_on: []
- prompt: 'Fix five code hygiene issues identified during the architecture review.
    These are small, mechanical cleanups that individually are not worth a chunk but
    collectively reduce cognitive friction and enforce codebase conventions:'
  chunk_directory: code_hygiene
  depends_on: []
- prompt: 'Delete the four deprecated standalone validation functions in `src/integrity.py`
    (lines 772-914): `validate_chunk_subsystem_refs`, `validate_chunk_investigation_ref`,
    `validate_chunk_narrative_ref`, and `validate_chunk_friction_entries_ref`. These
    functions are backward-compatibility shims that emit deprecation warnings and
    delegate to the `Chunks` class methods, which themselves already route through
    `IntegrityValidator`. No production code calls these functions -- the migration
    to `IntegrityValidator` is complete. Removing them eliminates ~142 lines of dead
    code and their associated test class (`TestDeprecatedStandaloneFunctions` in `tests/test_integrity.py`,
    5 tests), reducing maintenance burden and cognitive load when navigating the validation
    subsystem. This is the first chunk in the arch_review_cleanup narrative''s dead
    code removal tier.'
  chunk_directory: integrity_deprecated_removal
  depends_on: []
- prompt: Decompose the 206-line `list_chunks` function in `src/cli/chunk.py` (lines
    291-497) into focused, single-responsibility helpers. The function currently handles
    mutual exclusivity validation, multiple output mode branches, and full-list rendering
    with status filtering, external artifact handling, and JSON serialization all
    inline. This makes it difficult to read, test, and modify without risk of regressions.
  chunk_directory: list_chunks_decompose
  depends_on: []
- prompt: Prevent `update_working_tree_if_on_branch` in `src/orchestrator/merge.py`
    from silently destroying uncommitted changes in the user's working tree.
  chunk_directory: merge_safety
  depends_on: []
- prompt: Add test coverage for the migration state machine in `src/migrations.py`,
    which is currently untested beyond migration creation. The `VALID_MIGRATION_TRANSITIONS`
    dict, `update_status`, `update_phase`, `get_status`, and `parse_migration_frontmatter`
    methods have zero test coverage, meaning transition validation logic (valid transitions,
    invalid transitions, terminal state enforcement) has never been exercised by the
    test suite.
  chunk_directory: migration_test_coverage
  depends_on: []
- prompt: Move the synchronous `oracle.analyze_conflict()` call off the async event
    loop in the scheduler's dispatch tick.
  chunk_directory: oracle_async
  depends_on: []
- prompt: The orchestrator CLI (`src/cli/orch.py`) bypasses the typed client API in
    10 places, calling `client._request()` directly with raw HTTP method strings and
    URL paths. This couples the CLI to the daemon's HTTP contract and makes the client
    class an incomplete abstraction -- callers must know internal API routes to use
    it.
  chunk_directory: orch_typed_client
  depends_on: []
- prompt: Delete the two dead-code hook functions in `src/orchestrator/agent.py` --
    `create_question_intercept_hook` (lines 289-367) and `create_review_decision_hook`
    (lines 371-441) -- whose own docstrings explicitly document that they are non-functional.
    PreToolUse hooks in the Claude Agent SDK do not fire for built-in tools (AskUserQuestion)
    or MCP tools (ReviewDecision); the actual capture already happens via message
    parsing in `run_orchestrator_agent()`. These functions add ~150 lines of dead
    code that misleads readers into thinking hook-based interception is active.
  chunk_directory: orchestrator_dead_hooks
  depends_on: []
- prompt: Add concurrency safety to the repository cache and prevent indefinite hangs
    during remote ref resolution.
  chunk_directory: repo_cache_locking
  depends_on: []
- prompt: Replace the four nearly-identical `validate_*_ref` wrapper methods on the
    `Chunks` class (`validate_subsystem_refs`, `validate_investigation_ref`, `validate_narrative_ref`,
    `validate_friction_entries_ref` in `src/chunks.py` lines 899-985) with a single
    `validate_refs` method. Each of the current wrappers independently instantiates
    a `Project` and `IntegrityValidator`, calls `validator.validate_chunk()`, then
    filters the results by a single `link_type`. When all four are called in sequence
    during chunk completion (via `src/chunk_validation.py` lines 373-390), this creates
    four redundant `Project` + `IntegrityValidator` instantiations and four full validation
    passes for the same chunk.
  chunk_directory: validation_unify
  depends_on: []
created_after:
- explicit_chunk_deps
---
## Advances Trunk Goal

This narrative advances **"Following the workflow must maintain the health of documents over time and should not grow more difficult over time."** A comprehensive architecture review identified accumulated technical debt, dead code, correctness bugs, and language assumptions that collectively make the codebase harder to maintain and limit its applicability. Addressing these issues reduces cognitive load, improves correctness, and makes the tool work across all programming languages.

## Driving Ambition

A team of four senior architects independently reviewed the vibe-engineer codebase across four dimensions: core domain model, orchestrator subsystem, CLI/developer experience, and cross-cutting concerns. They identified 30+ findings ranging from dead code and god objects to silent data loss bugs and language-exclusivity assumptions.

This narrative organizes the actionable findings into concrete chunks, prioritized by impact. The work falls into three tiers:

1. **Dead code removal** (chunks 0-1): Delete deprecated functions and non-functional hooks that add confusion without value. No backward compatibility needed.

2. **Correctness and robustness fixes** (chunks 2-5): Fix the redundant validation instantiation, make backreference scanning language-agnostic, prevent silent data loss in working tree updates, and clean up code hygiene issues.

3. **Architectural improvements** (chunks 6-10): Unblock the async event loop from synchronous oracle analysis, promote the orchestrator CLI to use typed client methods, decompose the oversized list_chunks function, add missing test coverage, and add concurrency safety to the repo cache.

## Chunks

1. **Delete deprecated integrity standalone functions** - Remove 142 lines of backward-compat shims in integrity.py that delegate to the already-migrated IntegrityValidator path.

2. **Delete dead-code orchestrator hooks** - Remove create_question_intercept_hook and create_review_decision_hook from agent.py, which are self-documented as non-functional.

3. **Unify Chunks validation into single IntegrityValidator call** - Replace four near-identical validate_*_ref methods with one method that calls IntegrityValidator once and partitions results. Eliminates 4 redundant Project instantiations per chunk completion.

4. **Language-agnostic backreference scanning** - Use `git ls-files` to enumerate source files (respecting `.gitignore` as the exclusion mechanism), filter by source extensions, and fall back to simple glob for non-git projects. Fix the silent exclusion of files with only subsystem/narrative refs.

5. **Safe working tree update after merge** - Prevent update_working_tree_if_on_branch from discarding uncommitted changes via git checkout -- .. Check for dirty state first and skip with a warning.

6. **Code hygiene sweep** - Fix __import__ usage, hoist local imports, normalize argument naming, use shared path-stripping utilities, remove stray emoji.

7. **Async oracle conflict analysis** - Move synchronous oracle.analyze_conflict() off the event loop to prevent dispatch latency under load.

8. **Typed orchestrator client API** - Promote _request() call sites to named public methods and deduplicate prune display logic.

9. **Decompose list_chunks** - Break the 206-line function into focused helpers for validation, rendering, and status matching.

10. **Migration state machine tests** - Add comprehensive test coverage for the completely untested migration state machine and fix YAML round-tripping to use ruamel.yaml.

11. **Repo cache concurrency safety** - Add file locking for concurrent access and timeout for remote ref resolution.

## Completion Criteria

When complete:

- Zero deprecated functions or self-documented dead code remains in the codebase
- Chunk completion validates all reference types in a single IntegrityValidator pass (not four)
- Backreference scanning works for any programming language, not just Python, while correctly excluding dependency directories
- The orchestrator cannot silently discard uncommitted user changes
- The orchestrator dispatch loop is not blocked by synchronous file I/O
- All orchestrator CLI operations use typed client methods, not raw HTTP requests
- The migration state machine has test coverage for all transitions
- Concurrent repo cache access is safe under file locking
- No code hygiene issues (stray imports, naming inconsistencies, emoji) remain from the review findings
