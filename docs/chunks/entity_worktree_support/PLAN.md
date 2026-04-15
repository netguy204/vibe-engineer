

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk adds entity submodule support to the orchestrator's worktree lifecycle. The work is
additive — no existing orchestrator behavior changes, we insert entity-aware steps into the
worktree creation and merge flows.

**Data flow**:
1. `WorktreeManager._create_single_repo_worktree()` calls `git worktree add` — we add an
   `_init_entity_submodules(worktree_path, chunk)` call immediately after, which runs
   `git submodule update --init` in the worktree then checks out a `ve-worktree-<chunk>`
   branch in each entity submodule (leaving it off detached HEAD).

2. The agent runs in the worktree. Any entity-startup/shutdown within the session commits
   entity changes to `ve-worktree-<chunk>`. The orchestrator's existing `commit_changes()`
   (which runs `git add -A`) automatically picks up the updated entity submodule pointer
   and includes it in the chunk commit.

3. `WorktreeManager._merge_to_base_single_repo()` merges the chunk branch to main — we add
   a call to `merge_entity_worktree_branches(project_dir, chunk)` after the merge succeeds.
   This merges each entity's `ve-worktree-<chunk>` branch into the entity's `main` branch
   (without checkout, using git plumbing), then deletes the worktree branch.

The entity git operations live in `src/entity_repo.py` (they're entity-lifecycle concerns) and
are called from `src/orchestrator/worktree.py` (the worktree lifecycle orchestrator).

**No decision to add**: This approach (no-op when no entities attached, best-effort entity
merge with logged warnings on conflict) is consistent with the existing orchestrator's
design of isolating chunk work and not surfacing entity merge conflicts as hard errors during
the main chunk finalization.

## Subsystem Considerations

**docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS new behavior in the
orchestrator's worktree lifecycle. The entity submodule init and merge steps are orthogonal
to the existing scheduling and agent dispatch logic. No deviation from orchestrator patterns.

## Sequence

### Step 1: Correct GOAL.md code_paths

The chunk's GOAL.md lists `src/orchestrator/agent.py` and `src/orchestrator/daemon.py` as
code_paths. Based on investigation, the actual changes land in:
- `src/orchestrator/worktree.py` (worktree creation and merge hooks)
- `src/entity_repo.py` (entity-specific git operations)
- `tests/test_entity_worktree.py` (new test file)

Update `docs/chunks/entity_worktree_support/GOAL.md` code_paths accordingly.

### Step 2: Add `init_entity_submodules_in_worktree()` to `entity_repo.py`

Add a module-level function:

```python
# Chunk: docs/chunks/entity_worktree_support - Initialize entity submodules in orchestrator worktree
def init_entity_submodules_in_worktree(worktree_path: Path, chunk: str) -> None:
    """Initialize entity submodules in an orchestrator worktree.

    After `git worktree add`, the worktree directory exists but entity
    submodules have not been initialized. This function:
    1. Runs `git submodule update --init` in the worktree to populate
       .entities/<name>/ directories.
    2. For each entity, checks out a working branch `ve-worktree-<chunk>`
       from the detached HEAD state left by submodule init.

    This ensures agents running in the worktree can commit entity changes
    without affecting the main checkout or other worktrees.

    No-op if .entities/ doesn't exist or contains no submodule-based entities.

    Args:
        worktree_path: Absolute path to the orchestrator-created worktree.
        chunk: Chunk name used to derive the entity working branch name.
    """
```

Implementation notes:
- Check `(worktree_path / ".entities").exists()` first; return early if not.
- Run `git submodule update --init` via `subprocess.run(cwd=worktree_path)`.
  Log a warning and return if it fails (don't raise — entity support is additive).
- Iterate entities: for each dir in `.entities/` where `.git` is a file (submodule marker),
  run `git checkout -b ve-worktree-{chunk}` in the entity dir.
  If the branch already exists (rare but possible), just `git checkout ve-worktree-{chunk}`.

Location: `src/entity_repo.py` near the end of the submodule operations section.

### Step 3: Add `merge_entity_worktree_branches()` to `entity_repo.py`

Add a module-level function:

```python
# Chunk: docs/chunks/entity_worktree_support - Merge entity worktree branches to main after chunk merge
def merge_entity_worktree_branches(project_dir: Path, chunk: str) -> None:
    """Merge entity worktree branches to entity main after chunk merges to base.

    After the orchestrator merges orch/<chunk> to main (which includes the
    updated entity submodule pointer), this function merges each entity's
    `ve-worktree-<chunk>` branch into the entity's `main` branch and deletes
    the worktree branch. This keeps the entity's main branch current.

    Uses a no-checkout merge (git merge-base + git merge-tree + git commit-tree)
    mirroring how the orchestrator merges chunk branches without disturbing the
    user's working directory. If a merge conflict occurs (e.g., two worktrees
    modified the same entity), logs a warning and skips that entity — it is not
    a fatal error for the chunk finalization.

    No-op if .entities/ doesn't exist or no entities have a ve-worktree-<chunk>
    branch.

    Args:
        project_dir: Root project directory where .entities/ lives.
        chunk: Chunk name matching the ve-worktree-<chunk> branch.
    """
```

Implementation notes:
- Return early if `(project_dir / ".entities").exists()` is False.
- For each entity submodule dir (`.git` is a file):
  - Check if `ve-worktree-{chunk}` branch exists via `git rev-parse --verify`; skip if not.
  - Perform a no-checkout merge of `ve-worktree-{chunk}` into `main` using the same
    `merge_without_checkout` helper already imported from `orchestrator.merge` in worktree.py.
    Since we're in `entity_repo.py`, use `subprocess` directly or inline the plumbing steps:
    - `git merge-base main ve-worktree-{chunk}` → merge_base sha
    - `git merge-tree merge_base main ve-worktree-{chunk}` → tree sha (or conflict)
    - If tree sha (no conflict): create commit via `git commit-tree` and update `main` ref
    - If conflict: log warning, skip this entity
  - On success, delete the worktree branch: `git branch -d ve-worktree-{chunk}`.
- Do not push the entity — that's the operator's job via `ve entity push`.

> **Design note**: Alternatively, reuse `merge_without_checkout` from `orchestrator.merge`
> by importing it. Evaluate during implementation whether the import path is clean
> (entity_repo → orchestrator.merge creates a cross-layer dependency). If awkward,
> inline the git plumbing steps (~10 lines) directly in `merge_entity_worktree_branches`.

Location: `src/entity_repo.py` near `merge_entity_worktree_branches`.

### Step 4: Call `init_entity_submodules_in_worktree()` from `WorktreeManager._create_single_repo_worktree()`

In `src/orchestrator/worktree.py`, import the new function at the top of the file (near other
`entity_repo` imports — check if any already exist, or add new import):

```python
from entity_repo import init_entity_submodules_in_worktree, merge_entity_worktree_branches
```

In `_create_single_repo_worktree()`, after the `git worktree add` block succeeds (before
`_lock_worktree`):

```python
# Chunk: docs/chunks/entity_worktree_support - Initialize entity submodules in worktree
init_entity_submodules_in_worktree(worktree_path, chunk)
```

Also call in `recreate_worktree_from_branch()` after the worktree is recreated (so recovered
worktrees also have entity support).

For task context (`_create_task_context_worktrees()`): after each per-repo `git worktree add`
loop iteration, call `init_entity_submodules_in_worktree(repo_worktree_path, chunk)`. This
handles multi-repo task contexts where each repo worktree may have its own entities.

### Step 5: Call `merge_entity_worktree_branches()` from `WorktreeManager._merge_to_base_single_repo()`

In `_merge_to_base_single_repo()`, after the `self._merge_without_checkout(...)` call succeeds
and before the branch deletion:

```python
# Chunk: docs/chunks/entity_worktree_support - Merge entity worktree branches after chunk merge
merge_entity_worktree_branches(self.project_dir, chunk)
```

For multi-repo merges (`_merge_to_base_multi_repo()`): call
`merge_entity_worktree_branches(repo_path, chunk)` for each repo after its merge succeeds.
If the entity merge logs a warning (conflict), the chunk merge should still proceed — entity
merge conflicts are surfaced via log, not as exceptions.

### Step 6: Write tests in `tests/test_entity_worktree.py`

Create a new test file. Use `conftest.py` helpers (`make_ve_initialized_git_repo`) and helpers
from `test_entity_submodule.py` (`make_entity_origin`). Check conftest first for reusable
fixtures; extract anything needed in multiple test files to conftest.

**Test classes and methods**:

```
class TestInitEntitySubmodulesInWorktree:
    def test_no_op_when_no_entities_dir(...)
        # worktree with no .entities/ — function returns without error
    def test_no_op_when_entities_dir_empty(...)
        # .entities/ exists but empty — function returns without error
    def test_initializes_entity_submodule(...)
        # project with attached entity, worktree created, entity dir populated
    def test_entity_on_working_branch_after_init(...)
        # entity in worktree is on ve-worktree-<chunk> branch (not detached HEAD)
    def test_multiple_entities_all_initialized(...)
        # two entities attached; both initialized in worktree on working branches
    def test_worktree_entity_independent_from_main_checkout(...)
        # commit in worktree entity doesn't affect main checkout entity

class TestMergeEntityWorktreeBranches:
    def test_no_op_when_no_entities_dir(...)
        # function is no-op
    def test_no_op_when_no_worktree_branch(...)
        # entity exists but no ve-worktree-<chunk> branch — skip silently
    def test_merges_entity_changes_to_main(...)
        # entity has commits on worktree branch; after merge, entity main has those commits
    def test_deletes_worktree_branch_after_merge(...)
        # ve-worktree-<chunk> branch deleted after successful merge
    def test_conflict_logs_warning_does_not_raise(...)
        # conflicting edits in entity main and worktree branch — no exception, warning logged

class TestWorktreeManagerEntityIntegration:
    def test_create_worktree_initializes_entities(...)
        # WorktreeManager.create_worktree() on project with entity → entity initialized
    def test_finalize_includes_entity_submodule_pointer(...)
        # finalize_work_unit() includes entity submodule pointer in commit
    def test_merge_to_base_merges_entity_branches(...)
        # full end-to-end: create worktree, entity commits, finalize, merge to base,
        # entity main has the changes
```

Each test uses real git repos (via tmp_path) — consistent with the existing worktree test
pattern. No mocking.

### Step 7: Run tests and fix issues

```bash
uv run pytest tests/test_entity_worktree.py -v
uv run pytest tests/ -x  # full suite to catch regressions
```

Fix any issues discovered. Common pitfall: `git submodule update --init` in a worktree
requires that the parent repo's submodule registration is committed (not just staged). Tests
should commit `.gitmodules` and the entity submodule entry before creating the worktree.

### Step 8: Add backreference comments

Add `# Chunk: docs/chunks/entity_worktree_support` comments at method level for all new
and modified methods in `entity_repo.py` and `worktree.py`.

## Dependencies

- `entity_attach_detach` (DONE): provides `attach_entity()`, the submodule attach mechanism
  that `git submodule update --init` depends on being committed.
- `entity_shutdown_wiki` (DONE): entity-shutdown commits wiki changes to entity repo —
  this chunk assumes that behavior works correctly within worktrees.

## Risks and Open Questions

- **Import direction**: `entity_repo.py` importing from `orchestrator.merge` creates a
  cross-layer dependency (entity module importing orchestrator module). Evaluate during
  implementation; if awkward, inline the git plumbing (merge-base + merge-tree +
  commit-tree) directly in `merge_entity_worktree_branches`.

- **Submodule init in task context**: Task context worktrees use `_create_task_context_worktrees()`;
  the entity call needs to be added per-repo. The investigation only tested single-repo worktrees.
  Verify the task context path works or note it as a future extension.

- **`git submodule update --init` requires committed submodule**: The submodule must be committed
  in the parent repo (not just staged) for the worktree to initialize it. Tests must commit
  `.gitmodules` before creating the worktree. Document this constraint.

- **`commit_changes()` and entity pointer staging**: `git add -A` in the worktree stages
  modified submodule pointers if the entity has new commits. The existing comment in
  `commit_changes()` notes an edge case where submodule entries appear in `git status` but
  aren't staged. Verify entity pointer changes pass through cleanly in integration tests.

- **Concurrent worktrees with same entity**: The GOAL.md lists this as a success criterion.
  The test `test_worktree_entity_independent_from_main_checkout` covers isolation.
  The `merge_entity_worktree_branches` conflict handling (warn + skip) covers the merge case.
  Document this as a known limitation: when two worktrees modify the same entity, only the
  first to merge will succeed cleanly; the second requires manual resolution.

## Deviations

- **Step 3 — `merge_entity_worktree_branches` signature change**: Added an optional
  `worktree_path: Path` parameter. The plan called for operating on the project entity
  directly, but testing revealed that `git submodule update --init` in an orchestrator
  worktree creates a **separate git module** at a worktree-specific path
  (`project/.git/worktrees/<wt>/modules/.entities/<name>`), not a linked worktree of
  the main module (`project/.git/modules/.entities/<name>`). The two module repos do
  not share a ref namespace, so the `ve-worktree-<chunk>` branch created in the worktree
  entity was invisible from the project entity. The fix: fetch the branch from the
  worktree entity into the project entity using `git fetch <worktree-entity-path>` before
  merging. Callers pass the worktree path explicitly; it defaults to
  `project_dir/.ve/chunks/<chunk>/worktree` for the single-repo case.
