

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Build a new build-time template collection `src/templates/plugin/` that holds
plugin command bodies once, with editor-specific idioms factored into a
per-flavor partial of Jinja2 macros (`partials/claude/idioms.md.jinja2`). A
new `src/plugin_render.py` module reuses the existing template machinery
(`src/template_system.py#get_environment` / `render_template` — per the
template_system subsystem, no second renderer) to render the Claude flavor of
every collection template into `commands/`. A new `ve plugin render` CLI
group (`src/cli/plugin.py`) exposes this; it refuses to run outside the
plugin source repo (guard: `.claude-plugin/plugin.json` must exist at the
target root).

Key design points:

- **Flavor substitution via macro import**: each command template starts with
  `{% import "partials/" ~ flavor ~ "/idioms.md.jinja2" as idioms %}`. The
  renderer passes `flavor` ("claude" for this chunk) and `source_template`
  (the collection-relative template path). dualplugin_cursor_scaffold adds
  `partials/cursor/idioms.md.jinja2` implementing the same macro signatures —
  that signature set is the substitution interface.
- **Macro vocabulary** (the partial vocabulary the migration chunk reuses):
  - `frontmatter(name, description, allowed_tools=None)` — YAML frontmatter;
    Claude emits `allowed-tools:` as a comma-joined list; other flavors may
    omit/map it.
  - `generated_marker()` — the generated-from-template comment; interpolates
    `source_template`. Wording deliberately avoids the legacy
    "AUTO-GENERATED" substring (see Marker collision risk in GOAL.md).
  - `probe(label, command)` — one context-probe line; Claude renders the
    `` !`...` `` preprocessing idiom.
  - `canonical_preamble()` — the canonical `## Context` + `## Runtime
    context` block from PORTING_GUIDE.md section 2, built on `probe()`.
    Command-specific task-workspace guidance is supplied via Jinja `{% call
    %}` body and lands as trailing bullets inside Runtime context.
  - `plugin_root()` — the plugin-root environment reference
    (`${CLAUDE_PLUGIN_ROOT}` for Claude). Neither pilot uses it, but the
    vocabulary must exist for the 36-command migration (several commands
    reference plugin files).
- **Marker convention**: rendered files carry, immediately after the
  frontmatter, `<!-- GENERATED from src/templates/plugin/<path>.jinja2 — edit
  that template and run `ve plugin render`; direct edits here will be
  overwritten. -->`. This does not contain "AUTO-GENERATED", so
  `_is_ve_generated_file()` legacy cleanup and the existing
  no-AUTO-GENERATED invariant tests are unaffected.
- **Byte stability**: Jinja2 strips one trailing newline; the writer
  normalizes output to end with exactly one `\n`. Pilot templates are
  authored so `uv run ve plugin render` reproduces the committed
  `commands/ve-status.md` and `commands/chunk-create.md` byte-for-byte
  *after* the marker line is added to them (the marker is the single
  deliberate diff — see Deviations). Verified with `git diff` /
  `cmp` during implementation and enforced forever by the drift test.
- **Drift test**: `tests/test_plugin_render.py` parametrizes over every
  template in the collection; for each, a fresh in-process render must equal
  the committed file's bytes, and the rendered text must carry the marker.
  This fails when (a) a template is edited without re-rendering, or (b) a
  committed render is hand-edited.

Testing follows docs/trunk/TESTING_PHILOSOPHY.md: the drift test and marker
tests are written first (red against the unmodified commands/ files), then
the collection + renderer turn them green. The existing invariant suites
(test_plugin_commands.py, test_plugin_agents.py, test_plugin_manifest.py,
test_session_hook.py) continue to pass — the new marker wording is chosen so
`test_no_auto_generated_header` needs no semantic change.

This is deliberately not a relitigation of DEC-010: the old
`src/templates/commands/` collection rendered per-consuming-project at `ve
init` time; this collection renders once, at build time, in this repository,
and the outputs are committed. Consuming repos still receive nothing. The
marker text and the templating guide record this kind distinction.

## Subsystem Considerations

- **docs/subsystems/template_system** (status: see OVERVIEW.md): this chunk
  USES the subsystem — `src/plugin_render.py` builds on
  `template_system.get_environment`/`render_template` and the
  `src/templates/<collection>/` layout (collection with `partials/`
  excluded from direct rendering) rather than introducing a second renderer.
  The new collection follows the existing pattern; no deviations introduced.

## Sequence

### Step 1: Failing drift/marker tests (red)

Create `tests/test_plugin_render.py`:

- `list_plugin_templates()`-driven parametrized drift test: fresh render of
  each collection template equals the committed output file bytes.
- Marker tests: rendered output contains `GENERATED from
  src/templates/plugin/...` pointing at its own template; rendered output
  does NOT contain `AUTO-GENERATED` (collision guard).
- Pilot coverage test: the collection covers exactly
  `commands/ve-status.md.jinja2` and `commands/chunk-create.md.jinja2` for
  now (asserts the two pilots exist; the migration chunk will extend, not
  rewrite, this test).
- CLI tests (CliRunner): `ve plugin render` outside a plugin source repo
  fails with a clear error; inside a scratch copy with
  `.claude-plugin/plugin.json` it writes the rendered files and reports them.

These fail initially (module and collection don't exist).

### Step 2: The collection and Claude idiom partial

Create `src/templates/plugin/partials/claude/idioms.md.jinja2` with the five
macros above, and the two pilot templates:

- `src/templates/plugin/commands/ve-status.md.jinja2` — uses
  `frontmatter(...)`, `generated_marker()`, and `probe(...)` for its three
  custom context lines; body verbatim from the committed file.
- `src/templates/plugin/commands/chunk-create.md.jinja2` — uses
  `frontmatter(...)`, `generated_marker()`, and `canonical_preamble()` with
  the chunk-create task-workspace bullet supplied via `{% call %}`; the
  Instructions body verbatim.

### Step 3: src/plugin_render.py

Renderer module reusing template_system:

- `list_plugin_templates() -> list[str]` — collection-relative names
  (`commands/*.md.jinja2`), partials excluded, sorted.
- `output_path(template_name, repo_root) -> pathlib.Path` — strips
  `.jinja2`, maps `commands/x.md.jinja2` → `<repo_root>/commands/x.md`.
- `render_plugin_template(template_name, flavor="claude") -> str` — calls
  `template_system.render_template("plugin", ...)` with `flavor` and
  `source_template` context; normalizes to a single trailing newline.
- `render_plugin_collection(repo_root, flavor="claude") -> RenderResult`-like
  summary of written paths.

### Step 4: ve plugin render CLI

`src/cli/plugin.py`: `plugin` click group with `render` command
(`--flavor claude` choice, default claude). Guard: error out unless
`.claude-plugin/plugin.json` exists under the target root (cwd). Register
the group in `src/cli/__init__.py`.

### Step 5: Render, verify byte-stability, commit the marker diff

Run `uv run ve plugin render`. Verify with `git diff commands/` that the
ONLY change to each pilot file is the added marker line (the deliberate
diff), and that re-running the command is idempotent. Then the drift test
goes green.

### Step 6: Invariant-suite adjustment

Run test_plugin_commands.py / test_plugin_agents.py / test_plugin_manifest.py
/ test_session_hook.py. Expected: no behavioral change needed because the
marker avoids the `AUTO-GENERATED` substring; add a clarifying comment to
`test_no_auto_generated_header` noting the legacy header it guards against
and that the new `GENERATED from` marker is required separately by
test_plugin_render.py. Adjust only if something actually fails.

### Step 7: Templating guide for the migration chunk

Write `docs/chunks/dualplugin_template_source/TEMPLATING_GUIDE.md` (chunk
artifact, mirroring the PORTING_GUIDE.md precedent): collection layout, the
macro vocabulary and signatures, the `flavor`/`source_template` render
context contract, marker convention, byte-stability rules (trailing-newline
normalization, whitespace-control conventions), and the mechanical recipe
for porting one of the remaining 36 commands into the collection.

### Step 8: Full test run and backreferences

Add `# Chunk: docs/chunks/dualplugin_template_source` backreferences to the
new modules. Run `uv run pytest tests/` and compare against the inherited
baseline (32 failures / 4020 passes on main); no new failures allowed.

## Dependencies

- None beyond what exists: Jinja2 is already a dependency;
  `src/template_system.py` provides the renderer; the committed
  `commands/ve-status.md` and `commands/chunk-create.md` are the
  byte-stability references.

## Risks and Open Questions

- **Byte-exactness vs Jinja whitespace control**: macros and `{% call %}`
  blocks make whitespace fiddly. Mitigation: drift test compares bytes, and
  implementation iterates with `git diff` until only the marker line
  changes.
- **Marker substring collisions**: the chosen wording must never contain
  `AUTO-GENERATED` (legacy cleanup in `src/project.py#_is_ve_generated_file`
  and the invariant tests key on it). Guarded by an explicit test.
- **CLI guard**: `ve plugin render` must not scaffold a `commands/` dir in
  arbitrary consuming projects. Guard on `.claude-plugin/plugin.json`.
- **Wheel build**: renders are committed, so the hatch force-include of
  `commands/` as orchestrator phase prompts is unaffected; no packaging-time
  render step.

## Deviations

- **Deliberate diff to the pilot commands (planned, executed in Step 5)**:
  `commands/ve-status.md` and `commands/chunk-create.md` each gain one line —
  the `<!-- GENERATED from src/templates/plugin/... -->` marker immediately
  after the frontmatter. Everything else renders byte-identical to the
  previously committed content. This is required by the success criterion
  that rendered files carry the marker; it is the only diff.
