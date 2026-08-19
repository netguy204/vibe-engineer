# Implementation Plan

## Approach

**The decision this chunk exists to make: Cursor gets a real plugin hook,
not the skill-embedded fallback.** Verified against the live spec on
2026-08-14 (`cursor.com/docs/reference/plugins.md`, `cursor.com/docs/hooks.md`,
and the upstream `github.com/cursor/plugins` examples):

- Cursor plugins declare hooks: the manifest `hooks` field is "path to a
  hooks configuration file, or an inline hooks object", and upstream
  plugins (`ralph-loop`, `continual-learning`) ship `hooks/hooks.json`
  files referenced as `"hooks": "./hooks/hooks.json"`.
- `sessionStart` is a supported agent hook event. It fires when a composer
  conversation is created, is fire-and-forget (never blocks the session —
  matching the Claude hook's exit-0-always contract by construction), and
  its JSON output supports `additional_context`: "context to add to the
  conversation's initial system context" — the same surfacing channel as
  Claude Code prepending SessionStart stdout.
- Hook scripts receive `CLAUDE_PROJECT_DIR` ("alias for project dir, Claude
  compatibility", documented as always present) alongside
  `CURSOR_PROJECT_DIR`. Upstream's continual-learning plugin uses
  `${CURSOR_PLUGIN_ROOT}` in its hook command for the installed plugin
  directory.
- The contract difference from Claude Code: Cursor hooks speak **JSON over
  stdio** (input on stdin, output on stdout), not plain text. Claude's
  `hooks/session_start.sh` emits plain lines, so it cannot be registered
  directly — its output would be discarded as unparseable.

So the shape is: **a thin Cursor adapter around the unchanged shared core.**
`.cursor-plugin/hooks/session_start.sh` (new, static — hooks are not
template-rendered on the Claude side either) locates the plugin root from
its own path, exports the `CLAUDE_*` variables the core expects, runs
`hooks/session_start.sh`, and wraps the captured stdout as
`{"additional_context": "..."}` (or `{}` when silent). Everything
DEC-013/DEC-011-shaped — ve-project detection, polite bootstrap,
managed-install/bootstrap-attempt markers under
`${XDG_STATE_HOME:-~/.local/state}/vibe-engineer`, drift warning, current
chunk — happens in the one shared core, so both editors' hooks share the
state markers instead of duplicating the logic. The adapter stays POSIX
sh + sed, dependency-free, exit 0 always, like the core.

One small core change: the core reads its version from
`.claude-plugin/plugin.json` only. Under a Cursor-only install that file
may be absent, so the core falls back to `.cursor-plugin/plugin.json` —
safe because DEC-014's coupling test forces the two to carry the same
version.

The manifest's `"hooks": {}` placeholder (explicitly empty per DEC-014's
consequence bullet, guarded by
`tests/test_cursor_manifest.py::TestDiscoveryCollision::test_hooks_declares_no_hook_events`)
becomes `"hooks": "./.cursor-plugin/hooks/hooks.json"`; it still overrides
discovery of the root Claude `hooks/hooks.json`, which is the property that
test protects. That test is replaced by tests asserting the declared config
exists inside the Cursor tree, declares `sessionStart`, and points at an
executable script.

Docs work (README):
- **Cursor install section** for colleagues: official Cursor Marketplace /
  Customize panel, team-marketplace "Import from Repo", and the local-dev
  path (`~/.cursor/plugins/local` symlink). Explicitly not `ve skills
  reify` (DEC-015 is Claude-only).
- **Releasing** section becomes the real checklist, matching what 0.6.0
  actually did: bump all three co-versioned manifests (DEC-014,
  test-enforced), `uv lock`, `ve plugin render` once per flavor, drift +
  version tests, commit, tag `releases/vX.Y.Z` (triggers
  `.github/workflows/publish.yml`, PyPI trusted publishing), push, then
  update both plugin channels (`/plugin update` for Claude; Cursor
  marketplace refresh/auto-refresh).
- **Developing the plugin** section: the template-edit → render → test loop
  and the three-layer testing story (CLI via `uv run ve` + pytest;
  structural plugin tests against repo files; live behavior via version
  bump + plugin update, headless `claude -p`, or a Cursor session).
- Fix the stale Project Structure listing (`commands/` no longer exists;
  `skills/`, `agents/`, `.cursor-plugin/` do).

DECISIONS.md: annotate DEC-014's "explicitly empty `hooks` object until a
Cursor hook counterpart exists" consequence, which this chunk makes stale.
No new ADR — the hook-vs-fallback question was delegated by DEC-014/DEC-013
and the answer (hook, because the event model supports it) is recorded here
and in the adapter's header comment.

Finally: this is the last chunk of `docs/narratives/cursor_plugin_port` —
set the narrative status to COMPLETED at chunk completion.

## Subsystem Considerations

- **docs/subsystems/template_system** (if present): NOT touched. Hooks are
  deliberately static files on both sides; the render pipeline
  (`src/plugin_render.py`) renders only `skills/` and `agents/` templates
  and never writes into `.cursor-plugin/hooks/`.

## Sequence

### Step 1: Manifest-fallback in the shared core

`hooks/session_start.sh`: after computing `plugin_manifest` from
`.claude-plugin/plugin.json`, fall back to
`${CLAUDE_PLUGIN_ROOT}/.cursor-plugin/plugin.json` when the Claude manifest
is absent. Update the header comment to note the hook is shared by both
editors' registrations and why the fallback is version-safe (DEC-014).

### Step 2: Cursor adapter script

`.cursor-plugin/hooks/session_start.sh` (mode 0755, POSIX sh):
- Header comment documenting the contract and the spec facts it rests on
  (JSON stdio, `additional_context`, fire-and-forget), with a
  `# Chunk: docs/chunks/dualplugin_lifecycle_release` backreference.
- Resolve `PLUGIN_ROOT` as `$(dirname $0)/../..` (the repo root), allow
  `CURSOR_PLUGIN_ROOT` to override.
- Export `CLAUDE_PROJECT_DIR` (from `CURSOR_PROJECT_DIR` when only that is
  set) and `CLAUDE_PLUGIN_ROOT`, run the core, capture stdout.
- Emit `{}` when the core said nothing; otherwise JSON-escape (backslash,
  double quote, newlines) with sed + a shell loop and emit
  `{"additional_context": "…"}`. Exit 0 unconditionally.

### Step 3: Cursor hooks config

`.cursor-plugin/hooks/hooks.json`:
```json
{
  "version": 1,
  "hooks": {
    "sessionStart": [
      { "command": "${CURSOR_PLUGIN_ROOT}/.cursor-plugin/hooks/session_start.sh" }
    ]
  }
}
```
`${CURSOR_PLUGIN_ROOT}` follows upstream's continual-learning precedent;
the adapter's self-location logic makes it robust even if the variable
resolves oddly, since the script path itself is what matters.

Update `.cursor-plugin/plugin.json`: `"hooks": "./.cursor-plugin/hooks/hooks.json"`.

### Step 4: Tests

- New `tests/test_cursor_session_hook.py`:
  - Registration: adapter exists and is executable; hooks.json declares
    `sessionStart` running the adapter; manifest points at hooks.json.
  - Behavior (subprocess, mirroring `test_session_hook.py` harness): build
    a tmp plugin root that copies the real core + adapter into the real
    layout; assert stdout parses as JSON; `{}` outside ve projects;
    `additional_context` carries the current-chunk line inside a ve
    project; `CURSOR_PROJECT_DIR`-only environment works; output with
    embedded quotes/newlines stays valid JSON; exit 0 throughout.
  - Core fallback: plugin root with only `.cursor-plugin/plugin.json`
    still yields a version (drift warning names it).
- `tests/test_cursor_manifest.py`: replace
  `test_hooks_declares_no_hook_events` with hook-declaration tests
  (declared path exists inside `.cursor-plugin/`, valid JSON, declares
  `sessionStart`, command script exists + executable, and the declaration
  still overrides root discovery). Extend `test_declared_path_exists`
  coverage to hooks.
- `tests/test_session_hook.py`: existing suite must keep passing (the
  fallback only adds a branch); add one test for the
  `.cursor-plugin`-manifest-only fallback if it fits more naturally there.

### Step 5: README

As described in Approach: Cursor Plugin install section (marketplace /
Import-from-Repo / local dev, plus a note that the same session hook runs
in Cursor), rewritten Releasing checklist, new "Developing the plugin"
section, corrected Project Structure block.

### Step 6: DECISIONS.md touch-up

Annotate DEC-014's hooks consequence bullet so it no longer claims the
placeholder is current.

### Step 7: Validation and completion

- `uv run ve plugin render --flavor claude` and `--flavor cursor` — expect
  zero diff (nothing template-sourced changed); confirms hooks work didn't
  disturb renders.
- `uv run pytest tests/` (full suite) and `uv run ve validate` clean.
- Update GOAL.md `code_paths`/`code_references`; set narrative
  `cursor_plugin_port` status COMPLETED; chunk complete.

## Dependencies

- dualplugin_cursor_render (ACTIVE) — the Cursor render surface and
  manifest declarations this chunk extends. Satisfied.

## Risks and Open Questions

- **Plugin-hook working directory / variable substitution is not fully
  specified.** The hooks doc defines CWD only for enterprise/team/project/
  user hook sources, not plugin hooks; `${CURSOR_PLUGIN_ROOT}` in commands
  is upstream precedent, not documented contract. Mitigated by the adapter
  resolving the root from `$0` — but live verification in a Cursor session
  was not possible from this environment, and is flagged as the remaining
  manual check.
- **`sessionStart` does not run in cloud agents** (documented limitation).
  Acceptable: fail-open, same as no hook.
- **Whether a Cursor marketplace install materializes the full repo**
  (including `.claude-plugin/`, `pyproject.toml`). Plugins are "distributed
  as Git repositories," so the DEC-013 bootstrap source should be present;
  the manifest fallback covers the manifest half, and the bootstrap already
  degrades to a hint when `pyproject.toml` is absent.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->
