
<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add `ve entity attach`, `ve entity detach`, and an enhanced `ve entity list` to the existing
entity CLI. Business logic (git submodule operations) lives in `src/entity_repo.py`, with thin
Click wrappers in `src/cli/entity.py`.

The submodule lifecycle was fully prototyped in the investigation's H2 experiment — attach,
detach, push/pull, fork/merge, and worktree compatibility are all verified. This chunk
implements the verified design.

Key patterns:
- Git subprocess calls follow the existing `_run_git` / `_run_git` helper pattern in
  `entity_repo.py`.
- **DEC-005**: Neither `attach` nor `detach` auto-commits. The user decides when to commit
  `.gitmodules` and the gitlink entry.
- **DEC-002**: We validate the CWD is a git repo before submodule operations, but VE docs
  don't require git. The entity *repo* commands require it; the entity *knowledge* commands don't.

## Subsystem Considerations

No existing subsystem directly governs submodule operations. The `cross_repo_operations`
subsystem (`docs/subsystems/cross_repo_operations`) is the closest candidate — check it
before implementing to see if any patterns apply and record a backreference if so.

## Sequence

Follow the TDD cycle: write failing tests → implement → see tests go green.

---

### Step 1: Write unit tests for `derive_entity_name_from_url` (red phase)

**File**: `tests/test_entity_repo.py` (extend existing file)

Add a `TestDeriveEntityNameFromUrl` class with cases that must fail before implementation:

- HTTPS URL with `.git` → last component minus suffix (`entity-slack-watcher.git` → `slack-watcher`)
- HTTPS URL without `.git` → last component (`my-specialist` → `my-specialist`)
- SSH URL (`git@github.com:user/my-entity.git`) → `my-entity`
- Local relative path (`../local-entity`) → `local-entity`
- Local absolute path (`/some/path/to/my-entity`) → `my-entity`
- Trailing slash is stripped before extraction (`../my-agent/`) → `my-agent`
- Generic name that doesn't start with `entity-` is returned as-is
- Name starting with `entity-` has prefix stripped (`entity-ops-specialist` → `ops-specialist`)

Run `uv run pytest tests/test_entity_repo.py::TestDeriveEntityNameFromUrl` — confirm all fail
(NameError since the function doesn't exist yet).

---

### Step 2: Implement `derive_entity_name_from_url` in `entity_repo.py`

**File**: `src/entity_repo.py`

```python
# Chunk: docs/chunks/entity_attach_detach - Name derivation for entity attach
def derive_entity_name_from_url(url: str) -> str:
    """Derive an entity name from a repo URL or local path.

    Algorithm:
    1. Strip trailing slash
    2. Take the last path component (after the last '/')
    3. Strip '.git' suffix if present
    4. Strip 'entity-' prefix if present
    5. Return the result (validation against ENTITY_REPO_NAME_PATTERN happens at call site)
    """
```

Run tests — confirm they pass.

---

### Step 3: Add `AttachedEntityInfo` model to `entity_repo.py`

**File**: `src/entity_repo.py`

Add a Pydantic `BaseModel` (per DEC-008):

```python
class AttachedEntityInfo(BaseModel):
    name: str
    remote_url: Optional[str]       # None if not a submodule or no remote
    specialization: Optional[str]   # From ENTITY.md frontmatter
    status: str                     # "clean" | "uncommitted" | "ahead" | "unknown"
```

No behavioral tests needed here (data class). Only add it when Step 4 tests reference it.

---

### Step 4: Write unit tests for `attach_entity`, `detach_entity`, `list_attached_entities` (red phase)

**File**: `tests/test_entity_submodule.py` (new file)

These tests need a real git environment. Add a module-level `_git()` helper (same pattern as
`test_entity_repo.py`) and a `make_entity_origin` fixture that:
1. Creates an entity repo via `create_entity_repo`
2. Clones it to a bare repo (simulating a hosted origin)
3. Configures the source repo to point at the bare clone as `origin`
4. Returns `(entity_src, bare_origin)` so tests can use the bare origin's path as the URL

Also add a `make_project_git_repo` fixture (reuse `make_ve_initialized_git_repo` from
conftest.py).

**`TestAttachEntity`** — test cases:
- `test_attach_clones_into_entities_dir`: after attach, `.entities/<name>/` exists and
  `is_entity_repo(.entities/<name>/)` is True
- `test_attach_creates_entities_dir_if_missing`: works even if `.entities/` doesn't exist yet
- `test_attach_returns_correct_path`: return value is `project/.entities/<name>`
- `test_attach_registers_submodule`: `.gitmodules` file exists after attach and contains the URL
- `test_attach_rejects_non_git_project`: raises `RuntimeError` if project dir has no `.git`
- `test_attach_rejects_non_entity_repo`: raises `ValueError` if the cloned repo lacks ENTITY.md
  (attach should call `is_entity_repo` after clone and fail cleanly — using `deinit`+`rm` to
  clean up the partial submodule)
- `test_attach_with_local_path_url`: accepts a relative path as the URL

**`TestDetachEntity`** — test cases:
- `test_detach_removes_entities_dir`: after detach, `.entities/<name>/` no longer exists
- `test_detach_removes_from_gitmodules`: `.gitmodules` no longer references the submodule
  (or the file is gone if it was the only entry)
- `test_detach_refuses_uncommitted_changes`: raises `RuntimeError` when the submodule has
  uncommitted changes and `force=False`
- `test_detach_force_proceeds_with_uncommitted_changes`: with `force=True`, detach succeeds
  even when there are uncommitted changes
- `test_detach_raises_if_entity_not_found`: raises `ValueError` when `.entities/<name>/`
  doesn't exist

**`TestListAttachedEntities`** — test cases:
- `test_list_returns_empty_for_no_entities`: returns `[]` when `.entities/` is missing
- `test_list_returns_attached_entities`: after attaching two entities, list returns both with
  correct `name`, `remote_url`, and `specialization`
- `test_list_status_clean_for_fresh_attach`: freshly attached entity has status `"clean"`
- `test_list_status_uncommitted_after_modification`: after writing an untracked file in the
  submodule, status is `"uncommitted"`

Run `uv run pytest tests/test_entity_submodule.py` — confirm all fail (ImportError /
AttributeError since functions don't exist yet).

---

### Step 5: Implement `attach_entity`, `detach_entity`, `list_attached_entities` in `entity_repo.py`

**File**: `src/entity_repo.py`

Add a `_run_git_output` helper (returns stdout string, raises on failure) alongside `_run_git`.

**`attach_entity(project_dir: Path, repo_url: str, name: str) -> Path`**:

```
# Chunk: docs/chunks/entity_attach_detach - Submodule attach implementation
```

1. Validate `project_dir` is a git repo (run `git rev-parse --git-dir`; raise `RuntimeError` if
   it fails).
2. Ensure `.entities/` directory exists (`mkdir` with `exist_ok=True`). Git submodule add will
   create the target, but the parent must exist for the path to be unambiguous.
3. Run `git submodule add <repo_url> .entities/<name>` via `_run_git`. On failure, raise
   `RuntimeError` with the stderr output.
4. Validate the cloned repo is an entity repo via `is_entity_repo(project_dir / ".entities" / name)`.
   If not valid:
   - Run cleanup: `git submodule deinit -f .entities/<name>`, `git rm -f .entities/<name>`,
     remove `.git/modules/.entities/<name>` if it exists.
   - Raise `ValueError("Attached repo is not a valid entity repo — missing ENTITY.md")`.
5. Return `project_dir / ".entities" / name`.

**`detach_entity(project_dir: Path, name: str, force: bool = False) -> None`**:

```
# Chunk: docs/chunks/entity_attach_detach - Submodule detach implementation
```

1. Check `.entities/<name>` exists; raise `ValueError` if not.
2. Check for uncommitted changes inside the submodule:
   - Run `git -C .entities/<name> status --porcelain`; if output is non-empty and `force=False`,
     raise `RuntimeError("Entity '<name>' has uncommitted changes. Use force=True to override.")`.
3. Full removal sequence (from investigation H2):
   - `git submodule deinit -f .entities/<name>` — removes entry from `.git/config`
   - `git rm -f .entities/<name>` — removes `.gitmodules` entry, gitlink, and tracked directory
   - Remove `.git/modules/.entities/<name>` tree if it exists (`shutil.rmtree`)

**`list_attached_entities(project_dir: Path) -> list[AttachedEntityInfo]`**:

```
# Chunk: docs/chunks/entity_attach_detach - List attached entity submodules
```

1. If `.entities/` doesn't exist, return `[]`.
2. Iterate over subdirectories of `.entities/`.
3. For each subdirectory `d`:
   - Skip if not a directory.
   - Determine if it's a submodule: check if `(d / ".git").is_file()` (submodule checkout has
     a `.git` *file*, not a directory, pointing to the parent repo's module cache).
   - If submodule: get remote URL via `git -C <d> remote get-url origin` (return `None` on
     failure).
   - Get specialization via `read_entity_metadata(d).specialization` wrapped in try/except
     (return `None` on failure — entity may be corrupt or non-entity submodule).
   - Get status:
     - Run `git -C <d> status --porcelain`; if non-empty → `"uncommitted"`
     - Else run `git -C <d> log @{u}.. --oneline 2>/dev/null`; if non-empty → `"ahead"`
     - Else → `"clean"`
     - On any subprocess failure → `"unknown"`
4. Return list of `AttachedEntityInfo` instances.

Run `uv run pytest tests/test_entity_submodule.py` — confirm all tests pass.

---

### Step 6: Write CLI integration tests (red phase)

**File**: `tests/test_entity_attach_detach_cli.py` (new file)

Use Click's `CliRunner` for all tests. These tests need a real git project dir, so use
`make_ve_initialized_git_repo` from conftest.py (not the isolated CliRunner filesystem — pass
`project_dir` explicitly to CLI commands via `--project-dir`).

Add a `make_bare_entity_origin` helper in the test file that creates an entity repo and bare
clone (reuse logic from `test_entity_submodule.py` — if both files need this, move it to
`conftest.py`).

**`TestAttachCLI`**:
- `test_attach_creates_entity_subdir`: exit code 0, `.entities/<name>/` exists
- `test_attach_derives_name_from_url`: no `--name` given; name is derived from URL
- `test_attach_with_explicit_name`: `--name specialist` overrides derived name
- `test_attach_prints_confirmation`: output contains entity name and specialization
- `test_attach_non_git_project_exits_nonzero`: non-zero exit with error message

**`TestDetachCLI`**:
- `test_detach_removes_entity_dir`: exit code 0, `.entities/<name>/` gone
- `test_detach_refuses_uncommitted_without_force`: exit code non-zero, informative message
- `test_detach_force_flag_proceeds`: `--force` succeeds even with uncommitted changes
- `test_detach_unknown_entity_exits_nonzero`: non-zero exit for unknown name

**`TestListCLI`** (testing enhanced `list` command):
- `test_list_shows_attached_entities_with_url`: after attach, list output includes entity name
  and remote URL
- `test_list_shows_status`: output contains status word ("clean", "uncommitted", or "ahead")
- `test_list_empty_for_no_entities`: "No entities found" (or similar) when `.entities/` is empty

Run `uv run pytest tests/test_entity_attach_detach_cli.py` — confirm all fail (ImportError for
`attach`/`detach` commands not yet registered).

---

### Step 7: Add `attach` and `detach` commands to `entity.py`

**File**: `src/cli/entity.py`

**`attach` command**:

```python
# Chunk: docs/chunks/entity_attach_detach - CLI attach command
@entity.command("attach")
@click.argument("repo_url")
@click.option("--name", default=None, help="Override derived entity name")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=None)
def attach(repo_url: str, name: str | None, project_dir: pathlib.Path | None) -> None:
    """Attach an entity repository to this project as a git submodule.

    REPO_URL is the URL or path to the entity's git repository.
    The entity is cloned into .entities/<name>/.
    """
```

Implementation:
1. Resolve `project_dir` via `resolve_entity_project_dir`.
2. If `name` is None, call `derive_entity_name_from_url(repo_url)`.
3. Call `entity_repo.attach_entity(project_dir, repo_url, name)`.
4. Read metadata: `entity_repo.read_entity_metadata(project_dir / ".entities" / name)`.
5. Print confirmation: `"Attached entity '<name>' from <url>"` and specialization if set.
6. Wrap in try/except for `ValueError` and `RuntimeError` → `click.ClickException`.

**`detach` command**:

```python
# Chunk: docs/chunks/entity_attach_detach - CLI detach command
@entity.command("detach")
@click.argument("name")
@click.option("--force", is_flag=True, default=False, help="Remove even if entity has uncommitted changes")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=None)
def detach(name: str, force: bool, project_dir: pathlib.Path | None) -> None:
    """Detach an entity repository from this project.

    NAME is the entity identifier (subdirectory under .entities/).
    Removes the git submodule cleanly. Refuses if the entity has
    uncommitted changes unless --force is given.
    """
```

Implementation:
1. Resolve `project_dir`.
2. Call `entity_repo.detach_entity(project_dir, name, force=force)`.
3. Print `"Detached entity '<name>'"`.
4. Wrap errors → `click.ClickException`.

---

### Step 8: Update `list_entities` command in `entity.py`

**File**: `src/cli/entity.py`

Replace the body of `list_entities` to show submodule-based entities with richer info:

1. Call `entity_repo.list_attached_entities(project_dir)` to get submodule entities.
2. For each `AttachedEntityInfo`:
   - Print: `  <name>  [<status>]  <specialization or ''>  <remote_url or ''>`
3. Fallback for legacy plain-directory entities: keep the existing `Entities(project_dir)`
   path for entries in `.entities/` that are *not* submodules (i.e., lack a `.git` file in the
   subdirectory). This ensures backward compatibility.
4. If nothing found anywhere: print `"No entities found"`.

Add backreference:
```python
# Chunk: docs/chunks/entity_attach_detach - Enhanced list with submodule status
```

---

### Step 9: Run full test suite

```bash
uv run pytest tests/test_entity_repo.py tests/test_entity_submodule.py tests/test_entity_attach_detach_cli.py -v
```

All tests must pass. Then run the full suite:

```bash
uv run pytest tests/
```

No regressions in existing entity tests (`test_entity_cli.py`, `test_entity_create_cli.py`,
`test_entity_repo.py`). Fix any failures before completing the chunk.

---

### Step 10: Update GOAL.md `code_paths`

Update `docs/chunks/entity_attach_detach/GOAL.md` frontmatter to reflect the actual files
touched:

```yaml
code_paths:
- src/cli/entity.py
- src/entity_repo.py
- tests/test_entity_submodule.py
- tests/test_entity_attach_detach_cli.py
```

## Dependencies

- `entity_repo_structure` chunk must be complete (it provides `create_entity_repo`,
  `is_entity_repo`, `read_entity_metadata`, `ENTITY_REPO_NAME_PATTERN`, and `_run_git` helper
  already in `entity_repo.py`). This chunk builds directly on that foundation.
- Standard library `shutil` (for `rmtree` during detach cleanup) — already available.
- No new third-party packages required.

## Risks and Open Questions

- **Git submodule add in test environment**: Tests use real git subprocess calls. The
  `conftest.py` `clean_git_environment` fixture strips `GIT_DIR`/`GIT_WORK_TREE` which is
  essential here — confirm it's `autouse=True` so it applies automatically.

- **`.git` file detection for submodule check**: Relying on `(d / ".git").is_file()` to detect
  submodules is a git implementation detail. It holds for standard submodule checkouts. If a
  user manually places a `.git` file in an entity dir, they'd get false positives — acceptable
  for now.

- **`@{u}` upstream reference in worktrees**: `git log @{u}..` requires an upstream tracking
  branch. Freshly attached submodules may not have one set. Wrap this call in a try/except and
  fall back to `"clean"` or `"unknown"` status when no upstream is configured.

- **DEC-005 compliance**: Both `attach` and `detach` leave uncommitted changes in the parent
  repo's index. The user must explicitly commit `.gitmodules` and the gitlink. The CLI output
  should remind the user of this: `"Review changes with git status, then commit when ready."`.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
