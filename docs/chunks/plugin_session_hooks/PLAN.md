

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The SessionStart hook ships as two plugin files plus one small CLI addition:

1. **`hooks/hooks.json`** — registers a `SessionStart` hook that runs a shell
   script via `${CLAUDE_PLUGIN_ROOT}`, per Claude Code's plugin hook
   convention (DEC-010 established `hooks/` as the canonical home).
2. **`hooks/session_start.sh`** — a dependency-free POSIX shell script. It
   must work precisely when the `ve` CLI is *missing*, so it cannot be
   written in Python or depend on `jq`; it uses only `sh` built-ins, `grep`,
   and `sed`. Logic, in order:
   - **ve-project detection**: resolve the project root as
     `${CLAUDE_PROJECT_DIR:-$PWD}` and require `docs/trunk/GOAL.md` to exist
     there. This is the cheapest unambiguous signal — `ve init` always
     scaffolds it, and `docs/chunks/` alone can exist in non-ve repos that
     merely vendor docs. Not a ve project → `exit 0` with no output.
   - **CLI presence**: `command -v ve`. Missing → emit exactly one
     actionable line (`uv tool install vibe-engineer` hint) and exit 0.
   - **Version compatibility**: read the plugin version from
     `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` (grep/sed, no jq);
     read the CLI version from `ve --version`. Warn per the policy below.
   - **Current chunk**: run `ve chunk list --current` from the project root.
     Exit 0 → print `Current IMPLEMENTING chunk: <dir>`. Non-zero (no
     implementing chunk, or project not initialized) → print nothing for
     this section. Total output is at most 3 lines.
3. **`ve --version`** — the CLI currently has no version flag (`ve --version`
   exits 2), and the hook needs a version source. Add
   `@click.version_option(package_name="vibe-engineer", prog_name="ve")` to
   the `cli` group in `src/cli/__init__.py`. Version comes from installed
   package metadata (single source of truth: `pyproject.toml`), output is
   `ve, version X.Y.Z`. This is the cleanest mechanism — no parallel version
   constant to keep in sync.

### Version-compatibility policy (the DEC-010 deferral)

Recorded as a new ADR (DEC-011) in `docs/trunk/DECISIONS.md`:

- The plugin and the Python package are co-versioned in this repository:
  `.claude-plugin/plugin.json` `version` must equal `pyproject.toml`
  `version` at every release (enforced by a test).
- **Compatible** iff the `major.minor` of the plugin and the installed CLI
  match; patch-level drift is tolerated silently.
- `major.minor` mismatch → one warning line naming both versions and
  suggesting `uv tool install --upgrade vibe-engineer` (or a plugin update
  if the CLI is newer).
- A CLI that does not support `--version` predates this policy (< 0.2.x
  installs) → treated as a mismatch with version "unknown"; same one-line
  warning.
- Warnings never block the session; the hook always exits 0.

### Testing strategy (per docs/trunk/TESTING_PHILOSOPHY.md)

TDD with behavioral assertions. The hook script is pure behavior — write the
tests first, run them red, then implement:

- **Hook behavior tests** (`tests/test_session_hook.py`): invoke
  `hooks/session_start.sh` via `subprocess` with a controlled environment
  (tmp project dirs, a tmp `PATH` containing fake `ve` stub executables that
  report chosen versions / chunk output). Each test maps to a GOAL success
  criterion: silent in non-ve dirs, one-line hint when ve is missing,
  mismatch warning naming both versions, current chunk surfaced, output ≤ 3
  lines, exit 0 in all cases.
- **Hook registration tests**: `hooks/hooks.json` is valid JSON, registers a
  `SessionStart` command hook pointing at the script via
  `${CLAUDE_PLUGIN_ROOT}`, and the script is executable.
- **CLI version test**: `click.testing.CliRunner` invokes `cli` with
  `--version`; asserts the reported version equals
  `importlib.metadata.version("vibe-engineer")`.
- **Co-versioning test**: plugin.json version == pyproject.toml version
  (extends the contract started by `tests/test_plugin_manifest.py`).

## Subsystem Considerations

No documented subsystem in `docs/subsystems/` covers plugin layout or CLI
flag wiring; the closest governing artifacts are DEC-010 and the
`plugin_scaffold` chunk, which this plan builds on directly.

## Sequence

### Step 1: Add `ve --version` to the CLI

In `src/cli/__init__.py`, decorate the `cli` group with
`@click.version_option(package_name="vibe-engineer", prog_name="ve")`. Add a
chunk backreference comment. Write the CliRunner test first
(`tests/test_session_hook.py::TestVeVersionFlag` or a small dedicated test
class) asserting `ve --version` exits 0 and reports the installed package
version.

Location: `src/cli/__init__.py`, `tests/test_session_hook.py`

### Step 2: Write failing hook tests

Create `tests/test_session_hook.py` with subprocess-based tests against
`hooks/session_start.sh`:

- `test_silent_in_non_ve_directory` — tmp dir without `docs/trunk/GOAL.md`:
  no stdout, exit 0.
- `test_missing_ve_cli_emits_single_install_hint` — ve project, `PATH`
  without `ve`: exactly one line containing `uv tool install vibe-engineer`.
- `test_surfaces_implementing_chunk` — fake `ve` stub whose `--version`
  matches plugin major.minor and whose `chunk list --current` prints a chunk
  dir: output names the chunk, contains no warning.
- `test_no_chunk_line_when_nothing_implementing` — stub exits 1 with "No
  implementing chunk found": no chunk line emitted.
- `test_version_mismatch_warns_naming_both_versions` — stub reports a
  different minor version: warning line contains both version strings.
- `test_patch_drift_is_silent` — stub reports same major.minor, different
  patch: no warning.
- `test_cli_without_version_flag_warns` — stub exits 2 on `--version` (the
  pre-policy CLI): warning emitted, hook still exits 0 and surfaces chunk.
- `test_output_stays_within_budget` — worst case (mismatch + chunk) ≤ 3
  lines.

Fake `ve` stubs are tiny shell scripts written into a tmp `PATH` dir by a
test helper. Run the suite; these must fail (script doesn't exist yet).

### Step 3: Implement `hooks/session_start.sh`

Dependency-free shell script implementing the Approach logic. Set the
executable bit. Add a chunk backreference comment. Parse plugin.json with
`sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p'`-style
extraction; compare versions by splitting on dots and comparing the first
two components. Remove `hooks/.gitkeep` now that the directory has content.

Location: `hooks/session_start.sh`

### Step 4: Register the hook in `hooks/hooks.json`

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/session_start.sh\""
          }
        ]
      }
    ]
  }
}
```

Add registration tests (valid JSON, SessionStart entry, command references
the script, script file exists and is executable, plugin.json/pyproject
co-versioning).

Location: `hooks/hooks.json`, `tests/test_session_hook.py`

### Step 5: Document the policy (DEC-011) and README note

Append DEC-011 "Plugin/CLI version-compatibility policy" to
`docs/trunk/DECISIONS.md` following the existing ADR format: co-versioned
releases, major.minor compatibility rule, unknown-version handling,
warn-don't-block, and `ve --version` as the version source. Add a short
"Session hook" paragraph to the plugin section of `README.md` describing
what the hook surfaces.

Location: `docs/trunk/DECISIONS.md`, `README.md`

### Step 6: Full test run and GOAL.md bookkeeping

Run `uv run pytest tests/` — only the 32 pre-existing failures
(subsystem-related files + orchestrator daemon negative-pid test) may
remain; all new tests green. Update `code_paths` in the chunk GOAL.md.

## Dependencies

- `plugin_scaffold` (ACTIVE) — provides `.claude-plugin/plugin.json`, the
  `hooks/` directory, and DEC-010. Already merged.
- No new Python or system dependencies; the hook script deliberately uses
  only POSIX shell tooling.

## Risks and Open Questions

- **Hook output channel**: SessionStart stdout is added to session context.
  We rely on plain stdout (simplest, documented behavior) rather than the
  JSON `additionalContext` envelope; if Claude Code changes this, only the
  script's echo statements are affected.
- **`CLAUDE_PROJECT_DIR` availability**: assumed set for hooks; the script
  falls back to `$PWD` so it degrades gracefully.
- **plugin.json parsing without jq**: sed extraction assumes the `version`
  key appears once with simple formatting — true for our manifest, and the
  co-versioning test pins the file's shape indirectly.
- **`ve chunk list --current` cost**: runs a Python CLI at session start
  (~hundreds of ms). Acceptable; the script only reaches it inside ve
  projects with ve installed.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
