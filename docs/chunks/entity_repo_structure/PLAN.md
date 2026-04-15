

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk introduces **standalone git-repo-based entity creation** alongside the
existing `.entities/`-directory pattern. The core deliverable is a new
`src/entity_repo.py` module with a clean API for creating entity repos, detecting
them, and reading their metadata. The `ve entity create` CLI command is updated to
use this new module, producing a standalone git repo in the working directory
rather than a subdirectory of `.entities/`.

**What we're not changing**: The existing `Entities` class in `src/entities.py`
and its `.entities/<name>/` directory management is left intact. Future chunks
(`entity_attach_detach`, `entity_memory_migration`) will wire the two systems
together. This chunk focuses on creating the "blank entity" artifact that is the
input to those workflows.

**Patterns used**:
- Pydantic `BaseModel` for `ENTITY.md` frontmatter (DEC-008)
- `subprocess` for git operations (same pattern used in orchestrator and entity
  session code)
- `render_template` from `template_system` for wiki pages (already used by
  `Entities.create_entity`)

**Test strategy**: TDD per `docs/trunk/TESTING_PHILOSOPHY.md`. Tests are written
before implementation for all meaningful behavior: directory structure, git state,
metadata reading, validation, and CLI output.

## Sequence

### Step 1: Write failing tests for `entity_repo.py`

Create `tests/test_entity_repo.py` covering all success criteria before
implementing any production code. Tests use `tmp_path` fixtures and real git
subprocess calls.

Tests to write (all should fail initially since the module doesn't exist):

**`create_entity_repo` behavior**:
- `test_create_produces_valid_git_repo` — after creation, `git -C <path> log
  --oneline` exits 0 and shows one commit
- `test_create_all_required_directories_exist` — verifies presence of `wiki/`,
  `wiki/domain/`, `wiki/projects/`, `wiki/techniques/`, `wiki/relationships/`,
  `memories/journal/`, `memories/consolidated/`, `memories/core/`, `episodic/`
- `test_create_entity_md_has_correct_frontmatter` — ENTITY.md can be parsed and
  has `name`, `created`, `specialization: null`, `origin: null`
- `test_create_wiki_pages_exist` — `wiki/wiki_schema.md`, `wiki/identity.md`,
  `wiki/index.md`, `wiki/log.md` all exist
- `test_create_initial_commit_includes_all_files` — `git -C <path> show --stat
  HEAD` shows ENTITY.md, wiki files, and .gitkeep sentinels for empty dirs
- `test_create_rejects_invalid_name` — `ValueError` on names like `123bad`,
  `My_Entity`, `has space`
- `test_create_rejects_existing_directory` — `ValueError` if dest already exists
- `test_create_supports_kebab_case_name` — `my-specialist` succeeds (existing
  `ENTITY_NAME_PATTERN` only allows underscores; a new pattern is needed)
- `test_create_with_role_sets_role_in_entity_md` — `--role` value appears in
  ENTITY.md body or as a frontmatter field

**`is_entity_repo` behavior**:
- `test_is_entity_repo_true_for_valid_repo` — returns `True` for a freshly
  created entity repo
- `test_is_entity_repo_false_for_missing_entity_md` — returns `False` for a dir
  without `ENTITY.md`
- `test_is_entity_repo_false_for_invalid_entity_md` — returns `False` if
  `ENTITY.md` frontmatter is missing required fields

**`read_entity_metadata` behavior**:
- `test_read_entity_metadata_returns_correct_fields` — name, created match what
  was passed to `create_entity_repo`
- `test_read_entity_metadata_raises_on_missing_entity_md` — `FileNotFoundError`
  or `ValueError` when called on a non-entity dir

Location: `tests/test_entity_repo.py`

---

### Step 2: Create `src/entity_repo.py`

Implement the module to make the tests pass.

**`EntityRepoMetadata` Pydantic model**:
```python
class EntityRepoMetadata(BaseModel):
    name: str
    created: str          # ISO 8601 datetime string
    specialization: Optional[str] = None
    origin: Optional[str] = None
    role: Optional[str] = None
```

**`ENTITY_REPO_NAME_PATTERN`**: `^[a-z][a-z0-9_-]*$` — extends the existing
`ENTITY_NAME_PATTERN` to also allow hyphens (kebab-case), matching the
investigation's `my-specialist` example.

**`create_entity_repo(dest: Path, name: str, role: str | None = None) -> Path`**:
1. Validate `name` against `ENTITY_REPO_NAME_PATTERN`; raise `ValueError` if
   invalid
2. Compute `repo_path = dest / name`; raise `ValueError` if it already exists
3. Create directory structure:
   ```
   repo_path/
   ├── wiki/
   │   ├── domain/
   │   ├── projects/
   │   ├── techniques/
   │   └── relationships/
   ├── memories/
   │   ├── journal/
   │   ├── consolidated/
   │   └── core/
   └── episodic/
   ```
4. Add `.gitkeep` sentinels to all leaf directories (so they appear in the
   initial commit and the repo works without clutter)
5. Render `ENTITY.md` using `render_template("entity", "entity_md.jinja2", ...)`
   — see Step 3 for the template
6. Render wiki pages using existing templates:
   - `wiki/wiki_schema.md` ← `render_template("entity", "wiki_schema.md.jinja2")`
   - `wiki/identity.md` ← `render_template("entity", "wiki/identity.md.jinja2", ...)`
   - `wiki/index.md` ← `render_template("entity", "wiki/index.md.jinja2", ...)`
   - `wiki/log.md` ← `render_template("entity", "wiki/log.md.jinja2", ...)`
7. `git init` in `repo_path` (subprocess)
8. `git -C repo_path add -A` (subprocess)
9. `git -C repo_path commit -m "Initial entity state: {name}"` (subprocess)
   — configure `GIT_AUTHOR_NAME` and `GIT_AUTHOR_EMAIL` env vars with safe
   defaults so the commit works even in environments without a global git config
10. Return `repo_path`

**`is_entity_repo(path: Path) -> bool`**:
- Returns `True` if `path / "ENTITY.md"` exists and its YAML frontmatter
  contains a `name` field
- Returns `False` for any failure (missing file, invalid YAML, missing field)

**`read_entity_metadata(path: Path) -> EntityRepoMetadata`**:
- Parse `path / "ENTITY.md"` using `parse_frontmatter` (already in `frontmatter`
  module), validate against `EntityRepoMetadata`
- Raise `ValueError` if file is missing or frontmatter is invalid

Add module-level backreference:
```python
# Chunk: docs/chunks/entity_repo_structure - Standalone entity git repo creation
```

Location: `src/entity_repo.py`

---

### Step 3: Create the `ENTITY.md` Jinja2 template

Create `src/templates/entity/entity_md.jinja2`:
```
---
name: {{ name }}
created: {{ created }}
specialization: null
origin: null
{% if role %}role: {{ role }}{% else %}role: null{% endif %}
---

# {{ name }}

{% if role %}**Role:** {{ role }}{% endif %}

This entity was created with `ve entity create`. It is a standalone git repository
that can be hosted on GitHub and attached to projects via `ve entity attach`.
```

The frontmatter fields must match `EntityRepoMetadata` exactly.

Location: `src/templates/entity/entity_md.jinja2`

---

### Step 4: Write failing CLI tests for the updated `create` command

Before updating the CLI, add tests to `tests/test_entity_cli.py` (or create
`tests/test_entity_create_cli.py` if the existing file is already large — check
first).

Tests:
- `test_create_command_produces_git_repo_in_cwd` — invoke `ve entity create
  my_agent`, verify a `my_agent/` subdirectory with a valid git repo exists in
  the temp dir
- `test_create_command_output_shows_path` — CLI stdout contains the repo path
- `test_create_command_rejects_invalid_name` — CLI exits non-zero with a helpful
  error message
- `test_create_command_with_role` — `--role "Infrastructure expert"` causes the
  role to appear in `ENTITY.md`
- `test_create_command_with_output_dir` — `--output-dir /some/path` creates the
  repo there instead of CWD

Note: CLI tests must set the runner's `cwd` to a temp directory and use
Click's `CliRunner` with `mix_stderr=False`. The CliRunner's `invoke` can set
env vars; the git subprocess calls in `entity_repo.py` need git available.

---

### Step 5: Update `ve entity create` in `src/cli/entity.py`

Replace the existing `create` command implementation:

**Before**: calls `Entities(project_dir).create_entity(name, role=role)`, which
creates `.entities/<name>/` within a project directory.

**After**: calls `entity_repo.create_entity_repo(output_dir, name, role=role)`,
which creates `<name>/` as a standalone git repo.

Changes:
1. Remove `--project-dir` option (it was for `.entities/` resolution; standalone
   repos don't need it)
2. Add `--output-dir` option: `type=click.Path(path_type=pathlib.Path)`,
   `default=None` (None → resolve to `pathlib.Path.cwd()`)
3. Import `entity_repo` and call `entity_repo.create_entity_repo(output_dir,
   name, role=role)` inside a try/except for `ValueError`
4. Update help text and success echo to reflect standalone repo creation

The function signature becomes:
```python
@entity.command("create")
@click.argument("name")
@click.option("--role", default=None, help="Brief description of entity's purpose")
@click.option("--output-dir", type=click.Path(path_type=pathlib.Path), default=None,
              help="Directory to create entity repo in (default: current directory)")
def create(name: str, role: str | None, output_dir: pathlib.Path | None) -> None:
```

Add function-level backreference:
```python
# Chunk: docs/chunks/entity_repo_structure - Standalone entity repo creation command
```

---

### Step 6: Run tests and fix failures

```bash
uv run pytest tests/test_entity_repo.py tests/test_entity_cli.py -v
```

Iterate until all new tests pass and no existing tests regress. Pay special
attention to:
- Git subprocess calls needing a real git binary (fine in normal dev environments)
- `GIT_AUTHOR_NAME`/`GIT_AUTHOR_EMAIL` env vars so tests don't require global
  git config
- `.gitkeep` files ensuring empty dirs appear in the initial commit

---

### Step 7: Update `docs/chunks/entity_repo_structure/GOAL.md` code_paths

Add `src/templates/entity/entity_md.jinja2` and `tests/test_entity_repo.py` to
the `code_paths` list in the GOAL.md frontmatter.

## Dependencies

- `entity_wiki_schema` (ACTIVE / complete): The wiki templates
  (`src/templates/entity/wiki_schema.md.jinja2`, `wiki/identity.md.jinja2`,
  `wiki/index.md.jinja2`, `wiki/log.md.jinja2`) are already implemented and
  available. `create_entity_repo` reuses them via `render_template`.

## Risks and Open Questions

- **Git binary availability in tests**: The implementation shells out to `git`.
  Tests that call `create_entity_repo` require git in PATH. This is safe for
  local dev and CI but worth noting. Mitigation: set
  `GIT_AUTHOR_NAME=Test GIT_AUTHOR_EMAIL=test@example.com` in subprocess env
  so tests don't fail due to missing git config.

- **Existing CLI tests**: `test_entity_cli.py` currently tests `ve entity create`
  against the old `.entities/`-based behavior. Those tests will need to be updated
  or the new behavior isolated into a separate test file. Check before writing new
  tests to avoid duplication.

- **`Entities.create_entity` backward compat**: The existing method is left
  unchanged. The migration chunk (`entity_memory_migration`) will handle
  converting existing entities. No risk to current functionality.

## Deviations

### ENTITY.md `created` field quoted in YAML

The `created` field in `entity_md.jinja2` is rendered as `created: "{{ created }}"` (quoted) rather than `created: {{ created }}`. Without quotes, YAML parses ISO 8601 datetime strings as Python `datetime` objects, which Pydantic rejects for a `str`-typed field. Quoting the value in the template is the minimal fix.

### `test_lists_with_roles` and `test_identity_parseable` are pre-existing failures

These tests were already failing before this chunk's implementation due to a bug in `src/templates/entity/identity.md.jinja2`: the Jinja2 comment `{# ... #}` leaves a leading `\n` before `---`, causing `parse_frontmatter` to fail to detect the frontmatter block. Not fixed in this chunk to stay in scope.

### CLI test updates in `test_entity_cli.py`

The `TestEntityCreate` tests in `test_entity_cli.py` were updated to use `--output-dir` instead of `--project-dir` since the create command no longer accepts `--project-dir`. Other tests that used `entity create --project-dir` as setup (TestEntityList, TestEntityStartup, TestEntityRecall) were updated to use `Entities(project_dir).create_entity()` directly.