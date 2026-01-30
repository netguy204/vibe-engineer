---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/task_init.py
  - tests/test_task_init.py
  - src/templates/task/CLAUDE.md.jinja2
  - src/templates/commands/chunk-create.md.jinja2
  - src/templates/commands/chunk-plan.md.jinja2
  - src/templates/commands/chunk-implement.md.jinja2
  - src/templates/commands/chunk-complete.md.jinja2
  - src/templates/commands/narrative-create.md.jinja2
  - src/templates/commands/subsystem-discover.md.jinja2
  - src/templates/commands/investigation-create.md.jinja2
  - docs/trunk/SPEC.md
code_references:
  - ref: src/template_system.py#TaskContext
    implements: "Task-level context dataclass for template rendering with external_artifact_repo, projects, and task_context flag"
  - ref: src/task_init.py#TaskInit::_render_claude_md
    implements: "Renders task CLAUDE.md template to task root"
  - ref: src/task_init.py#TaskInit::_render_commands
    implements: "Renders command templates to .claude/commands/ with task context"
  - ref: src/task_init.py#TaskInitResult
    implements: "Extended result dataclass with created_files tracking"
  - ref: src/project.py#Project::_init_commands
    implements: "Project commands rendered with task_context=False for proper conditional block resolution"
  - ref: src/templates/task/CLAUDE.md.jinja2
    implements: "Task-specific CLAUDE.md template with project list and orientation"
  - ref: src/templates/commands/chunk-create.md.jinja2
    implements: "Chunk create command with task context conditional block"
  - ref: src/templates/commands/chunk-implement.md.jinja2
    implements: "Chunk implement command with task context conditional block"
  - ref: src/templates/commands/chunk-plan.md.jinja2
    implements: "Chunk plan command with task context conditional block"
  - ref: src/templates/commands/chunk-complete.md.jinja2
    implements: "Chunk complete command with task context conditional block"
  - ref: src/templates/commands/narrative-create.md.jinja2
    implements: "Narrative create command template (no task context block)"
  - ref: src/templates/commands/subsystem-discover.md.jinja2
    implements: "Subsystem discover command with task context conditional block"
  - ref: src/templates/commands/investigation-create.md.jinja2
    implements: "Investigation create command with task context conditional block"
  - ref: tests/test_task_init.py#TestTaskInitClaudeMd
    implements: "Tests for CLAUDE.md generation in task init"
  - ref: tests/test_task_init.py#TestTaskInitCommands
    implements: "Tests for command template rendering in task init"
  - ref: tests/test_task_init.py#TestTaskInitCreatedFiles
    implements: "Tests for created_files tracking in TaskInitResult"
  - ref: tests/test_template_system.py#TestTaskContext
    implements: "Tests for TaskContext dataclass"
  - ref: tests/test_template_system.py#TestConditionalBlocks
    implements: "Tests for task_context conditional blocks in templates"
narrative: null
subsystems:
  - subsystem_id: template_system
    relationship: uses
created_after: ["task_aware_investigations", "task_aware_subsystem_cmds"]
investigation: docs/investigations/task_agent_experience
---

# Chunk Goal

## Minor Goal

Enhance `ve task init` to generate Claude Code scaffolding files alongside `.ve-task.yaml`, providing agents with immediate orientation when working in task contexts.

Currently, task directories only receive a `.ve-task.yaml` file, leaving agents without the CLAUDE.md and `.claude/commands/` scaffolding they need to understand the multi-project context and access slash commands. This chunk adds:

1. **CLAUDE.md generation**: A lean (~30 lines) template populated with the task's external repo and project list, providing essential orientation without duplicating workflow details that live in slash commands.

2. **`.claude/commands/` rendering**: Render command Jinja2 templates from `src/templates/commands/` to the task root's `.claude/commands/` with task-aware context. Commands contain conditional Jinja2 blocks (`{% if task_context %}...{% endif %}`) that explain task-specific behavior (e.g., "creates in external repo" vs "creates in this project").

3. **Context-aware command templates**: Update existing command files to include conditional content for task vs project contexts, so agents understand where artifacts will be created and how cross-project workflows differ.

This enables the "same agent experience everywhere" vision—agents in task contexts have the same orientation and command access as agents in project contexts, with guidance tailored to their current context.

## Success Criteria

1. **CLAUDE.md generated**: Running `ve task init --external org/repo --project org/project-a --project org/project-b` creates a `CLAUDE.md` file in the task directory with:
   - External artifact repo reference populated from `--external`
   - Project list populated from `--project` arguments
   - Essential orientation content (~30 lines) rendered from new `src/templates/task/CLAUDE.md.jinja2`

2. **`.claude/commands/` rendered**: Command templates from `src/templates/commands/` are rendered to the task root with task context:
   - Template variables: `task_context=True`, `external_artifact_repo`, `projects`
   - Conditional blocks (`{% if task_context %}...{% else %}...{% endif %}`) render task-specific content
   - All command templates are rendered to task root's `.claude/commands/`

3. **Command templates updated**: Existing command files include conditional content:
   - `/chunk-create`: Explains artifact creation in external repo with external.yaml references
   - `/chunk-implement`: Notes implementation spans participating projects
   - Other artifact commands: Similar context-aware guidance
   - Project context (no task_context): Commands work as before

4. **Existing project .claude/commands/ regenerated**: After adding conditional blocks to command templates, regenerate the project's `.claude/commands/` with `task_context=False` to maintain current behavior for project contexts

5. **Idempotent**: Running `ve task init` when scaffolding already exists fails with appropriate error (existing behavior for `.ve-task.yaml` already handles this)

6. **Tests pass**: Unit tests cover CLAUDE.md generation, command template rendering, and conditional block processing

