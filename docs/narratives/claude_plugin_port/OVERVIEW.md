---
status: ACTIVE
advances_trunk_goal: "Required Properties: retrofit-ability and partial-adoption — 'It must be possible to retrofit a legacy project into the workflow' and 'The tooling that supports this workflow must remain effective even if not every engineer working in the project uses the workflow.'"
proposed_chunks:
  - prompt: >-
      Scaffold the Claude Code plugin in this repository: create
      .claude-plugin/plugin.json and .claude-plugin/marketplace.json, establish
      the plugin directory layout (commands/, skills/, agents/, hooks/), document
      the install path (/plugin marketplace add + /plugin install), and record
      the distribution decision as an ADR in docs/trunk/DECISIONS.md. Include one
      working pilot command to validate end-to-end installation.
    depends_on: []
    chunk_directory: plugin_scaffold
  - prompt: >-
      Establish the runtime context-detection convention that replaces Jinja2
      render-time conditionals in command templates. Plugin files are static, so
      the {% if task_context %} blocks and ve_config injection must become
      runtime instructions: commands direct the agent to detect .ve-task.yaml
      (task context) and read .ve-config.yaml (project config) when present.
      Define the shared convention (a reusable preamble or skill reference) and
      convert one representative command (chunk-create) end-to-end as the pilot.
    depends_on: [0]
    chunk_directory: plugin_runtime_context
  - prompt: >-
      Port the core workflow commands to static plugin commands and skills using
      the runtime context-detection convention: chunk-create, chunk-plan,
      chunk-implement, chunk-complete, chunk-execute, chunk-review, chunk-commit,
      chunk-rebase, chunk-demote, chunk-update-references,
      chunks-resolve-references, cluster-rename, narrative-create,
      narrative-compact, narrative-execute, investigation-create,
      subsystem-discover, discover-subsystems, decision-create, friction-log,
      validate-fix. Each ships as a slash command plus a skill description so
      the model can invoke it proactively.
    depends_on: [1]
    chunk_directory: plugin_core_commands
  - prompt: >-
      Port the orchestrator, steward, swarm, entity, and migration commands to
      static plugin commands and skills: orchestrator-inject,
      orchestrator-monitor, orchestrator-investigate, orchestrator-submit-future,
      steward-setup, steward-watch, steward-send, steward-changelog,
      swarm-monitor, swarm-request-response, entity-startup, entity-shutdown,
      entity-episodic, audit-intent, migrate-managed-claude-md.
    depends_on: [1]
    chunk_directory: plugin_orch_commands
  - prompt: >-
      Add plugin hooks: a SessionStart hook that verifies the ve CLI is
      installed, checks plugin/CLI version compatibility (warning on mismatch),
      and surfaces the currently IMPLEMENTING chunk so sessions open with
      workflow context. Define the version-compatibility policy between the
      plugin and the vibe-engineer Python package.
    depends_on: [0]
    chunk_directory: plugin_session_hooks
  - prompt: >-
      Define plugin subagents for the parallelizable workflow roles that
      commands currently describe inline — e.g., a chunk-executor agent used by
      narrative-execute, and an intent-auditor agent used by audit-intent.
      Identify which inline agent prompts in the ported commands deserve
      promotion to named plugin agents, and wire the commands to reference them.
    depends_on: [2, 3]
    chunk_directory: plugin_subagents
  - prompt: >-
      Slim down ve init to project scaffolding only: remove the _init_skills
      rendering, the .agents/skills layout, and the .claude/commands symlink
      machinery; delete the src/templates/commands collection; reduce the
      AGENTS.md managed block to project-documentation pointers (trunk docs,
      chunk conventions) since command documentation now travels with the
      plugin. Trunk doc scaffolding, artifact directories, reviewers baseline,
      and .gitignore handling remain.
    depends_on: [2, 3]
    chunk_directory: plugin_init_slimdown
  - prompt: >-
      Build the migration path for existing projects: re-running ve init on a
      project with the legacy layout should clean up .agents/skills,
      .claude/commands symlinks, and the old AGENTS.md managed content, then
      point the operator at the plugin install. Update README and trunk docs
      (SPEC.md, ORCHESTRATOR.md) to describe plugin-based distribution, and
      document the upgrade story: plugin updates replace the re-run-ve-init
      update channel for commands.
    depends_on: [6]
    chunk_directory: plugin_legacy_migration
created_after: ["intent_ownership"]
---

## Advances Trunk Goal

**Required Properties** — specifically the adoption clauses: *"It must be
possible to retrofit a legacy project into the workflow"* and *"The tooling
that supports this workflow must remain effective even if not every engineer
working in the project uses the workflow."*

Distribution-by-rendering (`ve init` writing 36 command files, symlinks, and a
managed AGENTS.md block into every target repo) is the single largest friction
point for retrofitting a project and the largest per-engineer cost of partial
adoption: every engineer's checkout carries the rendered artifacts, and every
ve upgrade requires a re-init commit in every consuming repo. Native plugin
distribution makes adoption a per-user install and updates a plugin-manager
concern, leaving only genuinely project-owned documentation in the repo.

## Driving Ambition

vibe-engineer currently distributes itself into target projects by rendering
Jinja2 templates: `ve init` writes 36 command skills into `.agents/skills/`,
creates `.claude/commands/` symlinks, and maintains a magic-marker-managed
block in AGENTS.md. This made sense before Claude Code had a plugin system,
but it has real costs:

- **Update lag**: projects only get new/fixed commands when someone re-runs
  `ve init` and commits the churn. Command updates are entangled with repo
  history.
- **Repo pollution**: ~40 rendered files plus symlinks live in every consuming
  repo, none of which are project-specific content.
- **Render-time conditionals**: templates branch on `task_context` and
  `ve_config` at render time, so the same logical command exists in multiple
  rendered variants across repos.

The ambition is to recast vibe-engineer as a proper Claude Code plugin, hosted
in this repository with a marketplace manifest. The plugin becomes the sole
distribution channel for commands, skills, hooks, and subagents. The `ve`
Python CLI remains the workflow engine (installed separately via uv/pip), and
`ve init` shrinks to what is genuinely per-project: trunk documentation
scaffolding, artifact directories, and .gitignore hygiene.

Success looks like: a new user adds the marketplace, installs the plugin, runs
a slimmed `ve init` in their project, and has the full workflow — commands,
proactive skills, session-start chunk context, named subagents — without a
single rendered command file in their repo. Existing projects migrate by
re-running `ve init`, which cleans up the legacy layout.

**Accepted trade-off**: full replacement ties command distribution to Claude
Code's plugin system. The `.agents/skills/` layout was agent-agnostic
(agentskills.io); dropping it narrows non-Claude-Code agent support to the
AGENTS.md pointer file. The operator accepted this; if multi-agent support
becomes a requirement later, a render channel can be reintroduced from the
plugin sources.

**Key technical constraint discovered during refinement**: plugin command
files are static, but current templates render conditionally (`{% if
task_context %}` blocks, `ve_config` injection). The port therefore needs a
runtime context-detection convention — commands instruct the agent to detect
`.ve-task.yaml` and read `.ve-config.yaml` at execution time — established
once (chunk 1) before mass-porting commands (chunks 2–3).

## Chunks

1. **plugin scaffold** — `.claude-plugin/plugin.json`, `marketplace.json`,
   directory layout, install docs, ADR, and one pilot command proving the
   install path. _(no dependencies)_
2. **runtime context convention** — replace render-time Jinja2 conditionals
   with runtime detection of `.ve-task.yaml` / `.ve-config.yaml`; convert
   chunk-create as the pilot. _(depends on 1)_
3. **core workflow command port** — chunk-*, narrative-*, investigation,
   subsystem, decision, friction, validate-fix as static commands + skills.
   _(depends on 2)_
4. **orchestrator/steward/entity command port** — orchestrator-*, steward-*,
   swarm-*, entity-*, audit-intent, migrate-managed-claude-md. _(depends on 2)_
5. **hooks** — SessionStart: ve CLI presence + version-compatibility check,
   surface the current IMPLEMENTING chunk. _(depends on 1)_
6. **subagents** — promote inline agent prompts (chunk-executor,
   intent-auditor, …) to named plugin agents. _(depends on 3, 4)_
7. **ve init slim-down** — remove skill rendering, symlink machinery, and the
   commands template collection; shrink the AGENTS.md managed block.
   _(depends on 3, 4)_
8. **migration + docs** — legacy-layout cleanup on re-init, README/trunk doc
   updates, plugin-based upgrade story. _(depends on 7)_

## Completion Criteria

When this narrative is complete:

- A new user can adopt the workflow with `/plugin marketplace add` +
  `/plugin install` + a slimmed `ve init`, and no rendered command files,
  skills, or symlinks appear in their repository.
- All 36 workflow commands work from the plugin, including in task (multi-repo)
  contexts, via runtime context detection rather than render-time variants.
- Sessions in a ve project open with the current chunk surfaced and a warning
  if the installed `ve` CLI is missing or version-incompatible with the plugin.
- An existing project on the legacy layout migrates by re-running `ve init`,
  which removes `.agents/skills/`, `.claude/commands/` symlinks, and legacy
  managed content.
- Command and skill updates reach users through plugin updates; re-running
  `ve init` is no longer part of the upgrade story for commands.
