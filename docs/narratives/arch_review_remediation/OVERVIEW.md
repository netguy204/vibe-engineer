---
status: DRAFTING
advances_trunk_goal: "Required Properties: Following the workflow must maintain the health of documents over time and should not grow more difficult over time."
proposed_chunks:
  - prompt: >
      Fix the critical data loss bug in `src/orchestrator/worktree.py:1152-1191`
      where `_update_working_tree_if_on_branch` runs `git checkout -- .` after
      `git reset --mixed HEAD`, silently overwriting uncommitted changes. Replace
      with `git read-tree -m -u HEAD` or equivalent that fails safely on conflicts
      instead of destroying work.
    chunk_directory: worktree_data_loss_fix
    depends_on: []
  - prompt: >
      Fix SQLite JSON queries in `src/orchestrator/state.py` that use
      `LIKE '%"chunk_name"%'` for blocked_by searches (lines ~708, ~765). These
      can false-match when one chunk name is a substring of another. Replace with
      `json_each()` consistently, matching the pattern already used correctly in
      `list_blocked_by_chunk`.
    chunk_directory: sqlite_json_query_fix
    depends_on: []
  - prompt: >
      Move `list_proposed_chunks` out of the `Chunks` class
      (`src/chunks.py:813-877`) to `Project`, since it queries across
      investigations, narratives, and subsystems. Break the circular import
      between `chunks.py` and `integrity.py` by having integrity functions accept
      protocols/interfaces instead of concrete types. Fix `Reviewers`
      (`src/reviewers.py:79-104`) to use the shared `frontmatter.py` parsing
      instead of its own manual YAML regex.
    chunk_directory: chunks_class_decouple
    depends_on: []
  - prompt: >
      Decompose the scheduler's `_advance_phase` God Method
      (`src/orchestrator/scheduler.py:562-753`) by extracting the completion/cleanup
      logic into `_finalize_completed_work_unit()`. Extract `_handle_review_result`
      (~160 lines, scheduler.py:925-1135) into a `review_routing.py` module
      alongside `review_parsing.py`.
    chunk_directory: scheduler_decompose_methods
    depends_on: []
  - prompt: >
      Consolidate duplicated patterns across artifact managers: (1) Extract
      `find_duplicates` into a single method on `ArtifactManager`. (2) Unify
      `ChunkRelationship`/`SubsystemRelationship` in `src/models/references.py`
      into a generic `ArtifactRelationship`. (3) Merge the duplicate
      `_parse_created_after`/`_parse_yaml_created_after` in
      `src/artifact_ordering.py:128-195`. (4) Unify the four `Active*`
      dataclasses in `src/template_system.py:79-212` into a single
      `ActiveArtifact`.
    chunk_directory: artifact_pattern_consolidation
    depends_on: []
  - prompt: >
      Cache `ArtifactIndex` as a lazily-initialized property on
      `ArtifactManager` instead of instantiating it repeatedly
      (`src/chunks.py:187,265,385,740`). Fix the N+1 query patterns in
      `src/orchestrator/state.py` where `get_ready_queue` and
      `get_attention_queue` issue individual COUNT(*) queries per work unit —
      replace with JOIN or subquery.
    chunk_directory: artifact_index_cache
    depends_on: [4]
  - prompt: >
      Add optimistic locking to `update_work_unit` in
      `src/orchestrator/state.py` to detect stale writes from the scheduler/API
      race condition (separate StateStore instances). Check `updated_at` matches
      expected value before writing.
    chunk_directory: optimistic_locking
    depends_on: [1]
  - prompt: >
      Decompose the two largest CLI files: (1) `src/cli/chunk.py` (1281 lines) —
      extract `_parse_status_filters` to the domain layer, extract list rendering
      to formatters, migrate `create` and `list` commands to use
      `handle_task_context` like all other CLI modules. (2) `src/cli/orch.py`
      (1104 lines) — extract `orch_tail` streaming logic into the orchestrator
      package. (3) Extract the shared interactive prompting logic duplicated
      between `log_entry` and `_log_entry_task_context` in
      `src/cli/friction.py:72-288`.
    chunk_directory: cli_decompose
    depends_on: []
  - prompt: >
      Deprecate the four standalone integrity functions at
      `src/integrity.py:678-858` that duplicate logic in `IntegrityValidator`.
      Route callers through the validator or extract a shared implementation.
    chunk_directory: integrity_deprecate_standalone
    depends_on: [2]
  - prompt: >
      Low-priority cleanup: (1) Fix `StateMachine` at `src/state_machine.py:60`
      to raise an explicit error when a status exists in the enum but is missing
      from the transition map, instead of silently treating it as terminal.
      (2) Remove the identity function `extract_short_name` from
      `src/models/shared.py:12-23`. (3) Consolidate the three copies of
      `_get_current_branch` across `worktree.py` (twice) and `daemon.py` into a
      single utility. (4) Fix `ArtifactType` double-import shadowing in
      `chunk.py`, `narrative.py`, `subsystem.py`, `investigation.py`.
      (5) Remove or clearly document the non-functional PreToolUse hooks in
      `src/orchestrator/agent.py:593-612`.
    chunk_directory: low_priority_cleanup
    depends_on: []
  - prompt: >
      Split large test files along functional boundaries:
      `test_orchestrator_scheduler.py` (5046 lines),
      `test_orchestrator_cli.py` (1930 lines),
      `test_orchestrator_agent.py` (1899 lines),
      `test_orchestrator_worktree.py` (1685 lines). Each should be broken into
      focused test modules that test distinct functional areas. Ensure all tests
      pass after the split.
    chunk_directory: test_file_split
    depends_on: [3, 4]
  - prompt: >
      Update `docs/trunk/SPEC.md`: (1) Replace `ve chunk start` with
      `ve chunk create` at line ~443 and any other references. (2) Add a note
      to the IMPLEMENTING constraint section (around line ~216) explaining that
      the orchestrator maintains the single-IMPLEMENTING constraint via worktrees
      — each worktree has at most one IMPLEMENTING chunk, but the orchestrator
      can manage multiple worktrees in parallel. (3) Record missing ADRs in
      `docs/trunk/DECISIONS.md` for the orchestrator daemon architecture,
      Pydantic model choice, and the ArtifactManager base class pattern.
    chunk_directory: spec_and_adr_update
    depends_on: []
created_after: ["explicit_chunk_deps"]
---

## Advances Trunk Goal

**Required Properties** (line 35-36): "Following the workflow must maintain the health of documents over time and should not grow more difficult over time."

A senior architectural review of the codebase identified 20 concrete issues across critical, high, medium, and low priority bands. Addressing these issues reduces coupling, eliminates code duplication, fixes correctness bugs, and brings documentation back into alignment with implementation — all of which directly serve the property that the workflow should not grow more difficult over time.

## Driving Ambition

A team of four senior reviewers conducted a comprehensive architecture review of the vibe-engineer codebase (~30K lines across ~80 source files). They identified two critical bugs (data loss in worktree merge-back, false-match SQLite queries), several high-priority structural issues (cross-cutting concerns absorbed by the wrong class, circular imports, duplicated frontmatter parsing, a 190-line God Method), medium-priority consolidation opportunities (duplicated patterns across managers, repeated index instantiation, N+1 queries, stale-write races, large CLI files), and low-priority cleanup items. Additionally, the SPEC.md has drifted from the implementation, and large test files need splitting for maintainability.

This narrative organizes these findings into 12 well-scoped chunks that can be largely parallelized, with dependencies only where one chunk's changes are prerequisite to another's.

## Chunks

1. **Fix worktree data loss bug** — Replace destructive `git checkout -- .` with a safe alternative in `_update_working_tree_if_on_branch`. No dependencies.

2. **Fix SQLite JSON query false-matches** — Replace LIKE-based blocked_by queries with `json_each()` consistently. No dependencies.

3. **Decouple Chunks class and fix cross-cutting concerns** — Move `list_proposed_chunks` to Project, break circular imports via protocols, fix Reviewers frontmatter parsing. No dependencies.

4. **Decompose scheduler God Methods** — Extract `_finalize_completed_work_unit()` from `_advance_phase` and `_handle_review_result` into `review_routing.py`. No dependencies.

5. **Consolidate duplicated artifact patterns** — Unify `find_duplicates`, relationship models, `_parse_created_after` variants, and `Active*` dataclasses. No dependencies.

6. **Cache ArtifactIndex and fix N+1 queries** — Lazy-init ArtifactIndex on ArtifactManager, replace N+1 patterns in state.py. Depends on chunk 5 (ArtifactManager changes).

7. **Add optimistic locking to work unit updates** — Detect stale writes from scheduler/API race. Depends on chunk 2 (state.py changes).

8. **Decompose large CLI files** — Break down chunk.py, orch.py, and friction.py CLI modules. No dependencies.

9. **Deprecate standalone integrity functions** — Route callers through IntegrityValidator. Depends on chunk 3 (Chunks class restructuring).

10. **Low-priority cleanup sweep** — StateMachine error handling, identity function removal, branch utility consolidation, import shadowing fixes, non-functional hook cleanup. No dependencies.

11. **Split large test files** — Break orchestrator test files along functional boundaries. Depends on chunks 4 and 5 (scheduler and manager changes must land first so tests are split against the new structure).

12. **Update SPEC.md and record missing ADRs** — Fix `ve chunk start` → `ve chunk create`, document orchestrator's worktree-based parallelism model, record architectural decisions. No dependencies.

## Completion Criteria

When this narrative is complete:

- No known critical or high-priority bugs remain in the codebase
- The `Chunks` class is focused on chunk-specific operations; cross-cutting queries live on `Project`
- Circular import chains are broken via protocols
- The scheduler's largest methods are decomposed into focused, testable units
- Duplicated code patterns (find_duplicates, relationship models, frontmatter parsing, Active* dataclasses) are consolidated
- Performance issues (repeated ArtifactIndex instantiation, N+1 queries) are resolved
- The scheduler/API stale-write race is protected by optimistic locking
- CLI files over 1000 lines are decomposed into focused modules
- Standalone integrity functions are deprecated in favor of IntegrityValidator
- Low-priority cleanup items (identity functions, import shadowing, non-functional hooks) are resolved
- No test file exceeds ~1000 lines; all tests pass
- SPEC.md correctly references `ve chunk create` and documents the orchestrator's parallel execution model
- Missing architectural decisions are recorded in DECISIONS.md
