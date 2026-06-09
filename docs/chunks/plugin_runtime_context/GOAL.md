---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- commands/chunk-create.md
- docs/chunks/plugin_runtime_context/PORTING_GUIDE.md
- tests/test_plugin_commands.py
code_references:
- ref: commands/chunk-create.md
  implements: "Pilot port: chunk-create as a static plugin command using the runtime context-detection preamble"
- ref: docs/chunks/plugin_runtime_context/PORTING_GUIDE.md
  implements: "The documented convention and mechanical porting recipe applied by plugin_core_commands and plugin_orch_commands"
- ref: tests/test_plugin_commands.py#TestCommandInvariants
  implements: "Generic invariants over every plugin command: valid frontmatter, no Jinja2 syntax, no auto-generated header"
- ref: tests/test_plugin_commands.py#TestChunkCreateCommand
  implements: "Pilot assertions: runtime detection references, preserved task-context guidance, $ARGUMENTS, backreference"
- ref: tests/test_plugin_commands.py#TestRuntimeDetection
  implements: "Behavioral check that the preamble's shell lines distinguish plain project, configured project, and task workspace"
narrative: claude_plugin_port
investigation: null
subsystems: []
friction_entries: []
depends_on:
- plugin_scaffold
created_after:
- orch_max_turns_config
- watch_handshake_timeout_retry
---

# Chunk Goal

## Minor Goal

Plugin command and skill files are static markdown; behavior that the template
system previously resolved at render time is resolved at execution time by a
documented runtime context-detection convention. Commands instruct the agent
to (a) detect task (multi-repo) context by checking for `.ve-task.yaml` at the
workspace root, replacing the `{% if task_context %}` render variants, and
(b) read `.ve-config.yaml` for project configuration such as
`cluster_subsystem_threshold`, replacing render-time `ve_config` injection.
The plugin's chunk-create command (commands/chunk-create.md) is the
end-to-end pilot demonstrating the convention; the porting guide in this
chunk directory (PORTING_GUIDE.md) makes it mechanically applicable to the
remaining commands.

## Context

- Render-time machinery this convention replaces (still present until
  plugin_init_slimdown removes it): src/template_system.py —
  `render_template()` and `load_ve_config()`; `TaskContext` carries
  `external_artifact_repo`, `projects`, and `task_context=True`
  (src/task_init.py).
- Source templates: src/templates/commands/*.md.jinja2 (36 files) with
  `{% if task_context %}` blocks (e.g., chunk-create.md.jinja2) and partials
  `partials/auto-generated-header.md.jinja2` and
  `partials/common-tips.md.jinja2`.
- `ve task init` writes `.ve-task.yaml` into the task root — that file is the
  runtime detection signal for task context. `.ve-config.yaml` lives at the
  project root.
- The convention is mechanically applicable: chunks plugin_core_commands and
  plugin_orch_commands mass-apply it to the remaining 35 commands via the
  canonical preamble and recipe in PORTING_GUIDE.md.
- The auto-generated header ("AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY /
  Run ve init to regenerate") is obsolete in plugin files — plugin files are
  the source, not render output. Ported commands omit it.

## Success Criteria

- A documented convention states how plugin commands detect task context and
  read project config at runtime, written so later chunks can apply it
  mechanically to the remaining commands.
- The plugin's chunk-create command contains no Jinja2 syntax and behaves
  correctly in three situations: a plain project (no .ve-task.yaml, no
  .ve-config.yaml), a project with .ve-config.yaml, and a task workspace with
  .ve-task.yaml.
- The task-context guidance from chunk-create.md.jinja2's
  `{% if task_context %}` blocks is preserved as runtime conditional
  instructions ("if .ve-task.yaml exists at the workspace root, ...") rather
  than dropped.
