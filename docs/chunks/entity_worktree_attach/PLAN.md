# Implementation Plan

## Approach

This chunk replaces submodule-based entity attach with a git worktree-based
attach, and rips out all submodule machinery in the same pass — a clean
break per the narrative's design.

The shape of the change:

1. **New module** `src/cli/entity_worktree.py` owns the new attach/detach
   logic. It is deliberately a fresh module rather than an in-place rewrite
   of `entity_repo.attach_entity`/`detach_entity` because:
   - The new API takes only the entity *name* (no `repo_url`) — the URL is
     derived via `cli.canonical_clone` from `git_base`/`name`.
   - The new code never touches `.gitmodules`, `git submodule`, or
     `.git/modules/`. Keeping it physically separate from the submodule
     machinery in `entity_repo.py` makes the clean break legible.
   - The module exposes a process-level `do_attach(name, ...) ->
     AttachResult` that the downstream `entity_claude_autoattach` chunk
     wires into `ve entity claude`.

2. **CLI rewrite**. `src/cli/entity.py`'s `attach` and `detach` commands are
   rewritten to take `NAME` (not `REPO_URL`) and delegate to
   `cli.entity_worktree.do_attach`/`do_detach`. The CLI translates
   `CanonicalCloneError` subclasses, `ValueError`s, and `WorktreeAttachError`s
   into distinct `click.ClickException` messages.

3. **Submodule removal**. Every submodule-aware code path is deleted:
   - `entity_repo.attach_entity` and `entity_repo.detach_entity` — gone.
   - `entity_repo.list_attached_entities` — rewritten to walk
     `.entities/<name>` as worktrees (look for `.git` *file* whose
     `gitdir:` line points into the canonical clone's `worktrees/`).
   - `entity_repo.init_entity_submodules_in_worktree` and
     `merge_entity_worktree_branches` — gone. The orchestrator no longer
     needs to bridge per-orch-worktree submodule modules because worktree
     attaches don't create per-orch-worktree state in the entity at all
     (the canonical clone is shared across all project worktrees, and the
     attach-side branches live in the canonical clone's ref namespace).
   - Call sites in `src/orchestrator/worktree.py` and import lines —
     gone, along with their `# Chunk: entity_worktree_support`
     backreferences (that subsystem's intent no longer exists; we leave
     the chunk doc but its code references are no longer current).
   - The list command's "legacy plain-directory entities" branch is kept
     (still useful for entity dirs created by `ve entity create`/`migrate`
     before attach), but its `submodule_names` set is replaced with
     `worktree_names`.

4. **Project-scoped branch naming**. The branch the worktree checks out is
   named `ve-attach/<project-slug>` where `<project-slug>` is the project
   directory's basename with non-alphanumeric characters replaced by `-`
   and lowercased. Examples: `/Users/btaylor/Projects/vibe-engineer` →
   `ve-attach/vibe-engineer`; `/var/tmp/Foo Bar` → `ve-attach/foo-bar`.

   - Constraint check: git allows `/` in branch names; two worktrees of
     the same canonical clone cannot share a branch; the slug is derived
     deterministically from project path so the same project always
     resolves to the same branch.
   - Path-basename collisions are rare in practice (two projects named
     `foo` on the same machine would collide). The risk is documented in
     "Risks and Open Questions"; a path-hash fallback is left for a
     follow-up.
   - Branch creation: `git worktree add -b ve-attach/<slug> <dest>
     <base-ref>` where `<base-ref>` is the canonical clone's default
     branch (resolved via `git -C <canonical> symbolic-ref refs/remotes/origin/HEAD`
     falling back to `main` if that fails).
   - The `entity_claude_autoattach` chunk gets the slug helper
     (`project_slug(project_dir: Path) -> str`) and branch helper
     (`attach_branch_name(project_dir: Path) -> str`) as importable
     functions so it can predict the branch name without re-attaching.

5. **Re-attach semantics**: **idempotent no-op**. Rationale:
   - The narrative's whole point is that `ve entity claude` auto-attaches
     on demand. If re-attach raised an error, the auto-attach pathway
     would have to special-case "already attached" everywhere. Idempotent
     no-op makes the composition trivial.
   - Detection: `do_attach` checks whether `.entities/<name>` exists and
     is a worktree whose `gitdir` points into the canonical clone's
     `worktrees/` directory. If yes, return `AttachResult(name, path,
     already_attached=True)`. CLI prints a friendly "already attached"
     message.
   - The legacy "plain directory" case (a `.entities/<name>` that is not
     a git worktree at all) is treated as an error — we refuse to clobber
     it, matching the canonical-clone helper's stance. The user must
     remove/rename the leftover by hand.

6. **Migration documentation**. README gains an "Upgrading from 0.x
   (pre-worktree) entities" section under or near the existing entity
   commands. It tells pre-1.0 users: detach with the old `ve`, upgrade,
   set `~/.ve-config.toml`, re-attach. The chunk directory also retains
   a `MIGRATION.md` for archaeology.

7. **Tests**. New file `tests/test_entity_worktree_attach.py` exercises
   the new module directly (no CLI). New file
   `tests/test_entity_worktree_attach_cli.py` exercises the rewritten
   `ve entity attach`/`detach` CLI surfaces. The five tests required by
   the success criteria all live in these files. Old submodule-attach
   tests are deleted:
   - `tests/test_entity_submodule.py` — fully deleted (its subject matter
     no longer exists).
   - `tests/test_entity_attach_detach_cli.py` — fully deleted, replaced
     by the new CLI test file.
   - `tests/test_entity_worktree.py` — deleted; subject is the now-deleted
     `init_entity_submodules_in_worktree`/`merge_entity_worktree_branches`.
   - `tests/test_entity_push_pull_cli.py` — the helper
     `make_entity_submodule` / `make_entity_submodule_no_origin` is
     rewritten to attach via the new worktree path. The 0.x submodule
     fixture is gone; push/pull tests themselves keep testing
     `push_entity`/`pull_entity` against the worktree-attached entity.

8. **Test isolation**: every test that calls into `cli.entity_worktree`
   passes an explicit `config_path=` (forwarded into
   `ensure_canonical_clone`) pointing at a `tmp_path`-scoped config so
   the suite never touches `~/.ve-config.toml`. The CLI commands gain a
   hidden `--config` flag for the same reason.

## Subsystem Considerations

No existing subsystems govern this code. The new module is small enough
(<300 lines projected) that a subsystem doesn't yet earn its keep — the
canonical-clone seam is the single architectural pattern, and that
substrate already lives in `cli.canonical_clone`.

## Sequence

### Step 1: Add slug/branch helpers and AttachResult dataclass

Location: `src/cli/entity_worktree.py` (new module).

- `def project_slug(project_dir: Path) -> str`: lowercases the directory
  basename, replaces every non-`[a-z0-9]` run with `-`, strips leading/
  trailing `-`. Raises `ValueError` if the result is empty (defensive —
  unlikely outside of pathological paths).
- `def attach_branch_name(project_dir: Path) -> str`: returns
  `f"ve-attach/{project_slug(project_dir)}"`.
- `@dataclass(frozen=True) class AttachResult`: fields `name: str`,
  `entity_path: Path`, `canonical_clone: Path`, `branch: str`,
  `already_attached: bool`.
- Module docstring + `# Chunk: docs/chunks/entity_worktree_attach`
  backreference.

### Step 2: Implement `do_attach` against the canonical clone

In `src/cli/entity_worktree.py`:

```python
def do_attach(
    name: str,
    project_dir: Path,
    *,
    config_path: Path | None = None,
) -> AttachResult:
    """Attach <name> to project_dir as a worktree of the canonical clone."""
```

Steps:

1. Validate `project_dir` is a git repo via `git -C <project_dir> rev-parse --git-dir`. Raise `WorktreeAttachError` on failure.
2. Resolve canonical clone via `ensure_canonical_clone(name, config_path=config_path)`. CanonicalCloneError subclasses propagate.
3. Compute `entity_path = project_dir / ".entities" / name` and `branch = attach_branch_name(project_dir)`.
4. **Idempotent re-attach**: if `entity_path.exists()`:
   - If `_is_worktree_of(entity_path, canonical_clone)`: return `AttachResult(..., already_attached=True)`.
   - Otherwise raise `WorktreeAttachError("'.entities/<name>' already exists but is not an attached worktree; remove or rename it and retry")`.
5. Ensure `entity_path.parent` exists (`.entities/`).
6. Resolve the canonical clone's default branch ref:
   - Try `git -C <canonical> symbolic-ref refs/remotes/origin/HEAD` →
     strip `refs/remotes/origin/` prefix.
   - Fall back to `main` if that ref isn't set (e.g. a bare canonical
     clone with no remote — supported for local-only testing).
7. Check whether `branch` already exists in the canonical clone:
   - `git -C <canonical> show-ref --verify --quiet refs/heads/<branch>`.
   - If yes (e.g. detach left it behind on a previous run): use `git
     worktree add <entity_path> <branch>`.
   - If no: use `git worktree add -b <branch> <entity_path> <base-ref>`.
8. Run the resulting `git worktree add ...` in the canonical clone's
   working tree. On failure, raise `WorktreeAttachError` with stderr
   appended.
9. Return `AttachResult(name=name, entity_path=entity_path,
   canonical_clone=canonical, branch=branch, already_attached=False)`.

Helper `_is_worktree_of(entity_path: Path, canonical: Path) -> bool`:
reads `.git` as a file, parses `gitdir: …` line, checks the gitdir path
starts with `<canonical>/.git/worktrees/`.

### Step 3: Implement `do_detach`

```python
def do_detach(
    name: str,
    project_dir: Path,
    *,
    config_path: Path | None = None,
    force: bool = False,
) -> None:
```

Steps:

1. `entity_path = project_dir / ".entities" / name`. If missing, raise
   `WorktreeAttachError("Entity '<name>' is not attached at '<entity_path>'")`.
2. Resolve canonical clone path: read `config_path` via `load_config()`,
   compute `canonical = cfg.entities_dir / name`. If the canonical clone
   is missing on disk, fall through to a "best effort cleanup": delete
   `entity_path` directly (no `git worktree remove` to call) and warn.
3. Check `_is_worktree_of(entity_path, canonical)`. If False, raise a
   `WorktreeAttachError("'<entity_path>' is not an attached worktree")`.
4. Uncommitted-changes check: run `git -C <entity_path> status --porcelain`.
   If non-empty and `force=False`, raise `WorktreeAttachError("Entity
   '<name>' has uncommitted changes. Use --force to detach anyway.")`.
5. Compute `branch = attach_branch_name(project_dir)`.
6. Run `git -C <canonical> worktree remove [--force] <entity_path>`.
7. Delete the project-scoped branch in the canonical clone (`git -C
   <canonical> branch -D <branch>`); ignore "branch not found" failure
   silently — re-detach of an already-half-cleaned state must succeed.

### Step 4: Rewrite the CLI surfaces

In `src/cli/entity.py`:

- Replace the body of `attach` with a `NAME`-only signature:
  ```
  @entity.command("attach")
  @click.argument("name")
  @click.option("--config", "config_path", ...)
  @click.option("--project-dir", ...)
  def attach(name, config_path, project_dir):
      project_dir = resolve_entity_project_dir(project_dir)
      from cli.entity_worktree import do_attach
      from cli.canonical_clone import (
          AuthFailure, MissingRemoteRepo, NetworkFailure, CanonicalCloneError,
      )
      from cli.config import ConfigError
      try:
          result = do_attach(name, project_dir, config_path=config_path)
      except (AuthFailure, MissingRemoteRepo, NetworkFailure,
              CanonicalCloneError, ConfigError, ValueError,
              WorktreeAttachError) as exc:
          raise click.ClickException(str(exc))
      if result.already_attached:
          click.echo(f"Entity '{name}' is already attached at {result.entity_path}")
      else:
          click.echo(f"Attached entity '{name}' at {result.entity_path}")
          click.echo(f"  Branch: {result.branch}")
          click.echo(f"  Canonical clone: {result.canonical_clone}")
  ```
- Rewrite `detach` similarly: takes `NAME` and `--force`, delegates to
  `do_detach`.
- Update `list_entities` to call a new
  `entity_repo.list_attached_entities` (rewritten in step 5) and rename
  the `submodule_names` local to `worktree_names`. Strip the
  `# Chunk: entity_attach_detach - Enhanced list with submodule status`
  comment, update to `# Chunk: docs/chunks/entity_worktree_attach`.
- Update CLI test imports as needed for the new file.

### Step 5: Rip out submodule code from `entity_repo.py`

In `src/entity_repo.py`:

- Delete `attach_entity` (submodule version). Replace with a deprecation
  stub? No — clean break per the narrative. Delete outright.
- Delete `detach_entity`.
- Delete `init_entity_submodules_in_worktree` and
  `merge_entity_worktree_branches`.
- Rewrite `list_attached_entities` to return `AttachedEntityInfo` for
  each `.entities/<d>` whose `.git` file points at a worktree under the
  canonical clone. Use the existing `remote_url` / `specialization` /
  `status` fields — they all still work because the worktree's `git -C`
  invocations resolve to the canonical clone.
- Update `AttachedEntityInfo` docstring from "git submodule" to "git
  worktree".
- Update the module-level docstring to drop the "submodules" mention.
- Remove the `shutil` import only if no other code path uses it (it does
  — keep).

### Step 6: Strip submodule call sites from orchestrator

In `src/orchestrator/worktree.py`:

- Delete the `from entity_repo import init_entity_submodules_in_worktree,
  merge_entity_worktree_branches` import.
- Delete the three `init_entity_submodules_in_worktree(...)` calls and
  the two `merge_entity_worktree_branches(...)` calls. The associated
  `# Chunk: entity_worktree_support` backreference comments go with them.
- The `# Chunk: docs/chunks/finalize_double_commit - Prune after rmtree
  fallback for submodule worktrees` comment is kept — that chunk
  governs the rmtree fallback behavior, which remains valuable for
  orchestrator worktrees that happen to contain entity worktrees
  (different mechanism, but same observable symptom: `git worktree
  remove` fails when the worktree contains another worktree).

### Step 7: Update test fixtures and add new tests

Delete:
- `tests/test_entity_submodule.py`
- `tests/test_entity_attach_detach_cli.py`
- `tests/test_entity_worktree.py`

Add `tests/test_entity_worktree_attach.py` with:

- `test_attach_fresh_canonical_clone_present`: pre-seed the canonical
  clone in `entities_dir/<name>` (a bare-cloned working repo); call
  `do_attach`; assert `.entities/<name>` is a worktree (`.git` is a file
  containing `gitdir:` pointing into the canonical's `worktrees/`).
- `test_attach_invokes_canonical_clone_helper`: set up a bare repo at
  `<git_base>/<name>.git`; ensure `entities_dir/<name>` does not pre-exist;
  call `do_attach`; assert the canonical clone was created AND the
  worktree exists.
- `test_attach_idempotent_no_op`: call `do_attach` twice; second call
  returns `AttachResult(already_attached=True)` and does not error.
- `test_attach_refuses_existing_plain_directory`: write a non-git
  directory at `.entities/<name>`; assert `do_attach` raises
  `WorktreeAttachError` with a message naming the conflicting path.
- `test_detach_removes_worktree_and_branch`: attach, then detach;
  assert `.entities/<name>` is gone; assert `entities_dir/<name>`
  (canonical clone) still exists; assert the project-scoped branch
  is gone from the canonical clone.
- `test_detach_refuses_uncommitted_without_force`: write a dirty file
  inside the worktree; assert `do_detach` without `force=True` raises.
- `test_detach_force_proceeds`: same as above but with `force=True`;
  assert the worktree is removed.
- `test_two_projects_share_canonical_clone`: set up two project_dirs;
  attach the same entity to both; assert both `.entities/<name>` exist
  and are worktrees of the same canonical clone; assert their branches
  differ (`ve-attach/<slug-a>` vs `ve-attach/<slug-b>`); assert detach
  in project A leaves project B's worktree intact.
- `test_project_slug_lowercases_and_dashes`: unit test for the slug
  helper.
- `test_attach_resolves_default_branch_via_origin_HEAD`: canonical clone
  has `origin/HEAD` pointing at `main`; the attach branch is created
  from `main`.

Add `tests/test_entity_worktree_attach_cli.py` with parallel coverage at
the Click level:

- `test_attach_cli_happy_path`
- `test_attach_cli_canonical_clone_missing_repo` (asserts the
  `MissingRemoteRepo` error message reaches the CLI cleanly)
- `test_attach_cli_already_attached_prints_friendly_message`
- `test_detach_cli_happy_path`
- `test_detach_cli_uncommitted_without_force`
- `test_list_cli_shows_worktree_attached_entity`

Rewrite `tests/test_entity_push_pull_cli.py`:

- `make_entity_submodule` → `make_attached_entity` (and rename the
  no-origin helper). Use `do_attach` instead of `git submodule add`.
- Tests that hit the no-origin path just create the entity directly in
  `.entities/<name>/` (no attach) — the helper already does this for
  legacy entities, no submodule mechanism involved.

### Step 8: Documentation updates

- README: add a short "Upgrading from 0.x entities (pre-worktree)"
  subsection that says: "Detach each entity using your existing 0.x
  `ve` binary, upgrade `ve` to 1.0+, set `~/.ve-config.toml`, then
  `ve entity attach <name>` for each entity you want re-attached. 1.0
  does not migrate submodule attachments — they will appear as 'not
  attached' until re-attached."
- `docs/chunks/entity_worktree_attach/MIGRATION.md`: same content,
  preserved as a chunk artifact for archaeology.

### Step 9: Validation pass

Run:

- `git grep -n 'submodule' src/` — expect zero matches in the entity
  attach/detach paths. Matches in
  `src/cli/__init__.py` ("each submodule contains a command group")
  refer to Python submodules and are kept.
- `uv run pytest tests/` — expect `31 failed, M passed` where the 31
  failures are the inherited baseline failures (NOT submodule-attach
  tests, which we deleted).
- `uv run ve config show` and `uv run ve entity attach <test-name>`
  smoke-test against a local bare repo.

### Step 10: Update `code_paths` in GOAL.md before complete

Replace `code_paths` with the reality:

```yaml
code_paths:
  - src/cli/entity_worktree.py
  - src/cli/entity.py
  - src/entity_repo.py
  - src/orchestrator/worktree.py
  - tests/test_entity_worktree_attach.py
  - tests/test_entity_worktree_attach_cli.py
  - tests/test_entity_push_pull_cli.py
  - docs/chunks/entity_worktree_attach/MIGRATION.md
  - README.md
```

## Dependencies

- `entity_config_toml` (ACTIVE) — `cli.config.load_config`.
- `entity_canonical_clone` (ACTIVE) — `cli.canonical_clone.ensure_canonical_clone`
  and its exception hierarchy.

## Risks and Open Questions

- **Project-slug collisions**. Two projects named `foo` on the same machine
  attached to the same entity would collide on `ve-attach/foo`. Acceptable
  for 1.0 — the failure mode is a clear `git worktree add` error pointing
  at the existing branch. A path-hash variant is a future enhancement.
- **`origin/HEAD` may be unset** in canonical clones produced by some
  hosts. Fallback to `main` is documented; if `main` doesn't exist either,
  the `git worktree add` call surfaces the real error to the user.
- **Worktree-of-canonical detection** relies on parsing `.git`-file
  content. The `gitdir:` prefix matching is sensitive to symlinks in the
  entities_dir path. We resolve both paths via `Path.resolve()` before
  comparing.
- **Orchestrator worktrees with attached entities**. Removing
  `init_entity_submodules_in_worktree` means an orch-created worktree
  of the project no longer auto-attaches entities. This is OK because
  attached entities now live as worktrees under the canonical clone;
  the canonical clone is referenced from both the main project tree
  and the orch tree via independent worktrees, but each worktree has
  the same `.entities/<name>/.git` file (which is committed to the
  project repo? — no, `.entities/` is *not* tracked by the project in
  the new model; it's a local-only working artifact). This is a behavior
  shift worth noting: pre-worktree, submodule pointers were tracked in
  the project repo. Post-worktree, attachment state is local and
  ephemeral. **Decision**: do not auto-create attachments in orch
  worktrees; if the project's chunks need an entity inside an orch
  worktree, the user re-attaches inside that worktree. This is
  documented in the chunk and may grow a follow-up if real friction
  emerges.

## Deviations

(Populated during implementation if any.)
