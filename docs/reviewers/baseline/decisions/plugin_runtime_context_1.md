---
decision: APPROVE
summary: "All three success criteria satisfied - the runtime context-detection convention is documented as a mechanically-applicable porting guide with a canonical preamble, chunk-create is ported with no Jinja2 syntax and behaviorally-tested detection of all three runtime situations, and the task-context guidance survives as a runtime conditional."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: A documented convention states how plugin commands detect task context and read project config at runtime, written so later chunks can apply it mechanically to the remaining commands

- **Status**: satisfied
- **Evidence**: docs/chunks/plugin_runtime_context/PORTING_GUIDE.md - section 1 maps each render-time mechanism (`{% if task_context %}`, `{{ external_artifact_repo }}`, `{% for project in projects %}`, `ve_config` injection, both partials) to its runtime replacement; section 2 gives the canonical preamble verbatim (Context `!` lines with fallback chains plus the Runtime context instruction section); section 3 is a 7-step mechanical recipe covering frontmatter/allowed-tools, guidance-only blocks, dual-variant `{% if %}/{% else %}` blocks, and a final no-Jinja2 grep check; section 4 shows the template block and its ported form side by side. The wave-3 chunks' GOALs reference "the plugin_runtime_context convention and porting guide" and this file lives in the chunk directory they depend on.

### Criterion 2: The plugin's chunk-create command contains no Jinja2 syntax and behaves correctly in three situations: a plain project, a project with .ve-config.yaml, and a task workspace with .ve-task.yaml

- **Status**: satisfied
- **Evidence**: commands/chunk-create.md - `grep -E '\{%|\{\{|\{#'` matches nothing, enforced by tests/test_plugin_commands.py#TestCommandInvariants::test_no_jinja2_syntax (parameterized over every commands/*.md, so wave-3 ports inherit the check). The three situations are exercised behaviorally by TestRuntimeDetection, which extracts the actual `!` shell lines and runs them in three temp directories: a plain project yields the "(not a task workspace)"/"defaults apply" fallbacks, a project with .ve-config.yaml surfaces `cluster_subsystem_threshold: 3`, and a task workspace surfaces `external_artifact_repo` and the `projects` list. All 16 tests pass; the full suite shows only the 32 pre-existing baseline failures (subsystem test files + orchestrator daemon test), none attributable to this chunk.

### Criterion 3: The task-context guidance from chunk-create.md.jinja2's {% if task_context %} blocks is preserved as runtime conditional instructions rather than dropped

- **Status**: satisfied
- **Evidence**: commands/chunk-create.md:40-45 - the template's task-context block (external artifact repo routing for GOAL.md/PLAN.md, code changes in participating projects, external.yaml discovery) appears under "**If this is a task workspace** (the Task workspace context above shows `.ve-task.yaml` contents)", with `{{ external_artifact_repo }}` rewritten as "the external artifact repo named by `external_artifact_repo` in `.ve-task.yaml`". Enforced by tests/test_plugin_commands.py#TestChunkCreateCommand::test_preserves_task_context_guidance. The instruction body (steps 1-10, $ARGUMENTS, the intent-judgment gate) carries over verbatim from the template per the guide's step 6.
