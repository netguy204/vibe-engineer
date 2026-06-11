# Implementation Plan

## Approach

Add a new `src/cli/config.py` module that owns the schema, loading,
validation, and normalization of `~/.ve-config.toml`. The module exposes:

- `VeConfig` dataclass with two fields: `entities_dir: pathlib.Path` and
  `git_base: str`. Both are post-validation, fully resolved values
  (`entities_dir` is absolute, `git_base` has no trailing slash).
- `DEFAULT_CONFIG_PATH = Path.home() / ".ve-config.toml"`
- `DEFAULT_ENTITIES_DIR = "~/Entities"` (sentinel string applied when
  `entities_dir` is omitted from the file).
- `ConfigError(Exception)` — surfaced by the CLI as a clean Click error,
  always names the offending field and the config file path.
- `load_config(path: Path | None = None) -> VeConfig` — the canonical
  loader. Handles missing-file, malformed-TOML, missing-required-field,
  wrong-type, and produces actionable error messages. Performs:
  - tilde expansion on `entities_dir` (`Path.expanduser().resolve()`).
  - trailing-slash strip on `git_base` (`.rstrip("/")`).
  - applies `DEFAULT_ENTITIES_DIR` if `entities_dir` is missing.
  - raises `ConfigError` if `git_base` is missing (no sensible default).
- Convenience accessors used by downstream chunks:
  - `get_entities_dir(path: Path | None = None) -> Path` — resolved
    absolute path.
  - `get_git_base(path: Path | None = None) -> str` — normalized base URL.

Then wire a top-level `ve config` group with a single `show` subcommand to
`src/cli/__init__.py`, paralleling the existing pattern used by
`cli/init_cmd.py`. The `show` command prints the resolved config in a
stable, human-readable `key = value` format (the input file path included
as a comment header so users can confirm which file was read).

The board config module (`src/board/config.py`) is the closest existing
template — same `tomllib`-based load pattern, same dataclass-with-defaults
shape, same `Path.home() / ".ve" / "board.toml"` style. We deliberately do
NOT reuse it: board config has different schema, different defaults, and
different responsibilities. Sharing structure (dataclass + `load_*`
function + `DEFAULT_*` constants) is enough.

Tests live in `tests/test_config.py`. We use the existing `runner` and
`tmp_path` fixtures; no new conftest plumbing needed. For each test we
write a TOML file under `tmp_path` and pass the path explicitly to
`load_config(path)` — we never poke at the user's real `~/.ve-config.toml`.

## Subsystem Considerations

None directly relevant. This is a new operator-level config and does not
intersect with existing subsystems. Future entity-related chunks may form
an `entity_worktrees` subsystem; out of scope here.

## Sequence

### Step 1: Create `src/cli/config.py`

Implements:
- `VeConfig` dataclass
- `ConfigError` exception
- `DEFAULT_CONFIG_PATH`, `DEFAULT_ENTITIES_DIR` constants
- `load_config(path=None)` with full validation + normalization
- `get_entities_dir(path=None)` and `get_git_base(path=None)` helpers
- Module-level backreference comment to this chunk.

Error message contract (used by tests and downstream UX):
- Missing file: `"Config file not found: {path}. Create it with two fields: entities_dir and git_base."`
- TOML parse error: `"Failed to parse {path}: {orig_message}"`
- Missing required field: `"Missing required field '{field}' in {path}"`
- Wrong type: `"Field '{field}' in {path} must be a {type}, got {actual_type}"`

### Step 2: Add `ve config show` subcommand

Create the new `config` group in `src/cli/config.py` as a `@click.group`,
with a single `show` command. Register the group in `src/cli/__init__.py`
following the existing pattern (import + `cli.add_command(config)`).

`ve config show` output format:
```
# Config file: /Users/op/.ve-config.toml
entities_dir = /Users/op/Entities
git_base = git@github.com:my-org
```

On `ConfigError`, the command echoes the error to stderr and exits with
code 1 (via `click.ClickException`).

### Step 3: Write `tests/test_config.py`

Cover every success-criteria bullet:

1. `test_load_valid_config` — file with both fields loads, types correct,
   `entities_dir` is absolute.
2. `test_load_default_entities_dir` — file with only `git_base` loads,
   `entities_dir` defaults to `~/Entities` resolved absolute.
3. `test_tilde_expansion` — `entities_dir = "~/Entities"` resolves to
   absolute path under `Path.home()`.
4. `test_trailing_slash_stripped` — `git_base = "https://x/"` loads as
   `"https://x"`.
5. `test_missing_file_error` — `load_config(non_existent_path)` raises
   `ConfigError` whose message names the path.
6. `test_malformed_toml_error` — invalid TOML raises `ConfigError` naming
   the path.
7. `test_missing_required_field_error` — file without `git_base` raises
   `ConfigError` naming the field.
8. `test_wrong_type_error` — `git_base = 42` raises `ConfigError` naming
   the field and types.
9. `test_get_entities_dir_returns_path` — helper returns `Path`.
10. `test_get_git_base_returns_str` — helper returns normalized string.
11. `test_config_show_command` — CLI invocation prints `entities_dir = ...`
    and `git_base = ...` with the resolved values. Uses
    `runner.isolated_filesystem` + an explicit `--config` flag OR a
    monkeypatched `DEFAULT_CONFIG_PATH` to avoid touching the real
    `~/.ve-config.toml`. Decision: pass `--config PATH` option to
    `ve config show` for testability; downstream callers use the default.
12. `test_config_show_missing_file` — exits non-zero with helpful error.

### Step 4: Run tests + verify baseline

Run `uv run pytest tests/test_config.py -v` to confirm new tests pass.
Then run the full suite to confirm `31 failed, N passed` where N has grown
by the count of new tests (≈12) and no new failures appear outside the
pre-existing subsystem failures.

## Dependencies

- Python 3.12+ stdlib `tomllib` (already required by project — see
  `pyproject.toml requires-python = ">=3.12"`).
- No new runtime deps. No coordination with other chunks (this is the
  first chunk of the narrative).

## Risks and Open Questions

- **`ve config show` reading the user's real `~/.ve-config.toml` in tests**
  — mitigated by accepting `--config PATH` and never relying on the real
  home file in test code.
- **Downstream chunks expect a specific accessor shape** — declared above
  (`get_entities_dir(path=None) -> Path`, `get_git_base(path=None) -> str`).
  If chunks 1–3 need a different signature, this is a small refactor; the
  data model is stable.
- **`git_base` validation strictness** — we only check type and strip
  trailing slash. We do NOT validate that it's a valid URL, because both
  `git@github.com:org` SSH-form and `https://github.com/org` HTTPS-form
  must work; URL parsing differs between them. The clone helper (next
  chunk) handles invalid URLs by surfacing the underlying git error.

## Deviations

(Populated during implementation if reality diverges from the plan.)
