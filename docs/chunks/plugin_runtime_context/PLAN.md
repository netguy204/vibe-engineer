

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Plugin command files are static markdown (DEC-010), so everything the template
system resolved at render time must become instructions the agent resolves at
execution time. Two render-time mechanisms are being replaced:

1. **`{% if task_context %}` conditionals** (with `{{ external_artifact_repo }}`
   and `{% for project in projects %}` interpolations) — replaced by a
   `!`-prefixed context line that prints `.ve-task.yaml` when present, plus
   runtime-conditional prose ("If this is a task workspace ..."). The values
   that Jinja2 interpolated (`external_artifact_repo`, `projects`) are exactly
   the keys `ve task init` writes into `.ve-task.yaml`
   (src/task_init.py#TaskInitializer.initialize), so surfacing the file's
   contents gives the agent the same data the renderer had.

2. **`ve_config` injection** — replaced by a `!`-prefixed context line that
   prints `.ve-config.yaml` when present, with documented defaults. The only
   config key today is `cluster_subsystem_threshold` (default 5, see
   src/template_system.py#load_ve_config); no command template currently
   interpolates it, so for the pilot this is purely the conventional mechanism
   that later ports rely on.

**Form of the convention**: an embedded standard preamble (a `## Context`
block of `!` lines plus a `## Runtime context` instruction section) that each
ported command carries verbatim, documented once in a porting guide. The
narrative offered "a reusable preamble or skill reference"; the preamble is
chosen over a skill indirection because commands stay self-contained — an
agent reading one command file needs no second fetch to know how to behave,
and the wave-3 ports become a mechanical copy-paste plus per-block rewrite.

**Where the guide lives**: `docs/chunks/plugin_runtime_context/PORTING_GUIDE.md`
— a chunk artifact. The wave-3 chunks (plugin_core_commands,
plugin_orch_commands) already `depends_on` this chunk and their GOALs say "per
the plugin_runtime_context convention and porting guide", so the chunk
directory is where they will look. The durable intent (plugin commands detect
context at runtime) is owned by this chunk's GOAL.md per the intent-ownership
model; the guide is the mechanical companion.

**Pilot**: `commands/chunk-create.md`, ported end-to-end from
src/templates/commands/chunk-create.md.jinja2 following plugin_scaffold's
conventions (frontmatter `name`/`description`/`allowed-tools`; bare `ve`, not
`uv run ve`; probe presence with `ve --help` since `ve` has no `--version`;
failure-mode instructions; HTML-comment chunk backreference). The
auto-generated header partial is dropped — plugin files are source, not render
output. Source templates in src/templates/commands/ are NOT deleted or
modified (plugin_init_slimdown owns that).

**Testing** (per docs/trunk/TESTING_PHILOSOPHY.md): tests are written first in
tests/test_plugin_commands.py. Two layers:

- **Generic invariants over every `commands/*.md`** — valid frontmatter with
  `name`/`description`, no Jinja2 syntax (`{%`, `{{`, `{#`), no AUTO-GENERATED
  header. These run for free against every command the wave-3 chunks add,
  giving the mass ports standing regression coverage.
- **Pilot-specific assertions** — chunk-create.md detects `.ve-task.yaml` and
  `.ve-config.yaml`, preserves the task-context guidance (external artifact
  repo routing) as runtime conditionals, keeps `$ARGUMENTS`, keeps the
  intent-judgment gate, and carries the chunk backreference.

The three behavioral situations from the success criteria (plain project /
project with .ve-config.yaml / task workspace) are verified by executing the
preamble's `!` shell lines in three temp directories and asserting the output
distinguishes the situations — this tests the actual detection mechanism the
agent will see, not just the markdown text.

## Subsystem Considerations

- **docs/subsystems/template_system** (status: see OVERVIEW.md): this chunk
  documents the runtime replacement for two of its render-time features
  (`task_context` conditionals, `ve_config` injection) but does not modify the
  subsystem's code. src/template_system.py and src/task_init.py are read-only
  references here; removal of the commands collection belongs to
  plugin_init_slimdown.

## Sequence

### Step 1: Write failing tests

Create `tests/test_plugin_commands.py`:

- `TestCommandInvariants` (parameterized over `commands/*.md`):
  - frontmatter parses and has non-empty `name` and `description`; `name`
    matches the file stem
  - body contains no `{%`, `{{`, or `{#` (no Jinja2 syntax)
  - body contains no "AUTO-GENERATED" header
- `TestChunkCreateCommand`:
  - `commands/chunk-create.md` exists; frontmatter name is `chunk-create`
  - body references `.ve-task.yaml` and `.ve-config.yaml` (runtime detection)
  - body preserves task-context guidance: mentions `external_artifact_repo`
    and external-repo artifact routing as a runtime conditional
  - body keeps `$ARGUMENTS` and the chunk backreference comment
    (`docs/chunks/plugin_runtime_context`)
- `TestRuntimeDetection` (three-situation check):
  - extract the `` !`...` `` shell lines from chunk-create.md's Context block
  - run them (via `bash -c`) in three temp dirs: empty; with `.ve-config.yaml`
    (`cluster_subsystem_threshold: 3`); with `.ve-task.yaml`
    (`external_artifact_repo`/`projects` keys)
  - assert each situation produces distinguishable output (fallback text in
    the empty dir; file contents in the others)

Run `uv run pytest tests/test_plugin_commands.py` and confirm the new tests
fail (commands/chunk-create.md does not exist yet).

### Step 2: Write the porting guide with the canonical preamble

Create `docs/chunks/plugin_runtime_context/PORTING_GUIDE.md` containing:

1. **The convention** — how plugin commands resolve context at runtime:
   - task context: `.ve-task.yaml` at the workspace root (the session cwd in
     a task workspace) is the detection signal; its `external_artifact_repo`
     and `projects` keys carry the values templates used to interpolate
   - project config: `.ve-config.yaml` at the project root; known keys and
     defaults (`cluster_subsystem_threshold: 5`); absence means defaults
2. **The canonical preamble** — the exact `## Context` block (`!` lines with
   fallback chains for ve CLI, `.ve-task.yaml`, `.ve-config.yaml`) and the
   `## Runtime context` instruction section (ve missing → suggest
   `uv tool install vibe-engineer`; uninitialized → suggest `ve init`; task
   workspace and config interpretation rules) to paste into every ported
   command.
3. **Mechanical porting steps** — numbered recipe for converting one
   `src/templates/commands/<name>.md.jinja2` into `commands/<name>.md`:
   frontmatter mapping (add `allowed-tools`), drop the auto-generated header
   include, fold the common-tips include into the preamble, rewrite
   `{% if task_context %}` blocks as "If this is a task workspace" prose,
   rewrite `{% if %}/{% else %}` pairs as both-variants-with-conditions,
   replace `{{ external_artifact_repo }}`/`{% for project in projects %}`
   with references to the `.ve-task.yaml` keys, keep `$ARGUMENTS`, add the
   porting chunk's backreference, and a final no-Jinja2 grep check.
4. **Worked example** — pointer to commands/chunk-create.md as the reference
   port, with the template's task_context block and its ported form shown
   side by side.

### Step 3: Port chunk-create

Create `commands/chunk-create.md` from chunk-create.md.jinja2 by applying the
guide's recipe exactly (the pilot must be a faithful application of the
recipe, since wave-3 agents will treat the pair as guide + worked example):

- frontmatter: `name: chunk-create`, description copied from the template,
  `allowed-tools` covering the preamble probes and the ve invocations the
  body uses (`ve chunk create`, `ve chunk list`, `ve chunk suggest-prefix`
  is not used here — check the template body for the exact set)
- chunk backreference comment for docs/chunks/plugin_runtime_context
- canonical preamble (Context block + Runtime context section)
- the template's task_context block ("creates artifacts in the external
  artifact repo ...") preserved as a runtime conditional under the task
  workspace branch
- the 10 instruction steps carried over verbatim (no behavioral changes to
  the command itself), `$ARGUMENTS` intact

### Step 4: Make tests pass and run the three-situation check

`uv run pytest tests/test_plugin_commands.py tests/test_plugin_manifest.py`
until green. Then run the full suite `uv run pytest tests/` and compare
against the pre-existing-failure baseline (32 known failures on main —
subsystem test files + one orchestrator daemon negative-pid test); no new
failures attributable to this chunk.

### Step 5: Update chunk metadata

Update `docs/chunks/plugin_runtime_context/GOAL.md` `code_paths` with the
files touched. Record any deviations in this PLAN.md.

## Dependencies

- **plugin_scaffold** (ACTIVE) — supplies the plugin layout, manifest, the
  ve-status pilot whose conventions this chunk extends, and
  tests/test_plugin_manifest.py whose helpers the new tests mirror.

## Risks and Open Questions

- **`!` context-line portability**: the preamble's shell fallback chains must
  behave on a plain POSIX shell. Mitigated by the three-situation test that
  actually executes the extracted lines.
- **Workspace-root ambiguity**: an agent whose cwd is *inside* a participating
  project (not the task root) won't see `.ve-task.yaml` in cwd. The convention
  documents that the workspace root is the session cwd in a task workspace
  (where `ve task init` renders today) and tells the agent to check one parent
  level before concluding it is not in a task. Deeper resolution is out of
  scope.
- **allowed-tools breadth**: too narrow and the `!` lines silently fail; too
  broad and the command pre-approves writes. Follow ve-status's pattern and
  list only what the command actually runs.
- **Guide drift**: wave-3 agents may improvise if the recipe is ambiguous.
  Mitigated by the side-by-side worked example and the generic invariant
  tests that fail on any Jinja2 leftovers in commands/.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
