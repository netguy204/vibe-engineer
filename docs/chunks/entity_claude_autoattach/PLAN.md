# Implementation Plan

## Approach

The chunk composes an auto-attach prelude in front of the existing
`ve entity claude` lifecycle (currently `cli.entity.claude_cmd`). The
prelude does exactly three things, in order, before any of today's
session-launch logic runs:

1. **Resolve the project root** (already done by `resolve_entity_project_dir`).
2. **Unconditionally call `do_attach(name, project_dir, config_path=None)`**
   from `cli.entity_worktree`. That function is idempotent — it short-
   circuits when `.entities/<name>` is already a worktree of the
   canonical clone, so calling it unconditionally is the simplest
   correct implementation. There is no need to pre-check
   `is_attached()`.
3. **Render progress output** _only when work is actually happening_.
   When `do_attach` is doing real work (auto-clone or worktree attach),
   the user sees two informative lines so the multi-second wait is
   comprehensible. When the entity is already attached, the path is
   silent and instant.

Distinguishable errors are produced by catching the same exception
classes the existing `attach` CLI already catches in
`cli.entity.attach`, plus an explicit catch for `ConfigError` to point
the user at `~/.ve-config.toml`. We reuse the exact error-message
phrasing from the `attach` CLI so the user sees the same vocabulary
across both surfaces. On any error, we raise `click.ClickException`
**before** entering Phase 1 of the existing `claude_cmd` (so the Claude
session is never launched against a half-set-up entity).

### Where progress lines go

The auto-clone path can be slow (multi-second clone over the network),
so the "Cloning…" line must be emitted **before** `do_attach` runs.
But `do_attach` is the only function that knows whether work is
actually needed. We solve this with a small pre-check in the
auto-attach wrapper:

- If `.entities/<name>` already exists as a worktree of the canonical
  clone, do nothing (silent fast path).
- Otherwise, render the two progress lines and then call `do_attach`.
  After `do_attach` returns, we know `already_attached` should be
  `False` (because we already verified it wasn't); if for any reason
  it does come back `True`, that's a benign race we just accept
  silently.

The pre-check needs the canonical clone path (to compare against the
worktree marker). We get this by calling `load_config` once at the
top of the wrapper and computing `cfg.entities_dir / name`. The
existing `_is_worktree_of` helper in `cli.entity_worktree` answers
the "is this an attached worktree of the canonical?" question
directly.

To avoid leaking `_is_worktree_of` (a module-private helper) into
`cli.entity`, we add a thin public helper to `cli.entity_worktree`:

```python
def is_attached(name, project_dir, *, config_path=None) -> bool:
    """Return True iff name is already attached as a worktree of its
    canonical clone in project_dir.

    Cheap: reads the operator config and probes the .git marker file.
    Never invokes git or network. Returns False if the config is
    missing or malformed (the caller will hit the same error path
    when it goes to do_attach).
    """
```

This keeps the auto-attach pre-check on a public seam and lets tests
exercise the silent fast path directly without subprocess work.

### Module placement

Per the chunk goal's note (#8), the predicted `src/entity/claude_command.py`
path does not exist. The existing `ve entity claude` command lives at
`src/cli/entity.py#claude_cmd`. Two options were considered:

1. **Extend `claude_cmd` directly** with an inline prelude.
2. **Add `src/cli/entity_claude.py`** with `prepare_session_environment(...)`
   that does the auto-attach + progress rendering, and call it from
   `claude_cmd`.

Option 2 is preferred because:

- It isolates the auto-attach concern from the existing 200-line
  session lifecycle in `claude_cmd`, which already has five labeled
  phases.
- It makes the new behavior easy to test in isolation — both unit
  tests (mock `do_attach`, assert progress output) and an
  integration-style end-to-end test (real bare repo as `git_base`,
  real auto-attach, mock the actual `subprocess.Popen(["claude", ...])`).
- It keeps `cli.entity` from accumulating yet another set of
  responsibility-bearing imports.

So the implementation adds **`src/cli/entity_claude.py`** with one
public function `prepare_session_environment(name, project_dir, *, config_path=None)`
that:

- Calls `is_attached(name, project_dir, config_path=config_path)`.
- If already attached: returns immediately, silently.
- If not attached: emits the two progress lines (`click.echo`), then
  calls `do_attach(name, project_dir, config_path=config_path)`.
- All `do_attach` exceptions propagate to the caller, which is
  responsible for translating them into `click.ClickException`.

`claude_cmd` calls `prepare_session_environment` immediately after
`resolve_entity_project_dir` and **before** `Entities(project_dir)`,
because the `Entities` adapter assumes the entity exists on disk.

## Subsystem Considerations

No relevant subsystems apply. This is glue between three modules
that already exist (`cli.canonical_clone`, `cli.entity_worktree`,
`cli.entity.claude_cmd`).

## Sequence

### Step 1: Add `is_attached` to `cli.entity_worktree`

Add a public helper that returns `True` iff `.entities/<name>` is
already an attached worktree of `<entities_dir>/<name>`. Implementation:

- Try `load_config(config_path)` inside a `try` block; on `ConfigError`,
  return `False` (the caller will hit the same error path next).
- Compute `entity_path = project_dir / ".entities" / name`.
- Compute `canonical = cfg.entities_dir / name`.
- Return `entity_path.exists() and _is_worktree_of(entity_path, canonical)`.

Location: `src/cli/entity_worktree.py`

### Step 2: Add `src/cli/entity_claude.py`

Module with one public function:

```python
def prepare_session_environment(
    name: str,
    project_dir: pathlib.Path,
    *,
    config_path: pathlib.Path | None = None,
) -> None:
    """Ensure entity 'name' is attached in project_dir, with progress output.

    Idempotent: when the entity is already attached, this is a silent,
    instant no-op. When the entity needs to be cloned and/or attached,
    emits two progress lines so multi-second waits are comprehensible.

    Raises:
        cli.config.ConfigError
        cli.canonical_clone.CanonicalCloneError (incl. AuthFailure,
            MissingRemoteRepo, NetworkFailure)
        cli.entity_worktree.WorktreeAttachError
        ValueError
    """
```

Implementation:

1. If `is_attached(name, project_dir, config_path=config_path)` → return.
2. Load config to get `git_base` and `entities_dir` for the message;
   on `ConfigError`, re-raise (the caller catches it).
3. Compute branch via `attach_branch_name(project_dir)`.
4. Emit two `click.echo` lines:
   - `Cloning {name} from {cfg.git_base}/{name}.git into {cfg.entities_dir}/{name}…`
   - `Attaching as worktree at .entities/{name} (branch {branch})…`
5. Call `do_attach(name, project_dir, config_path=config_path)` and
   let any exception propagate.

Add module docstring with `# Chunk: docs/chunks/entity_claude_autoattach`
backreference.

Location: `src/cli/entity_claude.py` (new file)

### Step 3: Wire `prepare_session_environment` into `claude_cmd`

In `src/cli/entity.py#claude_cmd`:

1. After `project_dir = resolve_entity_project_dir(project_dir)`, and
   **before** `entities = Entities(project_dir)`:
2. Import locally: `from cli.entity_claude import prepare_session_environment`.
3. Wrap in `try/except`, mirroring the error vocabulary used by the
   existing `attach` command:
   - `AuthFailure` → "Authentication failed cloning '{name}' from {clone_url}. Check your git credentials (SSH key, token, or username)."
   - `MissingRemoteRepo` → "No repository at {clone_url} for entity '{name}'. Check the entity name and the configured git_base."
   - `NetworkFailure` → "Network failure cloning '{name}' from {clone_url}. Check your network and retry."
   - `ConfigError` → "Operator config missing or invalid: {exc}. Set up `~/.ve-config.toml` first."
   - `(CanonicalCloneError, ValueError, WorktreeAttachError)` → `str(exc)`.
4. Each raises `click.ClickException(...)` so the Claude session is
   never reached on failure.

Add chunk backreference comment above the prelude:
`# Chunk: docs/chunks/entity_claude_autoattach`

Location: `src/cli/entity.py`

### Step 4: Update GOAL.md `code_paths` to reflect reality

Replace the predicted path `src/entity/claude_command.py` with
`src/cli/entity_claude.py`. Final list:

```yaml
code_paths:
- src/cli/entity_claude.py
- src/cli/entity_worktree.py
- src/cli/entity.py
- tests/test_entity_claude_autoattach.py
```

This must be done before `/chunk-complete` so the `code_references`
generator emits accurate refs.

### Step 5: Add `tests/test_entity_claude_autoattach.py`

Test file structured around five concerns:

#### 5a. `is_attached` unit tests

- Returns `True` when the worktree marker matches the canonical clone.
- Returns `False` when `.entities/<name>` doesn't exist.
- Returns `False` when `.entities/<name>` exists but isn't a worktree.
- Returns `False` when the config is missing (no exception leaks).

#### 5b. `prepare_session_environment` unit tests (mocked `do_attach`)

- **Already-attached short-circuit**: pre-create an attached worktree
  (helper from `test_entity_worktree_attach.py`), call
  `prepare_session_environment`, assert `do_attach` was NOT called
  and no output was produced.
- **Not-attached emits two progress lines**: with a bare origin
  cloned (so `do_attach` succeeds), capture stdout and assert both
  "Cloning…" and "Attaching as worktree…" appear, and that the
  resolved URL and destination are in the first line.
- **Auth/missing/network errors propagate** (parametrize): patch
  `do_attach` to raise each class, assert the exception class
  reaches the caller unchanged.

#### 5c. `claude_cmd` CLI integration tests (mocked subprocess)

- **End-to-end fresh-machine path**: no entities_dir pre-existing,
  no canonical clone, no .entities/<name>; invoke
  `ve entity claude --entity <name>` via `CliRunner` against a
  bare origin pointed to by `~/.ve-config.toml` (use a
  pytest-managed temp config path through monkeypatching
  `DEFAULT_CONFIG_PATH`, or — better — accept that the CLI doesn't
  expose a `--config` flag for `claude` and instead patch
  `cli.entity_claude.prepare_session_environment` to forward an
  explicit `config_path` for the test). With `subprocess.Popen`
  mocked to return a benign process, assert:
  - exit code 0
  - `.entities/<name>` exists and is a worktree of the canonical
  - canonical clone exists at `entities_dir/<name>`
  - the two progress lines appeared in stdout
  - `subprocess.Popen` was called at least once with `claude` as
    `argv[0]` (proves session launch was reached)
- **Already-attached cold path is silent for auto-attach**:
  pre-attach the entity via `do_attach`, then invoke `claude_cmd`
  and assert no "Cloning…" / "Attaching…" lines appear.
- **Auth failure aborts before session launch**: patch `do_attach`
  to raise `AuthFailure`. Assert non-zero exit, error message
  mentions auth, and `subprocess.Popen` was NOT called.
- **Missing-repo failure aborts before session launch**: same shape.
- **Network failure aborts before session launch**: same shape.
- **Missing config aborts with config-shaped error**: patch
  `do_attach` to raise `ConfigError`. Assert error message hints
  at `~/.ve-config.toml`.

For the CLI tests that need real `do_attach` execution, the
existing `claude` command does not currently accept a `--config`
flag. Solution: write an explicit `test_config_path` fixture that
monkeypatches `cli.config.DEFAULT_CONFIG_PATH` to a temp file. Then
the CLI runs without any `--config` flag and still reads the test
config.

For the CLI tests that need mocked `do_attach`, patch
`cli.entity_claude.do_attach` directly.

Location: `tests/test_entity_claude_autoattach.py` (new file)

### Step 6: Run the full test suite and verify baseline

`uv run pytest tests/` — expected: `31 failed, M passed` where
`M ≥ 4039 + (number of tests added in step 5)`. The 31 pre-existing
failures must remain the same set; no new failures introduced.

## Dependencies

- `entity_config_toml` (ACTIVE) — `cli.config.load_config`,
  `ConfigError`, `DEFAULT_CONFIG_PATH`.
- `entity_canonical_clone` (ACTIVE) — `ensure_canonical_clone`,
  `CanonicalCloneError`, `AuthFailure`, `MissingRemoteRepo`,
  `NetworkFailure`.
- `entity_worktree_attach` (ACTIVE) — `do_attach`, `AttachResult`,
  `WorktreeAttachError`, `attach_branch_name`, `_is_worktree_of`.
- `entity_claude_wrapper` (ACTIVE) — `claude_cmd` is the function
  we're extending; not superseded, just extended.

## Risks and Open Questions

- **`~/.ve-config.toml` discovery in tests**: the `claude` CLI doesn't
  take a `--config` flag today. Adding one would expand the chunk
  scope. Instead, monkeypatch `cli.config.DEFAULT_CONFIG_PATH` for the
  CLI tests that exercise real attach; this is a well-trodden pattern
  in the test suite.
- **Progress output via `click.echo` vs. `click.echo(..., err=True)`**:
  the chunk goal says "the user sees informative progress output," and
  Click's convention puts purely-informational output on stdout. We
  use plain `click.echo`. Errors continue to use
  `click.ClickException`, which Click writes to stderr.
- **Race between `is_attached` check and `do_attach`**: if another
  process attaches between our check and our call, `do_attach` would
  see `already_attached=True` after we already printed the progress
  lines. This is benign — the worst case is two informational lines
  followed by a fast return — and not worth a lock.

## Deviations

- **Step 2 added a backward-compat fast path**: when `.entities/<name>`
  already exists as a plain directory (legacy `ve entity create`
  output, predating the worktree migration), `prepare_session_environment`
  treats it as "already present" and skips the auto-attach pathway
  entirely. Without this, the auto-attach would try to `git worktree
  add` over a non-empty plain directory and explode. Discovered when
  running the existing `tests/test_entity_claude_cli.py` suite — those
  tests use `Entities.create_entity` to seed a plain directory and
  expect `ve entity claude` to run against it. Honoring the GOAL's
  "behaves identically to today" criterion for already-present
  entities means short-circuiting on any existing `.entities/<name>`,
  not just attached worktrees. Documented inline.
- **CLI tests use `sys.modules["cli.config"]` to monkeypatch
  `DEFAULT_CONFIG_PATH`**: the package attribute `cli.config` resolves
  to the Click group, not the module, because the module's
  `config = click.group(...)` decorator shadows the module name. The
  fix is a one-liner (`sys.modules["cli.config"]`) and was added to
  the test helper `_patch_default_config`.
- **Progress output uses relative `.entities/<name>` for the second
  line**, not the absolute `<project_dir>/.entities/<name>`. This
  matches the handoff specification exactly and is more conventional
  to read in a project shell.
