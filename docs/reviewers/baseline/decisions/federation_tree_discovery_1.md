---
decision: APPROVE
summary: "All five success criteria satisfied; discovery is announced, non-destructive when no tree exists, and the full suite passes 4183/4183 with two documented additions beyond the GOAL's letter (task-directory boundary, AGENTS.md.jinja2 kept in sync)"
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: A discovery helper (natural home: `src/project.py`) `find_enclosing_tree(start) -> Path | None`

- **Status**: satisfied
- **Evidence**: `src/project.py#find_enclosing_tree` walks `start` (its parent when
  `start` is a file) and each ancestor, returning the first directory with
  `docs/trunk/`. Terminates on `current == current.parent` after testing the
  filesystem root, and returns None at a `.ve-workspace.yaml` boundary
  (existence check only — the manifest format belongs to
  `federation_workspace_manifest`). Tree-before-boundary ordering means a
  workspace root that is itself a tree resolves to itself
  (`tests/test_tree_discovery.py::TestDiscoveryBoundaries`).

### Criterion 2: CLI commands use discovery instead of trusting `default="."` blindly; single-tree repos behave exactly as before

- **Status**: satisfied
- **Evidence**: `src/cli/tree_discovery.py#install_tree_discovery`, called once
  from `src/cli/__init__.py`, attaches resolution to 87 of the 88 `project_dir`
  parameters (`init` exempt). Backward compatibility rests on
  `src/project.py#resolve_project_dir`: when no enclosing tree exists the literal
  value is returned unchanged, and when `start` is already the tree it is
  returned *verbatim* (a relative `"."` stays `"."`), so no downstream code sees
  a changed value. `_same_directory` compares realpaths so `/var` vs
  `/private/var` is not mistaken for a redirect. Full suite: 4181 passed with
  zero regressions against a 4161-passing baseline.

### Criterion 3: When discovery selects a tree other than the literal cwd, the selection is visible in command output (one line)

- **Status**: satisfied
- **Evidence**: `TreeResolution.notice()` produces
  `Using VE tree <tree> (nearest enclosing tree of <given>)`, echoed to stderr by
  `resolve_project_dir_option`. stderr keeps it out of `--json` stdout payloads
  and matches the CLI's existing advisory-warning channel. Verified live:
  `ve chunk list --project-dir src` announces the worktree root, while
  `ve chunk list` (cwd is the tree) prints nothing extra. Tests assert both the
  presence and the absence
  (`TestCliUsesDiscovery::test_redirection_is_announced`,
  `::test_tree_argument_is_not_announced`).

### Criterion 4: `src/templates/claude/CLAUDE.md.jinja2` documents the nearest-enclosing-tree rule

- **Status**: satisfied
- **Evidence**: New "Resolving a Backreference: Nearest Enclosing Tree"
  subsection under Code Backreferences states the rule, both negations (not the
  cwd, not the repo root), and walks through the case study's
  `pybusiness/savings/realized.py` misresolution. Applied to
  `AGENTS.md.jinja2` as well, because that is the template
  `Project._init_agents_md` actually renders — editing only the GOAL-named file
  would have left every project's rendered instructions without the rule.
  Verified by `ve init`: the section lands inside the `VE:MANAGED` markers.

### Criterion 5: Tests — nested tree fixture proving inner-tree and between-trees resolution

- **Status**: satisfied
- **Evidence**: `tests/test_tree_discovery.py` builds `outer/` (tree) →
  `outer/mid/` (gap) → `outer/mid/inner/` (tree) → `inner/pkg/src/`. A file in
  the inner tree resolves to the inner tree; `mid` resolves to the outer tree.
  The consequence is asserted end-to-end, not just on the helper:
  `ve chunk list` from `inner/pkg/src` lists `inner_chunk` and *not*
  `outer_chunk` — the case study's real-but-wrong landing. 22 tests total.

## Reviewer Notes

Two additions go beyond the letter of the GOAL and are called out deliberately:

1. **`.ve-task.yaml` is also a walk-stopping boundary.** Not named in the GOAL,
   but necessary: commands route on `is_task_directory(project_dir)` and tests
   pass task directories as `--project-dir`, so silently rewriting one would
   break cross-repo routing. Task directories are a separate addressing regime.

2. **`AGENTS.md.jinja2` edited alongside `CLAUDE.md.jinja2`** (see Criterion 4).
   A re-render of `AGENTS.md` was used only to *verify* the template edit; the
   collateral it produced (a legacy-layout migration deleting 68 tracked files,
   plus pre-existing template drift) was reverted, and only the new section was
   applied to the rendered `AGENTS.md`.

Known limitation, deliberately not fixed here: `docs/trunk/` is the sole tree
marker, per the GOAL's explicit wording. A directory holding `docs/chunks/` but
no `docs/trunk/` nested inside a tree would now be redirected to the enclosing
tree rather than used directly. `ve init` always creates `docs/trunk/`, so this
shape does not occur in practice today, but the pointer-only trees that
`federation_template_pointers` will introduce are exactly this shape.
`TREE_MARKERS` is a module constant so that chunk can extend the marker set as a
deliberate decision rather than inheriting an accident.
