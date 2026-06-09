---
decision: FEEDBACK
summary: "All four success criteria are functionally satisfied, but the chunk left a dangling code_reference to the deleted Project::_init_skills symbol (still marked COMPLIANT) in the template_system subsystem OVERVIEW, and skipped the Known Deviations note its own PLAN promised for the stale Scope mention of src/templates/commands/."
operator_review: null
---

## Criteria Assessment

### Criterion 1: A fresh `ve init` produces no .agents/skills/ directory, no .claude/commands/ entries, and an AGENTS.md whose managed block contains no per-command documentation

- **Status**: satisfied
- **Evidence**: `_init_skills()` removed from src/project.py and from the `init()` pipeline (src/project.py#Project::init). Verified end-to-end in a throwaway git repo: `uv run ve init --project-dir <tmp>` produced only docs/trunk/*, docs/chunks/, docs/narratives/, docs/reviewers/baseline/*, AGENTS.md (+CLAUDE.md symlink), .gitignore — no .agents/ or .claude/ anywhere. AGENTS.md managed block contains trunk/chunk/artifact pointers plus a plugin-install pointer and no "Available Commands" list. Negative tests added: tests/test_project.py (test_init_creates_no_agents_skills_directory, test_init_creates_no_claude_commands_directory) and tests/test_init.py.

### Criterion 2: src/templates/commands/ is deleted and the template system has no remaining references to the collection

- **Status**: satisfied (code) / gap (subsystem documentation — see Feedback Item 1)
- **Evidence**: All 38 files (36 templates + 2 partials) git-rm'ed. `skill_layout` parameter removed from render_to_directory (src/template_system.py). Grep over src/ for `templates/commands`, `"commands"` collection rendering, `common-tips`, `auto-generated-header` returns only the explanatory backreference comment. However, docs/subsystems/template_system/OVERVIEW.md still lists a code_reference to `src/project.py#Project::_init_skills` with `compliance: COMPLIANT` — that symbol no longer exists — and its Scope section still claims `src/templates/commands/` as in-scope.

### Criterion 3: `ve task init` is equivalently slimmed

- **Status**: satisfied
- **Evidence**: `_render_skills()` and its call site removed from src/task_init.py#TaskInit::execute; `.ve-task.yaml` and `_render_agents_md()` (with CLAUDE.md symlink) retained; unused render_to_directory import dropped. Negative tests added in tests/test_task_init.py (TestTaskInitNoSkills).

### Criterion 4: The test suite passes with rendering/symlink tests updated or removed

- **Status**: satisfied
- **Evidence**: Full suite: 32 failed / 3975 passed — the 32 failures are the documented pre-existing baseline (subsystem test files + orchestrator daemon negative-pid test), none in files touched by this chunk. tests/test_steward_skills.py deleted; rendering/symlink tests in test_project.py, test_init.py, test_task_init.py, test_template_system.py, test_chunk_review_skill.py updated or removed; test_orchestrator_feedback_injection.py repointed at the static plugin command (documented in PLAN.md Deviations). `_is_ve_generated_file()` retains direct unit coverage (TestIsVeGeneratedFile) for plugin_legacy_migration, and parse_markers/marker machinery is untouched with passing tests.

## Feedback Items

1. **Location**: docs/subsystems/template_system/OVERVIEW.md (frontmatter code_references; Scope section)
   - **Concern**: The chunk deleted `Project._init_skills` and `src/templates/commands/` but left the subsystem OVERVIEW claiming a `COMPLIANT` code_reference to `src/project.py#Project::_init_skills` (a now-nonexistent symbol) and an in-scope bullet for "Slash command templates: the `src/templates/commands/` templates". The chunk's own PLAN (Subsystem Considerations) committed to at least noting this as a Known Deviation, which was not done. Dangling symbol references are exactly the referential decay the artifact system exists to prevent.
   - **Suggestion**: Remove the `Project::_init_skills` entry from the OVERVIEW's code_references and drop (or annotate as historical) the "Slash command templates" Scope bullet, OR add a Known Deviations entry stating that command distribution moved to the Claude Code plugin (docs/chunks/plugin_init_slimdown) and the remaining prose is updated by plugin_legacy_migration. Either way, no frontmatter reference to a deleted symbol should remain.
   - **Severity**: style/documentation (artifact integrity)
   - **Confidence**: high

## Escalation Reason

<!-- Not applicable. -->
