

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Two coupled pieces of work, both consequences of DEC-010 (plugin-based
distribution replaces render-based distribution):

1. **Legacy-layout migration in `ve init`.** Add a `_migrate_legacy_layout()`
   phase to `Project.init()` (src/project.py) that detects and removes the
   artifacts the old render channel left behind: `.claude/commands/` symlinks
   pointing into `.agents/skills/`, ve-generated regular files in
   `.claude/commands/` (identified by `_is_ve_generated_file()`, the existing
   safety rail), and ve-generated `SKILL.md` files under `.agents/skills/`.
   User-authored files (no AUTO-GENERATED header, or symlinks pointing
   elsewhere) are preserved with a warning. Emptied directories are pruned
   (`.claude/commands/`, `.claude/`, `.agents/skills/`, `.agents/`). The
   AGENTS.md managed-block rewrite needs no new code — the existing
   `_init_agents_md()` marker machinery already rewrites the block to the
   slimmed template on re-run. Removals are reported through a new
   `InitResult.removed` channel; the CLI prints `Removed <path>` lines and,
   when anything was removed, a pointer to the plugin install. Idempotency
   falls out naturally: a second run finds nothing to remove and reports
   only skips through the existing channels.

2. **Orchestrator phase-prompt decoupling.** `AgentRunner.get_skill_path()`
   (src/orchestrator/agent.py) still loads phase prompts from the target
   project's `.agents/skills/<name>/SKILL.md` — a layout this chunk's
   migration deletes (and which fresh inits never had since
   plugin_init_slimdown). Per DEC-010 the plugin command sources in
   `commands/` are the single source of truth, and the orchestrator always
   runs where the vibe-engineer package is installed, so the phase prompts
   ship as package data: a hatch `force-include` maps the repo-root
   `commands/` directory into the wheel at `orchestrator/skills/`, and
   `get_skill_path()` resolves `Path(__file__).parent / "skills" /
   f"{name}.md"` first, falling back to the repo-root `commands/` directory
   for development checkouts (editable installs don't materialize
   force-includes). The sdist gains `commands/**` so wheels built from sdists
   contain the prompts. `_load_skill_content()` already strips frontmatter,
   which works unchanged on the plugin command files.

Documentation follows the code: README.md, docs/trunk/SPEC.md, and
docs/trunk/ORCHESTRATOR.md drop the "ve init renders commands/symlinks"
story in favor of plugin-based distribution, the "update the plugin" upgrade
story, and the legacy-migration behavior of re-running `ve init`.

Testing per docs/trunk/TESTING_PHILOSOPHY.md: TDD for the migration logic
(behavioral, lots of boundary cases) with an end-to-end CLI integration test
against a constructed legacy-layout fixture. The migration is **never** run
against this repository's own live `.claude/commands` / `.agents/skills`
(operator decision pending) — all tests use tmp_path fixtures.

## Subsystem Considerations

- **docs/subsystems/template_system** (DOCUMENTED): This chunk USES the
  marker machinery (`parse_markers`) indirectly via `_init_agents_md()`; no
  changes to the subsystem itself.
- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk MODIFIES the
  agent runner's phase-prompt source. The change is localized to
  `get_skill_path()` and packaging; the phase-execution algorithm is
  untouched.

## Sequence

### Step 1: Decouple orchestrator phase prompts from project layout

- `pyproject.toml`:
  - Add `[tool.hatch.build.targets.wheel.force-include]` mapping
    `"commands" = "orchestrator/skills"`.
  - Add `"commands/**"` to the sdist `include` list.
- `src/orchestrator/agent.py`:
  - Rewrite `get_skill_path()` to resolve the packaged copy
    (`Path(__file__).parent / "skills" / f"{skill_name}.md"`) and fall back
    to the development checkout location
    (`Path(__file__).resolve().parents[2] / "commands" / f"{skill_name}.md"`).
  - Update the docstring and replace the stale
    `orchestrator_skill_path_fix` backreference with this chunk's.
- Tests (write first):
  - `tests/test_orchestrator_agent_skills.py`: replace
    `test_get_skill_path`'s `.agents/skills` assertion with: the resolved
    path exists and is the plugin command file for every phase (in this
    checkout, `commands/<name>.md`); the `project_dir` fixture no longer
    needs to scaffold `.agents/skills/`.
  - `get_phase_prompt` tests run against the real plugin command files:
    content loads with frontmatter stripped; the GOAL phase replaces
    `$ARGUMENTS` (asserts the real `commands/chunk-create.md` still carries
    the `$ARGUMENTS` placeholder — an invariant the orchestrator depends on).

### Step 2: Add `_migrate_legacy_layout()` to Project (TDD)

Write failing tests in `tests/test_init.py` (new `TestLegacyMigration`
class), then implement in `src/project.py`:

- Add `removed: list[str]` field to `InitResult`.
- `_migrate_legacy_layout(self) -> InitResult`:
  - `.claude/commands/` entries:
    - Symlink whose target (lexically or resolved) points into
      `.agents/skills/` → unlink, record in `removed`. Broken symlinks whose
      readlink target contains `.agents/skills` are removed too.
    - Symlink pointing elsewhere → preserve, warn.
    - Regular file with the AUTO-GENERATED header
      (`_is_ve_generated_file()`) → remove, record. Without the header →
      preserve, warn.
  - `.agents/skills/` entries:
    - Per-skill directory: remove `SKILL.md` when `_is_ve_generated_file()`;
      prune the directory if empty afterwards. Non-generated or extra files
      → preserve, warn, leave the directory.
  - Prune now-empty `.claude/commands/`, `.claude/`, `.agents/skills/`,
    `.agents/` (in that order; only when empty).
  - No legacy layout present → return an empty result (no skips, no noise).
- Wire `_migrate_legacy_layout()` into `init()` (first, before
  `_init_trunk()`), and extend the aggregation loop to merge `removed`.
- Test coverage (success criteria mapping):
  - Legacy fixture (skills with header + symlinked commands + marked
    AGENTS.md with old managed content): init removes skills and symlinks,
    prunes empty dirs, rewrites the managed block to the slimmed form,
    `removed` lists the paths.
  - Planted user-authored `.claude/commands/custom.md` (no header) and a
    user-authored skill file survive, each with a warning.
  - Second run: `removed` empty, no warnings about migration, everything
    else skipped (idempotency).
  - Fresh (non-legacy) project: no `removed` entries, no migration warnings.

### Step 3: CLI reporting and plugin-install pointer

- `src/cli/init_cmd.py`: print `Removed <path>` for each `result.removed`
  entry; when `result.removed` is non-empty, print the migration pointer:
  legacy command layout removed, commands now come from the vibe-engineer
  Claude Code plugin (`/plugin marketplace add netguy204/vibe-engineer`,
  `/plugin install vibe-engineer`), updates via `/plugin update`.
- CLI-level integration test (end-to-end success criterion): build the
  legacy fixture in tmp_path, invoke `ve init` through CliRunner, assert
  removal lines + pointer in output; invoke again, assert no removal lines
  and no pointer.

### Step 4: commands/chunk-create.md backreference repair

Add the missing backreference HTML comment for chunk `intent_workflow_docs`
(its code_reference already points at this file):
`<!-- Chunk: docs/chunks/intent_workflow_docs - Command description qualified for intent-bearing work -->`.

### Step 5: Documentation updates

- `README.md`: replace the "When you run `ve init`, slash commands are
  installed to `.claude/commands/`" section with the plugin story (commands
  ship with the plugin; table stays as documentation of what the commands
  do); note that re-running `ve init` on a legacy-layout project removes the
  old rendered files and that command upgrades are `/plugin update
  vibe-engineer`, not re-init. Adjust the project-structure tree comment for
  `src/templates/` (project docs only) and add `commands/` (plugin command
  sources).
- `docs/trunk/SPEC.md`:
  - Workflow Contexts: drop `.claude/commands/` from the Project and Task
    Directory definitions; describe commands as plugin-distributed.
  - Project / task directory structure listings: remove `.claude/commands/`
    blocks; document the plugin as the command channel.
  - `ve init` postconditions/behavior: no command rendering; add the
    legacy-migration behavior (removal of ve-generated `.agents/skills/`
    and `.claude/commands/` symlinks, preservation + warning for
    user-authored files, plugin pointer, idempotency).
  - `ve task init` postconditions: no `.claude/commands/` rendering (matches
    the already-slimmed task_init).
- `docs/trunk/ORCHESTRATOR.md`: add a short "Command distribution" note —
  workflow commands and phase prompts ship with the vibe-engineer package /
  plugin (DEC-010); the orchestrator loads phase prompts from package data,
  not from the target project; upgrades arrive via plugin/package updates.

### Step 6: Wrap-up

- Update `code_paths` in this chunk's GOAL.md.
- Run the full test suite; compare against the pre-existing 32-failure
  baseline (subsystem test files + orchestrator daemon negative-pid).
- `uv run ve validate` to confirm referential integrity.

## Dependencies

- plugin_init_slimdown (ACTIVE): slimmed AGENTS.md template, retained
  `_is_ve_generated_file()`, slimmed `init()` pipeline — all in place.

## Risks and Open Questions

- **Editable installs and force-include**: hatchling editable wheels don't
  materialize force-included files, so the dev fallback path
  (`parents[2] / "commands"`) is required for `uv run` in this repo. An
  installed wheel gets `orchestrator/skills/`. Both paths are exercised in
  CI only via the dev fallback; the packaging mapping is declarative and
  covered by a test that asserts every `PHASE_SKILL_FILES` value has a
  corresponding `commands/<name>.md` source file.
- **Symlink semantics across platforms**: legacy symlinks were relative
  (`../../.agents/skills/<name>/SKILL.md`). Detection uses `os.readlink`
  text + resolved-path containment, so both relative and absolute (and
  broken) symlinks are handled. Windows legacy installs used copies, which
  the AUTO-GENERATED header path covers.
- **This repository's own legacy layout** must NOT be migrated by this
  chunk's work — tests operate exclusively on tmp_path fixtures, and no
  `ve init` is run against the repo root.

## Deviations

- **Preserve-warnings gated on actual removals.** The plan had user-authored
  files warned about unconditionally. A smoke test showed this re-warns on
  every subsequent `ve init` run forever, and warns about user files even in
  projects that never had ve-generated content. Warnings now accompany only
  runs that removed something (a genuine migration); covered by two
  additional tests (`test_user_only_layout_produces_no_warnings`,
  `test_second_run_does_not_rewarn_about_preserved_files`).
- **Template counterpart updated.** `src/templates/trunk/ORCHESTRATOR.md.jinja2`
  (rendered into new projects) received the same "Phase Prompts and Command
  Distribution" section as this repo's docs/trunk/ORCHESTRATOR.md; the plan
  only named the latter.
- **Known pre-existing quirk, not changed**: `_init_agents_md()` reports
  `AGENTS.md` in `created` on every run that rewrites the managed block
  (existing claudemd_magic_markers behavior), so a migration second run
  prints "Created AGENTS.md" while removing nothing. Out of scope here.
