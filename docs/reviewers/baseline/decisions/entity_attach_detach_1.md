---
decision: APPROVE
summary: All six success criteria satisfied — attach/detach/list implemented cleanly with full submodule lifecycle, 59 tests all passing, no regressions in existing suite.
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve entity attach https://github.com/user/my-entity.git` clones into `.entities/my-entity/`

- **Status**: satisfied
- **Evidence**: `attach_entity()` in `src/entity_repo.py:295` runs `git submodule add` with file protocol support. `derive_entity_name_from_url()` strips `.git` suffix and `entity-` prefix. CLI `attach` command calls both. Confirmed by `test_attach_creates_entity_subdir` and `test_attach_derives_name_from_url`.

### Criterion 2: `ve entity attach ../local-entity --name specialist` clones into `.entities/specialist/`

- **Status**: satisfied
- **Evidence**: `--name` CLI option overrides derived name. Local paths supported via `GIT_CONFIG_VALUE_0: "always"` for `protocol.file.allow`. Confirmed by `test_attach_with_explicit_name` and `test_attach_with_local_path_url`.

### Criterion 3: `ve entity detach specialist` cleanly removes the submodule

- **Status**: satisfied
- **Evidence**: `detach_entity()` in `src/entity_repo.py:359` runs full three-step removal: `git submodule deinit -f`, `git rm -f`, and `shutil.rmtree` of `.git/modules/.entities/<name>`. Confirmed by `test_detach_removes_entities_dir` and `test_detach_removes_from_gitmodules`.

### Criterion 4: `ve entity list` shows attached entities with status

- **Status**: satisfied
- **Evidence**: `list_attached_entities()` returns `AttachedEntityInfo` with name, remote_url, specialization, and status. Enhanced `list_entities` in `src/cli/entity.py:87` displays all fields plus falls back to legacy plain-directory entities. Confirmed by `TestListCLI` tests.

### Criterion 5: Refuses to detach if entity has uncommitted changes (unless --force)

- **Status**: satisfied
- **Evidence**: `detach_entity()` runs `git status --porcelain` inside the submodule and raises `RuntimeError` if output is non-empty and `force=False`. CLI wraps this in `try/except` → `ClickException`. Confirmed by `test_detach_refuses_uncommitted_changes` and `test_detach_force_proceeds_with_uncommitted_changes`.

### Criterion 6: Tests cover attach, detach, list, name derivation, and error cases

- **Status**: satisfied
- **Evidence**: 59 tests across three files: `test_entity_repo.py` (8 name-derivation cases), `test_entity_submodule.py` (12 submodule unit tests), `test_entity_attach_detach_cli.py` (12 CLI integration tests). All 59 pass. No regressions in 950 pre-existing tests (one pre-existing decay integration failure unrelated to this chunk).
