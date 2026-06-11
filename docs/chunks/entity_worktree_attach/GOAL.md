---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/entity_worktree.py
- src/cli/entity.py
- src/entity_repo.py
- src/orchestrator/worktree.py
- tests/test_entity_worktree_attach.py
- tests/test_entity_worktree_attach_cli.py
- tests/test_entity_push_pull_cli.py
- docs/chunks/entity_worktree_attach/MIGRATION.md
- README.md
code_references:
  - ref: src/cli/entity_worktree.py#do_attach
    implements: "Worktree-based attach: composes ensure_canonical_clone + git worktree add"
  - ref: src/cli/entity_worktree.py#do_detach
    implements: "Worktree-based detach: git worktree remove + branch cleanup"
  - ref: src/cli/entity_worktree.py#project_slug
    implements: "Deterministic project slug for branch naming"
  - ref: src/cli/entity_worktree.py#attach_branch_name
    implements: "Project-scoped branch convention: ve-attach/<slug>"
  - ref: src/cli/entity_worktree.py#AttachResult
    implements: "Importable result for downstream entity_claude_autoattach"
  - ref: src/cli/entity_worktree.py#WorktreeAttachError
    implements: "Distinct error class for worktree-attach failures"
  - ref: src/cli/entity.py#attach
    implements: "ve entity attach CLI wired to do_attach"
  - ref: src/cli/entity.py#detach
    implements: "ve entity detach CLI wired to do_detach"
  - ref: src/cli/entity.py#list_entities
    implements: "Worktree-aware entity listing (no submodule branch)"
  - ref: src/entity_repo.py#AttachedEntityInfo
    implements: "Metadata for worktree-attached entities surfaced by ve entity list"
  - ref: src/entity_repo.py#list_attached_entities
    implements: "Worktree-aware attached-entity enumeration"
  - ref: src/entity_repo.py#push_entity
    implements: "Configured-upstream-aware push for worktree-attached entities"
  - ref: src/entity_repo.py#pull_entity
    implements: "Configured-upstream-aware pull for worktree-attached entities"
narrative: entity_worktrees
investigation: null
subsystems: []
friction_entries: []
depends_on:
- entity_config_toml
- entity_canonical_clone
created_after:
- plugin_hook_cli_bootstrap
---

# Chunk Goal

## Minor Goal

`ve entity attach <name>` attaches an entity to the current project as a
git worktree of the canonical clone in `entities_dir/<name>`. `.entities/<name>`
is created via `git worktree add` against the canonical clone, on a
project-scoped branch so the same canonical clone can be attached to
multiple projects on the same machine without colliding with git's
"one worktree per branch" constraint.

`ve entity detach <name>` correspondingly removes the worktree via
`git worktree remove` (and any project-scoped branch the attach created),
leaving the canonical clone in `entities_dir/<name>` untouched and reusable
by future attaches.

All submodule machinery is removed from the attach/detach pathway: no
`.gitmodules` edits, no `git submodule add`/`deinit`, no submodule-aware
status output, no submodule-specific code branches in any entity command.
The clean break is total at the code level. Users on the pre-1.0
(submodule) version are directed by README/release notes to detach with
their old `ve` before upgrading; the 1.0 code does not detect or migrate
submodule attachments.

The behavioral guarantee for downstream commands is that the on-disk shape
of an attached entity — files at `.entities/<name>/`, the same directory
layout as before — is preserved. Anything that reads from
`.entities/<name>/identity.md`, `memories/`, `wiki/`, or `touch_log.jsonl`
keeps working without modification. The change is purely in how
`.entities/<name>` came to exist on disk.

## Success Criteria

- `ve entity attach <name>` against an entity whose canonical clone
  already exists in `entities_dir/<name>` creates `.entities/<name>` as a
  git worktree on a project-scoped branch.
- `ve entity attach <name>` against an entity whose canonical clone does
  *not* yet exist composes with the canonical-clone helper to clone first,
  then worktree-add. (This is the seam `ve entity claude` will use in the
  next chunk.)
- `ve entity detach <name>` removes the worktree at `.entities/<name>`
  and the project-scoped branch, leaving `entities_dir/<name>` intact.
- Two different projects on the same machine can each attach the same
  entity simultaneously — each gets its own worktree on its own
  project-scoped branch off the same canonical clone — without git
  errors.
- All submodule code paths are removed: grep of the codebase finds no
  remaining `git submodule`, `.gitmodules` edits, or submodule-aware
  status logic in entity commands.
- Existing commands that operate on attached entities (`ve entity
  startup`, `ve entity touch`, `ve entity recall`, `ve entity shutdown`,
  `ve entity episodic`) work against worktree-attached entities without
  regression.
- Re-attaching an already-attached entity to the same project either is
  a friendly no-op or fails with a clear "already attached" message —
  pick one during planning and document the decision in the PLAN.
- README and CHANGELOG document the migration step for pre-1.0 users
  (detach-then-upgrade-then-reattach) clearly enough that an existing
  user can complete it without reading source.
- Tests cover: fresh-attach with canonical clone present, fresh-attach
  composing with canonical-clone helper, detach removes worktree and
  branch but preserves canonical clone, two-projects-same-entity, and
  re-attach semantics (whichever is chosen).

## Notes for Planning

- This is `proposed_chunks[2]` of the `entity_worktrees` narrative.
- Depends on `entity_config_toml` and `entity_canonical_clone`.
- Pick the project-scoped branch naming convention during planning. The
  hard constraint: two worktrees can't share a branch. Candidates
  include `<project-name>/main`, `entity-worktree/<project-name>`, or
  something keyed off the project's path hash. The choice should be
  stable across attach/detach cycles for the same project.
- Decide re-attach semantics during planning: idempotent no-op vs.
  refuse-without-`--force`. Document the choice.
