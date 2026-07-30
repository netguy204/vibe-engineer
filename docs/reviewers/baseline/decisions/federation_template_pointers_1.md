---
decision: APPROVE
summary: "All four criteria satisfied by a new `ve package scaffold` surface; the GOAL's named files (task_init.py, templates/task/) were correctly left alone because they mint no namespace, and that deviation is documented in PLAN.md for operator review."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: Task/package scaffolding gains the pointer-only default and a full-tree opt-in flag; registers the new member when a manifest is present (and says so), skips registration cleanly when there is none

- **Status**: satisfied
- **Evidence**: `src/package_scaffold.py#PackageScaffold` — pointer-only is the
  default path (`full_tree=False`), `--full-tree` is the opt-in, and
  `PackageScaffold._register` goes through the library API (`load_workspace` →
  `add_member` → `save_workspace`) rather than new CLI surface, per the wave
  constraint. `src/cli/package.py#scaffold` reports registration ("Registered
  member 'viz' in the workspace at …") and reports the skip when no manifest exists
  above the path. Tests: `TestPointerOnlyScaffold::test_registers_the_package_as_a_workspace_member`,
  `TestRegistrationWithoutManifest::test_full_tree_scaffold_outside_a_workspace_still_works`,
  `test_package_scaffold_cli.py::test_says_when_registration_is_skipped`.
  **Deviation, recorded in PLAN.md:** the GOAL names `src/task_init.py` and
  `src/templates/task/`; both were left untouched because `ve task init` mints
  nothing (it requires participating repos to be VE-initialized already) and the
  task templates hold only prose. The criteria attach to the new command instead.

### Criterion 2: A pointer-only tree is not a governing tree for bare-ref resolution; bare refs resolve upward, qualified refs and its own pointers work normally

- **Status**: satisfied
- **Evidence**: No production change was needed — `project.TREE_MARKERS` stays
  `("docs/trunk",)` while `workspace.is_ve_tree` stays permissive, which is exactly
  the split the pointer-only tier needs. The property is now locked by
  `TestPointerOnlyTreeResolution`: `find_enclosing_tree` on a file in the scaffolded
  package returns the *enclosing* tree; `workspace.is_ve_tree(pkg)` is True while
  `project.is_ve_tree(pkg)` is False; `resolve_project_dir(pkg)` redirects; the
  package's own peer pointer still resolves through the manifest; and with no
  enclosing tree, resolution returns None rather than a guess.

### Criterion 3: The rendered CLAUDE.md/AGENTS.md explains where governing docs live and how to opt into a full tree later

- **Status**: satisfied
- **Evidence**: `src/templates/package/AGENTS.md.jinja2`, rendered by
  `PackageScaffold._render_agents_md` with a computed (not boilerplate) location:
  the relative path to `find_enclosing_tree`'s answer plus the trunk files to read,
  or — when the walk finds no trunk before the workspace root — an explicit
  statement that bare refs resolve to nothing here and every reference must be
  qualified. CLAUDE.md is a symlink per `agentskills_migration`. The whole body sits
  inside `VE:MANAGED` markers, so `ve init` later replaces it with the standard
  project instructions; that migration is tested
  (`test_opting_into_a_full_tree_replaces_the_managed_block`).

### Criterion 4: Tests: scaffold into a workspace fixture → manifest updated, docs contains only pointers; scaffold with the opt-in flag → full tree created and registered

- **Status**: satisfied
- **Evidence**: `tests/test_package_scaffold.py` (39 tests) and
  `tests/test_package_scaffold_cli.py` (10). `test_mints_no_namespace` asserts both
  halves of "only pointers" — no `docs/trunk`, and no artifact directory that holds
  no pointer. `TestFullTreeOptIn` covers the opt-in creating `docs/trunk/GOAL.md`
  and registering the member. Boundary coverage: unknown member, target artifact
  that never existed, duplicate member name, already-registered path, existing full
  tree, package outside the workspace, interests without a manifest — each asserted
  to leave nothing on disk. Full suite: 4380 passed (baseline 4331 + 49 new), 0
  failed. `ve validate`: 50 pre-existing errors, unchanged from main.

## Notes for the operator

Two judgment calls worth a look, both argued in PLAN.md "Risks" and "Deviations":

1. **Command name.** `ve workspace scaffold` reads better than `ve package
   scaffold`, but `src/cli/workspace.py` belonged to a concurrent chunk this wave.
   The group is a standalone module, so moving it is a two-line change.
2. **Scope addition.** `Project._workspace_advisory` makes `ve init` say out loud
   that it is minting an addressing root inside a workspace, and offers
   `ve package scaffold` / `ve workspace add`. Not requested by the GOAL, but
   without it the chunk only reaches operators whose template calls the new command.
   Advisory only — no behavior change, and suppressed for `--full-tree` scaffolds
   that register the tree themselves.

No ADR was added for the pointer-only membership tier: `docs/trunk/DECISIONS.md` is
a merge hot spot while sibling chunks run. It may deserve one.
