---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/project.py
- src/cli/init_cmd.py
- tests/test_project.py
- tests/test_init.py
code_references:
- ref: src/project.py#InitResult
  implements: notices list carrying informational arrangement announcements
- ref: src/project.py#Project::_init_agents_md
  implements: Records which arrangement outcome occurred and appends the notice lines
- ref: src/project.py#Project::init
  implements: Aggregates notices from sub-results
- ref: src/cli/init_cmd.py#init
  implements: Prints arrangement notices in ve init output
- ref: tests/test_project.py#TestInitAgentsMdNotices
  implements: Unit coverage of each arrangement outcome's notice
- ref: tests/test_init.py#TestInitCommand::test_init_announces_agents_md_arrangement
  implements: CLI-level assertion that a fresh init names the arrangement
- ref: tests/test_init.py#TestInitCommand::test_init_announces_claude_md_conversion
  implements: CLI-level assertion that the CLAUDE.md conversion is announced
narrative: init_trust
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- crossref_absence_evidence
- crossref_artifact_id_cap
- crossref_defect_line_anchor
- crossref_generator_verify
- crossref_glob_refs
- crossref_pointer_guard
- crossref_reexport_absence
- crossref_refactor_move
- crossref_unchecked_anchors
- crossref_workspace_parity
- federation_member_refs
---
# Chunk Goal

## Minor Goal

`ve init` announces the AGENTS.md/CLAUDE.md arrangement it produces. `Project._init_agents_md` (src/project.py) records which arrangement outcome occurred — created AGENTS.md fresh, converted a tracked regular CLAUDE.md into a symlink to AGENTS.md, updated the managed block in place, or created/repointed the CLAUDE.md symlink — and reports it as a notice on `InitResult`; the `init` command (src/cli/init_cmd.py) prints each notice. The conversion notice names the resulting git file-type change, so the 'T' typechange in git status is announced rather than a surprise (field report: 'an operator who commits without looking lands a file-type change they did not ask for'). Output-only chunk: the arrangement behavior itself is unchanged.

## Success Criteria

- `InitResult` carries a `notices` list, aggregated by `Project.init()` and
  printed by `ve init` (src/cli/init_cmd.py), so arrangement announcements
  flow through the existing result-reporting path rather than direct prints.
- Converting a pre-migration regular CLAUDE.md emits a notice that names the
  conversion to a symlink and the resulting git file-type change — the
  field-reported surprise 'T' is announced before the operator commits.
- A fresh init emits a notice stating AGENTS.md was created and CLAUDE.md is
  a symlink to it; a re-init emits a notice that the managed block in
  AGENTS.md was updated in place; creating or repointing the CLAUDE.md
  symlink for an existing AGENTS.md is likewise announced.
- Exactly one arrangement notice per init run (symlink-only notices appear
  only when not already implied by the arrangement line).
- No behavior change to the arrangement itself: file operations, branch
  conditions, and template rendering in `Project._init_agents_md` are
  untouched; existing `created`/`skipped`/`warnings` reporting (including
  `test_reinit_reports_updated_not_skipped`) is unchanged.
- Unit tests cover each arrangement outcome's notice; a CLI test verifies
  the lines reach `ve init` output. `uv run pytest tests/` passes.