# Implementation Plan

## Approach

Apply the mechanical porting recipe in
`docs/chunks/plugin_runtime_context/PORTING_GUIDE.md` to the 20 remaining
core workflow command templates, producing one static markdown file in
`commands/` per command. `commands/chunk-create.md` (the pilot from
`plugin_runtime_context`) is the worked example whose shape every port
follows; source templates in `src/templates/commands/` stay untouched
(their removal belongs to `plugin_init_slimdown`).

Per DEC-010, plugin command files are static markdown: everything the
template system resolved at render time is resolved at execution time.
Concretely, for each `src/templates/commands/<name>.md.jinja2` →
`commands/<name>.md`:

1. **Frontmatter**: keep `name` (must equal the file stem), write a
   `description` that states trigger conditions so the model can invoke the
   command proactively as a skill (GOAL success criterion). Add
   `allowed-tools` covering the canonical preamble probes
   (`Bash(ve --help:*)`, `Bash(cat:*)`) plus one entry per distinct `ve`
   invocation the body instructs.
2. **Backreference**: an HTML comment
   `<!-- Chunk: docs/chunks/plugin_core_commands - Static plugin port of <name> -->`
   immediately after the frontmatter. Existing `{# Chunk: ... #}` Jinja
   comments in templates convert to HTML comments so their archaeology
   survives.
3. **Canonical preamble**: the `## Context` block (three `!`-lines: ve CLI
   presence probe, `.ve-task.yaml` cat with `../` fallback, `.ve-config.yaml`
   cat with fallback) and the `## Runtime context` instruction section,
   verbatim from the porting guide. This replaces the `## Tips` section and
   the common-tips partial.
4. **Drop render machinery**: `{% set source_template %}`, the
   AUTO-GENERATED header partial, `{% raw %}`/`{% endraw %}` wrappers
   (friction-log, validate-fix — their contents carry over unwrapped).
5. **Task-context rewrites**: guidance-only `{% if task_context %}` blocks
   become prose runtime conditionals ("If this is a task workspace (the
   Task workspace context above shows `.ve-task.yaml` contents): ...")
   inside the Runtime context section; dual-variant if/else blocks
   (chunk-complete, chunk-update-references) keep BOTH variants, each
   introduced by its condition; `{{ external_artifact_repo }}` and
   `{% for project in projects %}` interpolations become references to the
   corresponding `.ve-task.yaml` keys.
6. **Body verbatim**: numbered instructions, `$ARGUMENTS`, examples, and
   bare `ve` invocations carry over without behavioral change.

The existing parameterized invariants in
`tests/test_plugin_commands.py#TestCommandInvariants` (frontmatter
name/description, no Jinja2 syntax, no AUTO-GENERATED header) automatically
cover every new file in `commands/`, so no new test code is required —
the testing philosophy's "tests verify documented intent" is satisfied by
the suite picking up the 20 new files. A final
`grep -nE '\{%|\{\{|\{#' commands/*.md` must match nothing.

## Subsystem Considerations

No documented subsystems govern the plugin command surface. The relevant
convention is the porting guide owned by `docs/chunks/plugin_runtime_context`,
which this chunk applies but does not modify.

## Sequence

### Step 1: Port the lifecycle core (chunk-plan, chunk-implement, chunk-complete, chunk-execute)

These four carry the richest Jinja2: task-context guidance blocks with
`projects` loops (chunk-implement, chunk-execute), and chunk-complete's
dual-variant if/else blocks for the code-reference format plus a
task-only step 15 (commit in the artifact repo) that becomes a runtime
conditional step. chunk-plan's task block is guidance-only.

### Step 2: Port the review/commit/repair commands (chunk-review, chunk-commit, chunk-rebase, chunk-demote)

chunk-review has no task blocks but three template-comment backreferences
to convert. chunk-commit is already static in the template (it has its own
git-context `!`-lines and allowed-tools); it gains the canonical preamble,
the chunk backreference, and `Bash(ve chunk list:*)` for its current-chunk
probe while keeping its git context lines. chunk-rebase keeps its
git-merge workflow verbatim and gains git entries in allowed-tools for the
commands its body instructs. chunk-demote is a straight port.

### Step 3: Port the reference-maintenance commands (chunk-update-references, chunks-resolve-references, cluster-rename)

chunk-update-references has the dual-variant symbolic-reference format
block — keep both variants. chunks-resolve-references is tiny (a grep plus
parallel sub-agent fan-out of /chunk-update-references); it still gets the
full canonical preamble.

### Step 4: Port the narrative commands (narrative-create, narrative-compact, narrative-execute)

narrative-compact has a guidance-only task block. narrative-execute
contains the inline chunk-executor agent prompt in Phase 4 — carry it
verbatim (the `plugin_subagents` chunk later decides whether to promote it
to a named agent).

### Step 5: Port the discovery/record commands (investigation-create, subsystem-discover, discover-subsystems, decision-create, friction-log, validate-fix)

investigation-create and subsystem-discover have guidance-only task
blocks. friction-log and validate-fix unwrap their `{% raw %}` blocks.
decision-create is the smallest port (no ve invocations beyond the
probes).

### Step 6: Write proactive skill descriptions

For every ported command, replace the template's bare description with one
that states trigger conditions ("Use when ..."), using the rendered
`.claude/commands/*.md` descriptions and CLAUDE.md's command list as the
starting point. Keep `name` equal to the file stem.

### Step 7: Verify

- `grep -nE '\{%|\{\{|\{#' commands/*.md` matches nothing.
- `uv run pytest tests/test_plugin_commands.py` passes (invariants
  parameterize over all 22 files: 20 new + chunk-create + ve-status).
- `uv run pytest tests/` shows no regressions beyond the 32 pre-existing
  failures on main (subsystem test files + orchestrator daemon
  negative-pid test).
- Spot-check chunk-plan, narrative-create, and validate-fix for: canonical
  preamble present, allowed-tools covering each `ve` invocation in the
  body, task-context guidance preserved where the source had it.

## Dependencies

- `plugin_runtime_context` (ACTIVE) — supplies the porting guide, the
  canonical preamble, the chunk-create worked example, and the generic
  test invariants this chunk relies on.

## Risks and Open Questions

- **allowed-tools beyond `ve`**: chunk-commit and chunk-rebase instruct
  git operations. The recipe only mandates probe + `ve` entries;
  chunk-commit's template already ships git allowed-tools, so they are
  kept, and chunk-rebase gets the git entries its body instructs. This is
  a small, documented extension of the recipe.
- **chunk-review's ReviewDecision tool**: the body references a
  `ReviewDecision` tool that may not exist in every consuming environment.
  Ported verbatim per the recipe — behavior changes are out of scope.
- **Hardcoded cluster threshold**: chunk-plan's body says "5+ chunks"
  rather than injecting `cluster_subsystem_threshold`. The canonical
  Runtime context section explains the config key and its default, so the
  body stays verbatim.

## Deviations

<!-- Populated during implementation. -->
