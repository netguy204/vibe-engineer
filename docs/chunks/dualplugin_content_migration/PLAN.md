

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Mechanical migration of the remaining 36 commands and 2 agents into
`src/templates/plugin/`, following
`docs/chunks/dualplugin_template_source/TEMPLATING_GUIDE.md` §6 per file. The
render contract, idiom macros, marker convention, and byte-stability rules
are all inherited from dualplugin_template_source — this chunk adds content
only and touches no renderer code (`src/plugin_render.py` and
`src/cli/plugin.py` are owned by the concurrently-running
dualplugin_cursor_scaffold and already handle the `agents/` subdirectory
generically via `output_path`).

Because the migration standard is byte-stability (each Claude render must be
identical to the committed file except the added generated marker), the
templates are produced by a **one-time generation script** kept as a chunk
artifact (`docs/chunks/dualplugin_content_migration/migrate_templates.py`).
The script derives each template from its committed render and self-verifies:
after writing a template, it renders it through
`plugin_render.render_plugin_template` and asserts the output equals the
committed file with exactly one inserted marker line. Any other diff aborts
the migration for that file. This turns the byte-stability bar into an
executable check instead of a hand-eyeballed one.

A pre-migration survey of all 38 files classified the corpus:

| Class | Files | Template shape |
|---|---|---|
| Canonical preamble, no command-specific bullets | 26 commands | `{{ idioms.canonical_preamble() }}` |
| Canonical preamble + trailing task-workspace bullets | 8 commands (chunk-complete, chunk-execute, chunk-implement, chunk-plan, discover-subsystems, investigation-create, narrative-compact, subsystem-discover) | `{% call idioms.canonical_preamble() -%} ... {%- endcall %}` |
| Nonstandard context block (extra probes beyond the standard three) | 2 commands (chunk-commit, chunk-execute-all) | own `## Context` heading, `{{ idioms.probe(...) }}` per probe line, runtime-context prose verbatim (the ve-status pilot pattern) |
| Agents (no context block, `tools:` frontmatter key) | 2 (chunk-executor, intent-auditor) | literal frontmatter + `{{ idioms.generated_marker(source_template) }}` + body verbatim |

Survey facts the plan relies on:

- No command or agent body contains `{{`, `{%`, or `{#` — no `{% raw %}`
  wrapping is needed anywhere (the friction-log/validate-fix brace history
  flagged in the wave-1 handoff concerns only single-brace placeholders like
  `{chunk_name}`, which are Jinja2-inert).
- No file references `${CLAUDE_PLUGIN_ROOT}`, so `idioms.plugin_root()` is
  unused by this wave.
- Every command frontmatter is exactly `name` / `description` /
  `allowed-tools` (single-line each); both agents are `name` / `description`
  / `tools`. `chunk-execute.md`'s description is YAML-double-quoted in the
  committed file; the quotes are part of the verbatim line and are passed
  through the `frontmatter` macro inside the description argument.
- Chunk backreference HTML comments, task-workspace guidance, chunk-review's
  verbatim ReviewDecision references, and steward/swarm channel-naming
  guidance all live in the verbatim body and survive untouched by
  construction.

**Agent frontmatter deviation (decided at planning time):** the
`idioms.frontmatter` macro emits an `allowed-tools:` line and cannot emit the
agents' `tools:` key. Extending the macro vocabulary mid-flight is off the
table — `partials/claude/idioms.md.jinja2` documents the five-macro signature
set as the flavor-substitution interface, and dualplugin_cursor_scaffold is
concurrently implementing `partials/cursor/` against exactly that set. The
two agent templates therefore carry their frontmatter as literal text and use
only `generated_marker` from the idiom vocabulary. Consequence for
dualplugin_cursor_render: agent frontmatter does NOT flavor-substitute; if
Cursor needs a different agent frontmatter shape, that chunk must either add
an `agent_frontmatter` macro to both partials or post-process. Recorded in
Deviations and in the executor handoff.

Testing follows docs/trunk/TESTING_PHILOSOPHY.md by extending the existing
parametrized drift suite (which auto-covers every new template) with a
completeness check, rather than per-file assertions: the new test fails when
a committed `commands/*.md` or `agents/*.md` exists without a corresponding
template (a hand-added rendered file would otherwise silently escape drift
coverage).

## Subsystem Considerations

- **docs/subsystems/template_system** (DOCUMENTED): this chunk USES the
  subsystem — all templates render through the shared `plugin` Jinja2
  environment via `plugin_render.render_plugin_template`. No environment
  changes (the byte-stability rules in TEMPLATING_GUIDE §7 forbid
  `trim_blocks`/`lstrip_blocks` flips). No new deviations discovered.

## Sequence

### Step 1: Write the migration script (chunk artifact)

`docs/chunks/dualplugin_content_migration/migrate_templates.py`:

1. For each of the 36 commands and 2 agents, read the committed file and
   split frontmatter from body.
2. Emit the template per the class table above:
   - import line (TEMPLATING_GUIDE §3) as line 1;
   - `{{ idioms.frontmatter(...) }}` (commands) or literal frontmatter
     (agents), copying name/description/tools verbatim;
   - `{{ idioms.generated_marker(source_template) }}` as the first body
     line, then the body verbatim;
   - for canonical files, the exact canonical-preamble text (rendered once
     from the macro for comparison) is replaced with the macro call /
     `{% call %}` block; for chunk-commit and chunk-execute-all, only the
     probe lines are replaced with `idioms.probe(...)` calls.
   - String arguments are emitted as Jinja literals with quote style chosen
     per content (double-quoted, single-quoted, or escaped).
3. Self-verify: render each written template (claude flavor) and assert it
   equals the committed file with exactly the one marker line inserted after
   the frontmatter. Abort loudly on any other diff.

Output: 36 files in `src/templates/plugin/commands/`, 2 in
`src/templates/plugin/agents/`.

### Step 2: Run the script and spot-check

Run the script; manually inspect representative templates from each class
(one canonical-empty, one `{% call %}`, chunk-commit, one agent) against the
pilots for style consistency (multi-line frontmatter call formatting).

### Step 3: Re-render the committed outputs

`uv run ve plugin render` — rewrites all of `commands/*.md` and
`agents/*.md`. Verify `git diff` shows, for every pre-existing file, exactly
one added line (the marker) and nothing else. The two pilots must show no
diff at all.

### Step 4: Extend the drift suite's collection-layout coverage

In `tests/test_plugin_render.py`, extend `TestCollectionLayout` (per the
wave-1 handoff: extend, don't rewrite `test_pilot_templates_exist`):

- a completeness test asserting a 1:1 mapping between collection templates
  and committed `commands/*.md` / `agents/*.md` files in both directions;
- an explicit count/membership assertion that the collection now covers all
  38 commands and 2 agents.

The parametrized `TestDrift` class picks up all 38 new templates
automatically — no edits there.

### Step 5: Verify suites and baseline

- `uv run pytest tests/test_plugin_render.py tests/test_plugin_commands.py
  tests/test_plugin_agents.py tests/test_plugin_manifest.py` — all green,
  including the pinned chunk-executor lifecycle invariants ("/chunk-plan" …
  "3 times maximum", SUCCESS/FAILURE) and intent-auditor rules.
- `uv run ve validate` — chunk backreference integrity unchanged.
- Full `uv run pytest tests/` — failures must not exceed the inherited
  baseline (32 failures / 4036 passed after wave 1).

### Step 6: Update GOAL.md code references and commit

Populate `code_references`, commit templates + re-rendered outputs + test
extension + chunk docs on this worktree branch (never staging the forbidden
paths: .entities/, idea.md, src/psutil*, watch_20260415-180006,
docs/articles/).

## Dependencies

- **dualplugin_template_source** (ACTIVE, merged as 775fce5): collection
  layout, claude idioms partial, renderer, drift suite, marker convention.
- Runs concurrently with **dualplugin_cursor_scaffold**, which owns
  `src/plugin_render.py`, `src/cli/plugin.py`, `partials/cursor/`, the two
  pilot templates, `.cursor-plugin/`, `docs/trunk/DECISIONS.md`, `README.md`,
  and `tests/test_plugin_manifest.py` — none of which this chunk touches.

## Risks and Open Questions

- **Canonical-preamble false positives**: a file might contain the canonical
  text plus subtle whitespace variation that the survey's exact-substring
  match missed in the runtime bullets. Mitigated by the script's per-file
  render-and-compare verification — any mismatch aborts that file's
  migration rather than committing a lossy template.
- **Jinja string-literal escaping** for descriptions containing both quote
  characters (chunk-execute). Mitigated by the same self-verification.
- **Merge adjacency with dualplugin_cursor_scaffold**: both branches add
  tests to `tests/test_plugin_render.py`. This chunk only extends
  `TestCollectionLayout`; scaffold work centers on flavors/CLI tests.
  Textual conflicts are possible but semantically orthogonal.
- The migration script is a one-time artifact; it is not maintained code and
  lives in the chunk directory per the chunk-artifact convention.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION, not at planning time. -->

- **Agent frontmatter is literal, not macro-emitted** (decided at planning
  time, confirmed during implementation): `idioms.frontmatter` emits
  `allowed-tools:`; agents need `tools:`. Extending the five-macro
  flavor-substitution interface mid-flight would race
  dualplugin_cursor_scaffold's `partials/cursor/` implementation of the same
  signatures. The two agent templates carry literal frontmatter and use only
  `generated_marker`. Flagged as a handoff for dualplugin_cursor_render.
- **Byte-stability outcome**: all 38 pre-existing rendered files differ from
  their pre-chunk state by exactly the one added marker line; the two pilot
  renders are byte-identical to their wave-1 state. No other diffs.
