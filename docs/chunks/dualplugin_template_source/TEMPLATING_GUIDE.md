# Templating Guide: the src/templates/plugin/ Collection

<!-- Chunk: docs/chunks/dualplugin_template_source - Build-time plugin template collection -->

This guide is the mechanical recipe for the chunks that build on the plugin
template layer: **dualplugin_content_migration** (move the remaining 36
commands and 2 agents into the collection) and **dualplugin_cursor_scaffold**
(add the Cursor flavor). The worked examples are the two pilots —
`src/templates/plugin/commands/ve-status.md.jinja2` (custom context probes)
and `src/templates/plugin/commands/chunk-create.md.jinja2` (canonical
preamble + task guidance) — read each next to its committed render in
`commands/` when in doubt.

## 1. Kind distinction (why this is not DEC-010 relitigated)

The old `src/templates/commands/` collection (deleted by
plugin_init_slimdown) rendered per-consuming-project at `ve init` time. This
collection renders **once, at build time, in this repository**, and the
outputs are **committed**. Consuming repos still receive nothing; the wheel
build is unaffected (pyproject's force-include ships the committed
`commands/` as orchestrator phase prompts — no render step at packaging
time).

## 2. Collection layout

```
src/templates/plugin/
  partials/
    claude/
      idioms.md.jinja2        # Claude-flavor idiom macros (the substitution point)
    cursor/                   # added by dualplugin_cursor_scaffold
      idioms.md.jinja2        # same macro signatures, Cursor idioms
  commands/
    <name>.md.jinja2          # one template per command; renders to commands/<name>.md
  agents/                     # added by dualplugin_content_migration
    <name>.md.jinja2          # renders to agents/<name>.md
```

Rules enforced by `src/plugin_render.py` and `tests/test_plugin_render.py`:

- A template's collection-relative path minus `.jinja2` is its output path
  from the repo root: `commands/foo.md.jinja2` → `commands/foo.md`. (For the
  Cursor flavor, `output_path` will grow a flavor-aware mapping —
  dualplugin_cursor_scaffold owns that.)
- Everything under `partials/` is import material, never rendered directly.
- Output is normalized to exactly one trailing newline.

## 3. The render contract

`plugin_render.render_plugin_template(template_name, flavor)` renders with
exactly two context variables; templates must not rely on anything else:

| Variable | Value | Used for |
|---|---|---|
| `flavor` | `"claude"` (more later) | selecting the idiom partial |
| `source_template` | `src/templates/plugin/<template_name>` | the generated marker |

Every command template begins with this exact import line:

```jinja2
{%- import "partials/" ~ flavor ~ "/idioms.md.jinja2" as idioms -%}
```

## 4. The idiom macro vocabulary

`partials/<flavor>/idioms.md.jinja2` must define these five macros — the
signature set IS the flavor-substitution interface. All macros emit content
**without** a trailing newline; the calling template owns line structure.

| Macro | Claude rendering |
|---|---|
| `frontmatter(name, description, allowed_tools=None)` | YAML frontmatter; `allowed_tools` (a list of strings) joins comma-separated into `allowed-tools:`; omitted entirely when `None`. Other flavors may drop or remap the tools line. |
| `generated_marker(source_template)` | `<!-- GENERATED from <path> — edit that template and run `ve plugin render`; direct edits here will be overwritten. -->` |
| `probe(label, command)` | One context-probe line: `` - <label>: !`<command>` `` (the `!` preprocessing idiom). Cursor renders these as run-these-first instructions instead. |
| `canonical_preamble()` | The canonical `## Context` + `## Runtime context` block from docs/chunks/plugin_runtime_context/PORTING_GUIDE.md section 2 (three standard probes, four standard runtime bullets). Command-specific task-workspace guidance is appended via a `{% call %}` body (see below). |
| `plugin_root()` | `${CLAUDE_PLUGIN_ROOT}` |

## 5. Marker convention (collision rule)

Rendered files carry the marker immediately after the frontmatter, before
any chunk backreference comments. The wording must NEVER contain the
substring `AUTO-GENERATED`: `src/project.py#_is_ve_generated_file` keys on
the legacy `AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY` header to delete
old init-rendered files, and the invariant tests
(`tests/test_plugin_commands.py::TestCommandInvariants::test_no_auto_generated_header`,
its agents twin) reject the substring wholesale.
`tests/test_plugin_render.py` requires the `GENERATED from
src/templates/plugin/...` marker in every rendered file and asserts the
collision rule.

## 6. Mechanical migration recipe (per command)

For each remaining `commands/<name>.md` (and later `agents/<name>.md`):

1. Create `src/templates/plugin/commands/<name>.md.jinja2` starting with the
   import line from section 3.
2. Replace the frontmatter with `{{ idioms.frontmatter("<name>",
   "<description>", [<allowed-tools entries as a list>]) }}` followed by one
   blank line. Copy name/description/tools verbatim from the committed file.
3. Add `{{ idioms.generated_marker(source_template) }}` on its own line,
   then the file's existing `<!-- Chunk: ... -->` backreference lines
   verbatim.
4. Replace the canonical preamble (if the file has the standard `## Context`
   + `## Runtime context` block):

   - No command-specific task bullet:

     ```jinja2
     {{ idioms.canonical_preamble() }}
     ```

   - With trailing command-specific bullets (compare chunk-create):

     ```jinja2
     {% call idioms.canonical_preamble() -%}
     - **If this is a task workspace** (...command-specific guidance...)
     {%- endcall %}
     ```

   Commands with nonstandard context blocks (compare ve-status) keep their
   own `## Context` heading and use `{{ idioms.probe("<label>",
   '<command>') }}` per line.
5. Replace literal `${CLAUDE_PLUGIN_ROOT}` references with
   `{{ idioms.plugin_root() }}`.
6. Keep the entire instruction body byte-verbatim. Watch for `{{`/`{%`/`{#`
   already present in command prose (several commands contain literal
   placeholder braces like `{prefix}_{current_name}` — single braces are
   safe; double braces must be wrapped in `{% raw %}...{% endraw %}`).
7. Run `uv run ve plugin render` and check `git diff commands/<name>.md`:
   the ONLY change must be the added marker line. Any other diff is a
   template bug (most commonly whitespace control around `{% call %}`).
8. Run `uv run pytest tests/test_plugin_render.py tests/test_plugin_commands.py`.
   The drift test parametrizes over the collection automatically — no test
   edits needed per migrated file.

## 7. Byte-stability rules learned from the pilots

- Jinja2 strips one trailing newline; `render_plugin_template` re-normalizes
  to exactly one. Author templates ending with a final newline.
- The idioms partial uses explicit whitespace control (`{%- ... -%}`) so
  macros are newline-neutral; do not switch the environment to
  `trim_blocks`/`lstrip_blocks` (it is the shared `template_system`
  environment — other collections depend on the defaults).
- In `{% call idioms.canonical_preamble() -%} ... {%- endcall %}`, the inner
  minus signs make the caller body whitespace-tight; the macro inserts the
  newline between the standard bullets and the caller content.
