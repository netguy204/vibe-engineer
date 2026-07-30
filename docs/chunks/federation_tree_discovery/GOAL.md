---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/project.py
- src/cli/tree_discovery.py
- src/cli/__init__.py
- src/templates/claude/CLAUDE.md.jinja2
- src/templates/claude/AGENTS.md.jinja2
- tests/test_tree_discovery.py
code_references:
- ref: src/project.py#find_enclosing_tree
  implements: 'Nearest-enclosing-tree discovery: walks a path and its ancestors for
    docs/trunk/ (TREE_MARKERS), stopping at the filesystem root or at an addressing
    boundary (BOUNDARY_MARKERS: .ve-workspace.yaml existence-checked only, .ve-task.yaml)'
- ref: src/project.py#is_ve_tree
  implements: VE tree detection against the extensible tree-marker set
- ref: src/project.py#TreeResolution
  implements: Resolution outcome carrying the selected directory, the directory asked
    for, and the discovered tree
- ref: src/project.py#TreeResolution::notice
  implements: One-line report making a tree selection other than the given directory
    visible instead of silent
- ref: src/project.py#resolve_project_dir
  implements: CLI-facing resolution contract, including the fallback that leaves behavior
    unchanged when no tree encloses the path
- ref: src/cli/tree_discovery.py#resolve_project_dir_option
  implements: Click callback resolving --project-dir to its governing tree and announcing
    redirects on stderr
- ref: src/cli/tree_discovery.py#install_tree_discovery
  implements: Single wiring point applying discovery to every project_dir parameter
    in the command tree, minus EXEMPT_COMMANDS (ve init creates a tree, so it must
    act on the literal directory)
- ref: src/cli/__init__.py
  implements: Installs tree discovery once the full command tree is assembled
- ref: src/templates/claude/AGENTS.md.jinja2
  implements: Nearest-enclosing-tree rule for bare backreferences in the rendered
    agent instructions
- ref: src/templates/claude/CLAUDE.md.jinja2
  implements: Nearest-enclosing-tree rule for bare backreferences (CLAUDE.md template)
- ref: tests/test_tree_discovery.py
  implements: Nested-tree fixture proving inner-tree and between-trees resolution,
    boundary behavior, and that CLI commands act on the discovered tree
narrative: monorepo_federation
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- backend_live_validation
---
# Chunk Goal

## Minor Goal

`ve` commands resolve their governing project tree by walking **up** from the
starting directory to the nearest ancestor containing a VE tree
(`docs/trunk/`), and the documented resolution rule for bare inline
backreferences is: a bare `# Chunk:`/`# Narrative:`/`# Subsystem:` reference
in a source file resolves against the **nearest enclosing tree of that file**
— never the current working directory, never the repository root. The
CLAUDE.md template states this rule so agents inherit it in every VE project.

The failure mode this owns: a bare subsystem ref in a file under
`packages/libs/pybusiness` resolved against the working directory lands in the
monorepo root's *different* `docs/subsystems/` — a silent landing in a real,
wrong directory. A `--project-dir` that is trusted literally (the declarations
default to `"."`) makes the answer depend on where the agent happens to stand,
which is information the reference never carried.

Behavior: when `--project-dir` is omitted or names a directory without
`docs/trunk/`, discovery walks parent directories to the nearest tree and
reports which tree was selected; an explicitly provided directory that is a
tree is used as-is (no behavior change for existing single-tree projects,
whose tree root is found immediately). When no enclosing tree exists at all,
the directory is used exactly as given — discovery replaces a directory that
could not have worked, and otherwise changes nothing.

Two markers stop the upward walk, because escaping past either would answer a
question that belongs to a different addressing regime: `.ve-workspace.yaml`
(the workspace root delimits the federation) and `.ve-task.yaml` (task
directories are cross-repo mode, and commands route on them explicitly). A
boundary that is itself a tree resolves to itself. `ve init` is exempt from
discovery entirely: it creates a tree, so walking up from a directory without
`docs/trunk/` would initialize the enclosing project instead of the new one.

### Case-study grounding (Cloud Capital monorepo, diagnosed 2026-07-29)

A user's monorepo grew ~29 nested VE trees. Verified failures: one file
(`pybusiness/savings/realized.py`) carried backreferences into two trees at
once, so no working directory resolved all of them; following bare refs from
the repo root landed in a real-but-wrong `docs/subsystems/` (silent
misresolution); two refs (`run_rate_cloud_capital_split`,
`rsv2_pybusiness_model`) were born dangling — never resolvable from anywhere,
with no deletion event for an audit to detect; and a cookiecutter task
template shipped a full `docs/` tree, minting a new namespace per scaffolded
package. 299 of 718 chunk directories were already external.yaml pointers to a
hub repo — federation is the de facto convention; only addressing is
single-tree. See `docs/narratives/monorepo_federation/OVERVIEW.md`.

## Success Criteria

- A discovery helper (natural home: `src/project.py`) `find_enclosing_tree(
  start: Path) -> Path | None` walking `start` and its parents for
  `docs/trunk/`, stopping at the filesystem root (and not escaping past a
  `.ve-workspace.yaml` workspace root when one is present).
- CLI commands use discovery instead of trusting `default="."` blindly;
  single-tree repos behave exactly as before (covered by existing test suite
  passing unchanged).
- When discovery selects a tree other than the literal cwd, the selection is
  visible in command output (one line), so misrouting is never silent.
- `src/templates/claude/CLAUDE.md.jinja2` documents the
  nearest-enclosing-tree rule for bare backreferences (edit the template, not
  rendered CLAUDE.md; re-render with `ve init` to verify).
- Tests: nested tree fixture (tree inside a tree) proving a file in the inner
  tree resolves to the inner tree and a file between the two resolves to the
  outer one.

## Rejected Ideas

### Resolve bare refs from the repository root

Resolving from the repository root is what an agent falls into when nothing
tells it otherwise (cwd = repo root), and it is exactly the silent-misresolution
failure the case study documented. The root tree is just another tree; it has no
addressing privilege.
