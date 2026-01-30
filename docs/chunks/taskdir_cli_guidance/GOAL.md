---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/task/CLAUDE.md.jinja2
- src/task_utils.py
- src/ve.py
- tests/test_task_cli_context.py
code_references:
  - ref: src/templates/task/CLAUDE.md.jinja2
    implements: "Task CLAUDE.md template section explaining artifact creation context"
  - ref: src/task_utils.py#TaskProjectContext
    implements: "Dataclass holding task/project context detection results"
  - ref: src/task_utils.py#check_task_project_context
    implements: "Core detection logic for identifying when running from a task's project"
  - ref: src/ve.py#warn_task_project_context
    implements: "Shared warning helper for CLI artifact commands"
  - ref: tests/test_task_cli_context.py
    implements: "Tests for CLI context warning behavior"
narrative: null
investigation: null
subsystems:
- subsystem_id: template_system
  relationship: uses
friction_entries: []
bug_type: null
created_after:
- template_lang_agnostic
---

# Chunk Goal

## Minor Goal

Prevent agents from accidentally creating project-level artifacts when operating in a task context.

**Problem observed:** An agent working in a task context (multi-repo workflow) was asked to create chunks for work uncovered during an investigation. Instead of running `ve chunk create` from the task directory (which creates cross-repo chunks), the agent `cd`'d into individual participating projects and ran the command there—creating project-level chunks instead of task-level chunks.

This happens because the agent loses task-level perspective when it moves into a project directory. The agent made reasonable choices about which projects to enter, but the result was wrong: cross-repo investigation work got fragmented into local project chunks.

**Proposed solutions:**

1. **Task-level CLAUDE.md guidance**: Add a section to the task CLAUDE.md template instructing agents to run all VE CLI artifact commands from the task directory, not from individual project directories. This guidance should explain why: running from task context creates cross-repo artifacts with proper external.yaml pointers, while running from a project creates local artifacts.

2. **CLI warning for misplaced commands**: When artifact commands (`ve chunk create`, `ve narrative create`, `ve investigation create`, etc.) are run from inside a project directory that is part of a task, emit a warning suggesting the command may be running in the wrong context. The CLI can detect this by checking if the current directory is within a project listed in a parent `.ve-task.yaml`.

## Success Criteria

1. **Task CLAUDE.md template includes CLI context guidance**:
   - Clear instruction that artifact creation commands should be run from the task directory
   - Explains the consequence: task-level vs project-level artifact creation
   - Located in the task-specific section of the template (not the base CLAUDE.md)

2. **CLI emits contextual warnings**:
   - When `ve chunk create` is run from a directory that is inside a project participating in a task, warn: "You are running this command from within project X which is part of task Y. To create a cross-repo chunk, run from the task directory instead."
   - Warning is non-blocking (command still executes) so intentional project-level chunks remain possible
   - Same pattern applies to other artifact creation commands: `ve narrative create`, `ve investigation create`, `ve subsystem discover`

3. **Detection mechanism**:
   - Walk up from cwd looking for `.ve-task.yaml`
   - If found, check if cwd is within one of the task's project directories
   - If so, emit the warning before proceeding

4. **Tests cover the warning behavior**:
   - Test that warning appears when running chunk create from project-in-task
   - Test that warning does NOT appear when running from task root
   - Test that warning does NOT appear for standalone projects (no task context)