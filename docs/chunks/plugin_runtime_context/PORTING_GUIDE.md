# Porting Guide: Runtime Context Detection for Plugin Commands

<!-- Chunk: docs/chunks/plugin_runtime_context - Runtime context-detection convention -->

This guide is the mechanical recipe for porting a command from
`src/templates/commands/<name>.md.jinja2` to a static plugin command at
`commands/<name>.md`. It was established by the `plugin_runtime_context`
chunk and is applied by `plugin_core_commands` and `plugin_orch_commands`
to the remaining 35 commands. The worked example is
`commands/chunk-create.md`, ported from
`src/templates/commands/chunk-create.md.jinja2` — read the pair side by
side when in doubt.

**Do not delete or modify the source templates.** They stay in place until
the `plugin_init_slimdown` chunk removes them.

## 1. The convention

Plugin command files are static markdown (DEC-010). Everything the template
system resolved at render time is resolved at execution time instead:

| Render-time mechanism | Runtime replacement |
|---|---|
| `{% if task_context %}` blocks | Detect `.ve-task.yaml` at the workspace root (the session cwd in a task workspace). Present if and only if this is a task (multi-repo) workspace — `ve task init` writes it. |
| `{{ external_artifact_repo }}` | The `external_artifact_repo` key inside `.ve-task.yaml`. |
| `{% for project in projects %}` | The `projects` list inside `.ve-task.yaml`. |
| `ve_config` injection (`load_ve_config`) | Read `.ve-config.yaml` at the project root. Known keys and defaults: `cluster_subsystem_threshold: 5`. A missing file means all defaults apply. |
| `partials/auto-generated-header.md.jinja2` | **Dropped.** Plugin files are the source, not render output. |
| `partials/common-tips.md.jinja2` | Folded into the standard preamble (the "installed CLI tool" tip). |

The detection signal is the *file*, not an environment variable or a flag:
the preamble's `!`-prefixed context lines print the file contents when
present, so the agent sees the same values the Jinja2 renderer used to
interpolate, and the runtime instructions branch on what those lines show.

## 2. The canonical preamble

Every ported command carries this preamble verbatim, immediately after the
chunk backreference comment. Only the chunk backreference and the
command-specific task-workspace guidance (see step 4 of the recipe) vary.

````markdown
## Context

- ve CLI: !`ve --help >/dev/null 2>&1 && echo "installed" || echo "(ve CLI not found)"`
- Task workspace: !`cat .ve-task.yaml 2>/dev/null || cat ../.ve-task.yaml 2>/dev/null || echo "(not a task workspace)"`
- Project config: !`cat .ve-config.yaml 2>/dev/null || echo "(no .ve-config.yaml — defaults apply)"`

## Runtime context

Interpret the context above before following the instructions:

- **ve CLI**: The `ve` command is an installed CLI tool, not a file in the
  repository. Do not search for it — run it directly via Bash. If the
  context shows "(ve CLI not found)", tell the operator that the
  vibe-engineer plugin requires the separately installed `ve` CLI, suggest
  `uv tool install vibe-engineer` (or `pip install vibe-engineer`), and
  stop.
- **Uninitialized project**: If `ve` is installed but commands fail because
  there is no `docs/chunks/` structure, tell the operator to run `ve init`
  in the project root, then stop.
- **Task workspace**: If the Task workspace context shows YAML (keys
  `external_artifact_repo` and `projects`) instead of "(not a task
  workspace)", you are in a multi-project task workspace. Artifacts
  (chunks, narratives, investigations) live in the external artifact repo
  named by `external_artifact_repo`; code changes happen in the
  participating `projects`. Command-specific task guidance appears below.
- **Project config**: `.ve-config.yaml` holds project configuration.
  Known keys: `cluster_subsystem_threshold` (default 5 — the cluster size
  at which to suggest subsystem documentation). When the context shows
  "(no .ve-config.yaml — defaults apply)", use the defaults.
````

Notes:

- The `!` lines execute when the slash command is invoked; their output is
  injected into the conversation. The `allowed-tools` frontmatter must
  pre-approve them (see step 1 of the recipe).
- The Task workspace line falls back to `../.ve-task.yaml` so an agent
  whose cwd is one level inside a task workspace (e.g., inside a
  participating project directory at the task root) still detects task
  context. Deeper nesting is out of scope: if both probes miss but you
  have other evidence of a task workspace (an `external.yaml` pointer,
  operator statement), check parent directories before concluding you are
  not in a task.
- `ve` has **no `--version` flag** — probe presence with `ve --help`.

## 3. Mechanical porting steps

For each `src/templates/commands/<name>.md.jinja2` → `commands/<name>.md`:

1. **Frontmatter**: copy `name` and `description` from the template
   frontmatter unchanged. Add `allowed-tools` listing, comma-separated:
   - the preamble probes (always): `Bash(ve --help:*)`, `Bash(cat:*)`
   - one `Bash(ve <subcommand>:*)` entry for each distinct `ve` invocation
     the command body instructs (e.g., `Bash(ve chunk create:*)`,
     `Bash(ve chunk list:*)`)

   Do not list write-capable invocations the body never uses.

2. **Drop the render machinery**: delete the
   `{% set source_template = ... %}` line and the
   `{% include "partials/auto-generated-header.md.jinja2" %}` include. Do
   not reproduce the AUTO-GENERATED header — plugin files are the source.

3. **Backreference + preamble**: immediately after the frontmatter, add an
   HTML-comment chunk backreference for the chunk doing the porting, e.g.:

   ```markdown
   <!-- Chunk: docs/chunks/plugin_core_commands - Static plugin port of <name> -->
   ```

   Then paste the canonical preamble from section 2. The preamble replaces
   the template's `## Tips` section and its
   `{% include "partials/common-tips.md.jinja2" %}` (that tip is already in
   the Runtime context section).

4. **Rewrite `{% if task_context %}` blocks** (guidance-only blocks): move
   the block's content under a heading inside the Runtime context section
   (or inline where the template had it, if it is mid-instruction),
   introduced by the condition in prose:

   > **If this is a task workspace** (the Task workspace context above
   > shows `.ve-task.yaml` contents): ...

   Then substitute interpolations:
   - `{{ external_artifact_repo }}` → "the external artifact repo named by
     `external_artifact_repo` in `.ve-task.yaml`"
   - `{% for project in projects %} - {{ project }} {% endfor %}` → "the
     participating projects listed under `projects` in `.ve-task.yaml`"

   Never drop the block's guidance — preserving it as a runtime conditional
   is the point of the convention.

5. **Rewrite `{% if task_context %} ... {% else %} ... {% endif %}` pairs**
   (dual-variant blocks, e.g., code-reference formats in chunk-complete):
   keep **both** variants, each introduced by its condition:

   > **In a task workspace** (`.ve-task.yaml` present): use the
   > project-qualified format `{project}::{file_path}#{symbol_path}` ...
   >
   > **In a single project** (no `.ve-task.yaml`): use the format
   > `{file_path}#{symbol_path}` ...

6. **Keep the command body verbatim**: the numbered instructions, the
   `$ARGUMENTS` placeholder, and all embedded examples carry over without
   behavioral changes. The port changes *how context is resolved*, not what
   the command does. Commands reference bare `ve ...` (consuming projects
   have ve installed) — never `uv run ve`.

7. **Verify**: no Jinja2 syntax survives —

   ```bash
   grep -nE '\{%|\{\{|\{#' commands/<name>.md   # must match nothing
   ```

   and run `uv run pytest tests/test_plugin_commands.py`, whose generic
   invariants (frontmatter, no Jinja2, no AUTO-GENERATED header)
   automatically cover every file in `commands/`.

## 4. Worked example

Template (`src/templates/commands/chunk-create.md.jinja2`):

```jinja2
{% if task_context %}

**Task Context:** This command creates artifacts in the external artifact repo
(`{{ external_artifact_repo }}`). The chunk GOAL.md and PLAN.md will be created
there. When implementing, code changes happen in participating projects, and
external.yaml references allow projects to discover the external chunk.
{% endif %}
```

Ported form (in `commands/chunk-create.md`, inside the Runtime context
section):

```markdown
- **If this is a task workspace** (the Task workspace context above shows
  `.ve-task.yaml` contents): this command creates artifacts in the external
  artifact repo named by `external_artifact_repo` in `.ve-task.yaml`. The
  chunk GOAL.md and PLAN.md will be created there. When implementing, code
  changes happen in the participating projects listed under `projects`, and
  external.yaml references allow projects to discover the external chunk.
```

Read `commands/chunk-create.md` in full for the complete shape: frontmatter
with `allowed-tools`, backreference, canonical preamble, and the untouched
instruction body.
