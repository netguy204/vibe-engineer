---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/project.py
- src/task_init.py
- src/template_system.py
- src/templates/claude/AGENTS.md.jinja2
- src/templates/claude/CLAUDE.md.jinja2
- src/templates/commands/
- tests/test_project.py
- tests/test_init.py
- tests/test_task_init.py
- tests/test_steward_skills.py
- tests/test_chunk_review_skill.py
- tests/test_template_system.py
- tests/test_orchestrator_feedback_injection.py
code_references:
- ref: src/project.py#Project::init
  implements: "Slimmed init pipeline: trunk docs, AGENTS.md, artifact directories, reviewers baseline, gitignore — no skill rendering or command symlinks"
- ref: src/project.py#_is_ve_generated_file
  implements: "Kept VE-generated-file detector for plugin_legacy_migration's legacy-layout cleanup"
- ref: src/task_init.py#TaskInit::execute
  implements: "Slimmed task init: writes .ve-task.yaml and task AGENTS.md only, no skill rendering"
- ref: src/template_system.py#render_to_directory
  implements: "Collection rendering without the removed skill_layout (agentskills.io) output mode"
- ref: src/templates/claude/AGENTS.md.jinja2
  implements: "Managed block reduced to trunk-doc pointers, chunk conventions, and the Claude Code plugin pointer for commands"
- ref: src/templates/claude/CLAUDE.md.jinja2
  implements: "Parallel slimmed managed-block template kept content-identical to AGENTS.md.jinja2"
- ref: tests/test_project.py#TestProjectInit::test_init_creates_no_agents_skills_directory
  implements: "Negative coverage: fresh init creates no .agents/ directory"
- ref: tests/test_project.py#TestProjectInit::test_init_creates_no_claude_commands_directory
  implements: "Negative coverage: fresh init creates no .claude/ directory"
- ref: tests/test_project.py#TestIsVeGeneratedFile
  implements: "Direct unit coverage for the kept _is_ve_generated_file helper"
- ref: tests/test_task_init.py#TestTaskInitNoSkills
  implements: "Negative coverage: task init renders no skills or command symlinks"
narrative: claude_plugin_port
investigation: null
subsystems: []
friction_entries: []
depends_on:
- plugin_core_commands
- plugin_orch_commands
created_after:
- orch_max_turns_config
- watch_handshake_timeout_retry
---
# Chunk Goal

## Minor Goal

`ve init` scaffolds only project-owned artifacts: trunk docs (docs/trunk/*,
overwrite=False), artifact directories (docs/chunks/, docs/narratives/), the
reviewers baseline, and .gitignore hygiene. It renders no command skills,
creates no `.agents/skills/` layout and no `.claude/commands/` symlinks, and
the AGENTS.md managed block (between `<!-- VE:MANAGED:START/END -->`) contains
only project-documentation pointers (trunk docs, artifact conventions, a
pointer to the plugin) — command documentation travels with the plugin. The
`src/templates/commands/` collection no longer exists.

## Context

- `Project.init()` (src/project.py) has no skills phase: there is no
  `_init_skills()` and no .claude/commands symlink machinery, and the
  src/templates/commands/ collection (with its partials) does not exist.
  `_is_ve_generated_file()` (src/project.py) is retained because
  plugin_legacy_migration's cleanup uses it to identify VE-generated files in
  legacy layouts.
- The managed content in src/templates/claude/AGENTS.md.jinja2 (and its
  parallel CLAUDE.md.jinja2) contains trunk-doc pointers, chunk conventions,
  brief artifact pointers, and a section directing agents/users to the Claude
  Code plugin for commands — no per-command documentation.
- The rest of the init pipeline is unchanged: `_init_trunk()`,
  `_init_narratives()`, `_init_chunks()`, `_init_reviewers()`,
  `_init_gitignore()`, and the magic-marker machinery (parse_markers and
  friends in src/project.py) all remain.
- `ve task init` (src/task_init.py) is equivalently slim: it writes
  .ve-task.yaml and the task-level AGENTS.md (with CLAUDE.md symlink) and
  renders no skills into task roots.
- Tests cover the slimmed behavior: fresh init creates no .agents/ or
  .claude/ directories, and the former skill-rendering/symlink tests are
  removed or repointed at the static plugin commands.
- This chunk depends on both command-port chunks: the render channel was
  removed only after the plugin carried all 36 commands, so no users were
  stranded.

## Success Criteria

- A fresh `ve init` produces no .agents/skills/ directory, no
  .claude/commands/ entries, and an AGENTS.md whose managed block contains no
  per-command documentation.
- src/templates/commands/ is deleted and the template system has no remaining
  references to the collection.
- `ve task init` is equivalently slimmed.
- The test suite passes with rendering/symlink tests updated or removed.

## Rejected Ideas

### Keep dual-channel rendering for non-Claude-Code agents

Continue rendering .agents/skills/ (the agent-agnostic agentskills.io layout)
alongside the plugin.

Rejected because: the operator chose full replacement. Maintaining two
distribution channels from one source re-creates the update-lag and
repo-pollution problems the narrative exists to remove. If multi-agent support
becomes a requirement, a render channel can be reintroduced from the plugin
sources.
