

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

`ve init` and `ve task init` currently distribute agent-facing commands by
rendering the `src/templates/commands/` Jinja2 collection into
`.agents/skills/` and symlinking `.claude/commands/`. Per DEC-010 the Claude
Code plugin (repo-root `commands/`, ported in plugin_core_commands and
plugin_orch_commands) is now the sole command distribution channel, so this
chunk removes the render channel entirely:

1. **Surgical removal in `Project.init()`** — drop `_init_skills()` and its
   call site; everything else in the init pipeline (`_init_trunk`,
   `_init_agents_md`, `_init_narratives`, `_init_chunks`, `_init_reviewers`,
   `_init_gitignore`) is untouched. `_is_ve_generated_file()` and the magic
   marker machinery (`MARKER_START`/`MARKER_END`, `MarkerParseResult`,
   `parse_markers`) are explicitly preserved — plugin_legacy_migration needs
   them for cleanup of already-initialized projects.
2. **Equivalent removal in `TaskInit`** — drop `_render_skills()` and its call
   site; `.ve-task.yaml` and `_render_agents_md()` remain.
3. **Delete the `src/templates/commands/` collection** (36 command templates +
   `partials/`). With both render call sites gone, the `skill_layout`
   parameter of `render_to_directory()` in src/template_system.py is dead
   code; remove it so the template system carries no residue of the skills
   layout.
4. **Shrink the AGENTS.md managed block** in
   `src/templates/claude/AGENTS.md.jinja2` (and its parallel
   `CLAUDE.md.jinja2`) to: trunk-doc pointers, chunk conventions (lifecycle,
   naming, frontmatter references), brief extended-artifact and
   code-backreference pointers, the artifact-creation-via-CLI rule, and a
   "Commands" section pointing at the Claude Code plugin
   (`/plugin marketplace add netguy204/vibe-engineer` +
   `/plugin install vibe-engineer`). All per-command documentation (Available
   Commands list, Steward section, cross-project messaging, orchestrator slash
   command list, Learning Philosophy) is removed — that content travels with
   the plugin now.
5. **Update tests** that assert the old behavior; add assertions that a fresh
   init produces *no* `.agents/skills/` and *no* `.claude/commands/`.

No new architectural decision is needed: DEC-010 (plugin-based distribution
replaces render-based distribution) already covers this change; this chunk is
the "remove the old channel" half of that decision.

Per docs/trunk/TESTING_PHILOSOPHY.md, tests exercise the public behavior
(`Project.init()` results, `ve init` CLI output, `TaskInit.execute()` results,
template rendering) rather than internals.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the subsystem
  and shrinks its surface — the `commands` collection is deleted and the
  `skill_layout` parameter is removed from `render_to_directory()`. The
  collection-based rendering model itself is unchanged (trunk, reviewers,
  claude, task, chunk, etc. collections remain). The subsystem OVERVIEW
  mentions of the commands collection are legacy-doc cleanup belonging to
  plugin_legacy_migration; if the OVERVIEW lists the commands collection
  explicitly, note it as a known deviation rather than rewriting docs here.
- **docs/subsystems/cross_repo_operations** (DOCUMENTED): `ve task init`
  belongs to this subsystem; the change removes its skill-rendering step but
  preserves `.ve-task.yaml` and the task AGENTS.md, so the subsystem's
  documented contract for task scaffolding shrinks consistently with the
  project-level change.
- **docs/subsystems/orchestrator** (discovered coupling, out of scope):
  `AgentRunner.get_skill_path()` (src/orchestrator/agent.py) loads phase
  prompts from `.agents/skills/<name>/SKILL.md` at runtime. Existing projects
  (including this repo) still have that layout, so nothing breaks today, but
  once plugin_legacy_migration removes legacy layouts the orchestrator needs a
  new prompt source. This is recorded under Risks as a handoff note; changing
  the orchestrator is outside this chunk's goal.

## Sequence

### Step 1: Remove `_init_skills()` from `Project.init()`

In `src/project.py`:
- Delete the `_init_skills()` method (lines ~210–294) including the
  `.claude/commands/` symlink creation, VE-generated-file migration, and
  stale-symlink cleanup logic.
- Remove `self._init_skills(),` from the `init()` pipeline list and update the
  `init()` docstring ("Creates trunk documents, AGENTS.md, artifact
  directories, and baseline reviewer").
- KEEP: `_is_ve_generated_file()` (plugin_legacy_migration dependency — leave
  its backreference comment in place), `MARKER_START`/`MARKER_END`,
  `MarkerParseResult`, `parse_markers()`, `_init_agents_md()` (including the
  CLAUDE.md→AGENTS.md symlink behavior), and all other `_init_*` methods.

### Step 2: Remove `_render_skills()` from `TaskInit`

In `src/task_init.py`:
- Delete the `_render_skills()` method and its call in `execute()`.
- `execute()` still writes `.ve-task.yaml` and calls `_render_agents_md()`.
- Drop the now-unused `render_to_directory` import.

### Step 3: Delete the commands template collection and `skill_layout`

- `git rm -r src/templates/commands/` (36 `.md.jinja2` templates plus
  `partials/auto-generated-header.md.jinja2` and
  `partials/common-tips.md.jinja2`).
- In `src/template_system.py`, remove the `skill_layout` parameter from
  `render_to_directory()` (signature, docstring, and the layout branch) and
  the associated agentskills_migration backreference comment. No other
  template-system code references the commands collection.
- Grep `src/` for remaining references to `templates/commands`,
  `"commands"` collection rendering, `common-tips`, and
  `auto-generated-header` to confirm zero residue (src/orchestrator/agent.py
  matches on `.claude/commands` strings are sandbox/path logic, not template
  references — leave them).

### Step 4: Shrink the AGENTS.md / CLAUDE.md managed templates

In `src/templates/claude/AGENTS.md.jinja2`, rewrite the content between
`<!-- VE:MANAGED:START -->` and `<!-- VE:MANAGED:END -->` to contain only:
- **Project Documentation (`docs/trunk/`)** pointer block (unchanged).
- **Chunks (`docs/chunks/`)** — what chunks are, lifecycle, naming
  conventions, frontmatter references (condensed from today's content).
- **Extended Artifacts** — one-line pointers to narratives, investigations,
  subsystems, friction log, external artifacts via `docs/trunk/ARTIFACTS.md`
  / `docs/trunk/EXTERNAL.md`, and the orchestrator via
  `docs/trunk/ORCHESTRATOR.md` (doc pointers only, no slash-command lists).
- **Code Backreferences** — the comment convention with pointer to
  `docs/trunk/ARTIFACTS.md#code-backreferences`.
- **Creating Artifacts** — the "never manually create artifact files" rule
  with the `ve <type> create` CLI table (CLI commands only; drop the slash
  command column).
- **Commands (Claude Code plugin)** — new section: workflow slash commands
  are distributed via the vibe-engineer Claude Code plugin
  (`/plugin marketplace add netguy204/vibe-engineer`, then
  `/plugin install vibe-engineer`); command docs/updates travel with the
  plugin, and the `ve` CLI is installed separately.

Remove entirely: Available Commands, Steward, cross-project messaging,
Getting Started's slash-command references, Learning Philosophy. Apply the
identical shrink to `CLAUDE.md.jinja2` (kept as the parallel template; today
it differs from AGENTS.md.jinja2 only by a header comment and one command
line). Preserve relevant `{# Chunk: ... #}` comments for surviving sections
and add a `{# Chunk: docs/chunks/plugin_init_slimdown ... #}` comment for the
new plugin-pointer section.

### Step 5: Update tests

- `tests/test_project.py`:
  - Delete skill-rendering tests: `test_init_creates_agents_skills_directory`,
    `test_init_creates_skill_files`, `test_init_creates_claude_commands_symlinks`,
    `test_init_command_symlinks_are_relative`, `test_init_skill_files_have_content`,
    `test_init_overwrites_existing_skills`, and the
    `TestInitSkillsSymlinkMigration` class (it exercises `_init_skills`
    migration behavior).
  - Add direct unit tests for `_is_ve_generated_file()` (header detected /
    absent / unreadable file) so the kept helper retains coverage for
    plugin_legacy_migration.
  - Add negative tests: fresh `Project.init()` creates no
    `.agents/skills/` directory and no `.claude/commands/` directory, and
    `result.created` contains no `.agents/skills/` entries.
  - Update `test_init_agents_md_has_content` (asserts `/chunk-create`) and
    idempotency tests (`test_init_preserves_user_content_skips_skills`,
    `test_init_result_tracks_skipped_and_created`,
    `test_init_reports_created_files`) to match the slimmed managed block
    and init output (AGENTS.md still updated on re-init; trunk still skipped).
- `tests/test_init.py`: update `test_init_command_creates_files` (drop
  `.agents/skills/` + `.claude/commands/` symlink assertions; keep CLAUDE.md
  symlink assertion — `_init_agents_md` is unchanged).
- `tests/test_task_init.py`: delete the `TestTaskInitSkills` class; update
  `TestTaskInitCreatedFiles` to expect only `.ve-task.yaml` + `AGENTS.md`;
  add a negative assertion that no `.agents/skills/` or `.claude/commands/`
  is created in the task root.
- `tests/test_steward_skills.py`: delete the file (entirely about steward
  skill rendering via `ve init`; steward commands live in the plugin and are
  covered by tests/test_plugin_commands.py).
- `tests/test_chunk_review_skill.py`: delete the
  `TestChunkReviewSkillTemplate` class (renders the deleted template); keep
  `TestConcurrentReviewsNoConflicts` (decision-file behavior, no templates).
- `tests/test_template_system.py`: delete tests that render the deleted
  collection — `test_real_command_template_task_context_true/_false`,
  `test_real_command_template_no_jinja_remnants_in_output`,
  `test_auto_generated_header_always_renders_in_command_templates`,
  `TestMigrateManagedClaudeMdSlashCommand`, `TestValidateFixSlashCommand` —
  and any `skill_layout` rendering tests. Keep the synthetic
  conditional-block tests (they use temp collections) and the AGENTS.md
  template tests (markers present, no Development / Template Editing
  Workflow sections — these must still pass against the shrunk template).
- Leave the orchestrator agent tests alone: their `.agents/skills/` fixtures
  are self-constructed and exercise `AgentRunner`, not `ve init`.

### Step 6: Verify behavior end-to-end

- In a throwaway temp directory (NOT this repo): `git init`, run
  `uv run ve init --project-dir <tmp>`, and confirm the produced tree is
  exactly: `docs/trunk/*`, `docs/chunks/`, `docs/narratives/`,
  `docs/reviewers/baseline/*`, `AGENTS.md` (+ `CLAUDE.md` symlink),
  `.gitignore` — with no `.agents/` and no `.claude/` directory, and an
  AGENTS.md managed block with no per-command documentation.
- Run `uv run pytest tests/` and record the new pass/fail baseline (main has
  32 pre-existing failures in subsystem test files and an orchestrator-daemon
  negative-pid test; the removals here change the collected-test total).
- Do NOT re-run `ve init` against this repository — cleaning its legacy
  layout is plugin_legacy_migration's job, and the rendered `.claude/commands/`
  and `.agents/skills/` here must remain untouched.

### Step 7: Update chunk metadata

Update `docs/chunks/plugin_init_slimdown/GOAL.md` `code_paths` with the files
touched (src/project.py, src/task_init.py, src/template_system.py,
src/templates/claude/AGENTS.md.jinja2, src/templates/claude/CLAUDE.md.jinja2,
deleted src/templates/commands/, and the five test files).

## Dependencies

- **plugin_core_commands** (ACTIVE) and **plugin_orch_commands** (ACTIVE):
  all 36+ commands are already ported to the repo-root `commands/` plugin
  directory (37 files on main), so removing the render channel strands no
  one. Verified present on this branch after fast-forwarding to main.

## Risks and Open Questions

- **Orchestrator skill loading**: `AgentRunner.get_skill_path()` reads
  `.agents/skills/<name>/SKILL.md` from the *host project* at runtime. This
  chunk does not delete any existing project's `.agents/skills/` (only stops
  creating them), so orchestrators in already-initialized projects keep
  working. But fresh projects initialized after this chunk will not have
  `.agents/skills/`, and plugin_legacy_migration will remove the layout from
  existing projects — the orchestrator's prompt source must be migrated
  before/with that chunk. **Handoff note for plugin_legacy_migration.**
- **AGENTS.md re-init churn in existing projects**: projects re-running
  `ve init` will have their managed block rewritten to the slimmed content.
  That is the intent (DEC-010), but operators see a large diff once.
- **Docs drift**: docs/trunk/SPEC.md and the rendered root CLAUDE.md of this
  repo still describe the rendered-skills world. Updating trunk docs and this
  repo's own layout is explicitly plugin_legacy_migration's scope; this chunk
  leaves them stale by design.

## Deviations

- **tests/test_orchestrator_feedback_injection.py** (not in the planned test
  list): its `TestImplementTemplateIncludesFeedbackInstructions` class read
  `src/templates/commands/chunk-implement.md.jinja2` directly to verify the
  review-feedback contract (REVIEW_FEEDBACK.md handling). Rather than delete
  the contract coverage, the tests were repointed at the static plugin
  command `commands/chunk-implement.md`, which carries the same content.
- **`TestInitSkillsSymlinkMigration` replacement**: the class tested
  `_init_skills()`'s symlink-migration behavior, which no longer exists. It
  was replaced with `TestIsVeGeneratedFile` — direct unit tests for the kept
  `_is_ve_generated_file()` helper — so the helper retains coverage for
  plugin_legacy_migration.
- Step 4 also dropped the previously-unique `/audit-intent` line from
  CLAUDE.md.jinja2; the two claude templates are now content-identical apart
  from CLAUDE.md.jinja2's historical header comment.
- **Review iteration 1**: per reviewer feedback, the template_system
  subsystem OVERVIEW was updated after all — the dangling
  `Project::_init_skills` code_reference was removed, the Scope bullet for
  the commands collection was annotated as historical, and a Known
  Deviations entry was added pointing remaining prose cleanup at
  plugin_legacy_migration.
