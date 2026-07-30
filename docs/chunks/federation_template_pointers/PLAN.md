# Implementation Plan

## Approach

### What the scaffold actually is

The GOAL names `src/task_init.py` / `src/templates/task/` as "the task scaffold",
inherited from the narrative prompt ("the task scaffold templates currently ship a
full docs tree"). Reading the code first changes the shape of the work:

- `ve task init` mints **nothing**. It writes `.ve-task.yaml` plus an AGENTS.md and
  *requires* every participating repo to already be VE-initialized
  (`src/task_init.py` `_validate_and_resolve` rejects a directory without
  `docs/chunks/`). `src/templates/task/` holds only AGENTS.md/CLAUDE.md prose. A
  task directory is a cross-repo coordination surface, not a package.
- The thing that mints namespaces in the case study is the operator's *cookiecutter*
  template, which shipped a literal `docs/trunk` + `docs/chunks` inside
  `{{cookiecutter.task_name}}`. VE cannot edit that template. What VE can do — and
  what the GOAL's success criteria actually describe — is **offer a scaffold command
  a template can call** whose default output is a pointer-only member, so the
  correct thing is the easy thing.

So this chunk adds the missing surface rather than editing `src/templates/task/`:
`ve package scaffold`. Every success criterion attaches to it.

### Design

`ve package scaffold PATH` (new `src/cli/package.py`, logic in new
`src/package_scaffold.py`, following the `validate()`-then-`execute()` shape
`TaskInit` already uses):

| Invocation | Result |
|---|---|
| `--interest '<member>::docs/<type>/<id>[: why]'` (repeatable) | pointer-only tree: one `external.yaml` interest edge per flag, **no `docs/trunk/`, no empty artifact dirs**, plus a rendered AGENTS.md and member registration |
| `--full-tree` | full VE tree via `Project(path).init()` (opt-in), also registered; may carry interests too |
| neither | error explaining that a package which consumes no documented intent needs no docs tree, and that `--full-tree` is the opt-in for packages that will own intent |

Pointer creation reuses prior-wave infrastructure verbatim — `normalize_artifact_path`
to parse the artifact, `create_peer_yaml` to write a validated `tree:` pointer, the
same two calls `ve external point` makes. Registration goes through the library API
(`load_workspace` → `add_member` → `save_workspace`), not by shelling out to
`ve workspace add`, and no new command is added to `src/cli/workspace.py`.

Why a `docs/` tree with **only** pointers is registrable at all: `is_ve_tree` in
`src/workspace.py` is permissive (docs/ + any artifact dir) while
`project.TREE_MARKERS` stays `("docs/trunk",)`. That split is what makes the
pointer-only tier expressible — the package is addressable as `<member>::` and is
*not* a governing tree for bare refs. Neither predicate is touched here; the chunk
consumes them and locks the consequence with tests.

Consequence worth stating: at least one interest edge is required for a pointer-only
package, because `docs/` with nothing under it is not a registrable tree and an
empty `docs/chunks/` is exactly the namespace the GOAL forbids creating. "A package
that consumes no documented intent needs no docs tree" is the honest answer, and the
error says so.

Interest grammar `<member>::docs/<type>/<id>[: why]` reuses the `::` qualifier
vocabulary from `federation_qualified_refs` so one string is copy-pasteable between
a comment, a scaffold flag, and a cookiecutter variable. A missing `why:` warns
rather than fails (the model allows None), but a pointer at a **nonexistent**
artifact is refused: born-dangling refs are the case-study defect that leaves no
deletion event behind, and creation time is the cheapest place to catch them.

### Prevention for the operator who scaffolds by running `ve init`

`ve package scaffold` only helps a template that calls it. The other half of "stop
minting namespaces" is that minting one inside a workspace should never be silent,
so `Project.init()` gains one advisory (reported through the existing
`InitResult.warnings` channel, which the CLI already prints to stderr): when a
`.ve-workspace.yaml` exists above the target, the target has no trunk yet, and an
enclosing governing tree already exists, `ve init` says that it is about to create a
new addressing root, points at `ve package scaffold --interest` for a
consuming-only package, and reminds the operator to register the tree. Advisory
only: `ve init` still creates the full tree and does not mutate the parent manifest.
Auto-registration stays on the explicitly workspace-aware command.

### Testing

Per TESTING_PHILOSOPHY, tests are written first and assert the GOAL's criteria
rather than the implementation's shape. Fixtures come from `tests/conftest.py`
(`make_ve_tree`, `make_workspace`, `write_workspace_manifest`) — imported, not
modified. Criterion-to-test mapping is spelled out in Step 6.

## Subsystem Considerations

- **docs/subsystems/cross_repo_operations** (check status at implementation time):
  this chunk USES the intra-workspace addressing flavor added by
  `federation_peer_refs` (`create_peer_yaml`, `tree:` pointers). It adds no new
  reference flavor — the scaffold is a new *producer* of existing peer pointers, so
  the backreference on the pointer-writing code names the subsystem and this chunk.
- **docs/subsystems/template_system**: the new `src/templates/package/` collection
  is rendered with `render_template("package", "AGENTS.md.jinja2", ...)`, following
  the collection-per-directory convention; no change to the rendering machinery.

## Sequence

### Step 1: Failing tests for the pointer-only default

`tests/test_package_scaffold.py` — library level, `PackageScaffold`:

- scaffolding with interests into a workspace fixture writes
  `docs/<type>/<id>/external.yaml` with `tree: <member>` and the `why:` note, and
  creates **no** `docs/trunk/` and no artifact directory that holds no pointer;
- the manifest gains the member (name defaulting from the directory name), and the
  written YAML round-trips through `load_workspace`;
- no manifest above the path → registration skipped, result says so, files still
  created (`--full-tree`, since interests need a manifest to resolve a member);
- no interests and no `--full-tree` → validation error naming the opt-in;
- unknown member, nonexistent target artifact, duplicate member name, path that is
  already a full VE tree → validation errors, and **nothing written** (validate runs
  before any mkdir);
- `--full-tree` → `docs/trunk/GOAL.md` exists, member registered.

### Step 2: `src/package_scaffold.py`

`InterestEdge` (member, artifact_type, artifact_id, why, local_name),
`parse_interest(spec)` for the `<member>::docs/<type>/<id>[: why]` grammar,
`PackageScaffoldResult` (path, name, full_tree, created, registered,
workspace_root, governing_tree, warnings), and `PackageScaffold.validate()` /
`.execute()`.

`validate()` resolves the workspace (absent is legal), checks the member names
against the manifest, checks each target artifact exists in the member's tree,
checks the member name grammar and uniqueness, and rejects a path that already
holds a tree. `execute()` creates the directory, writes pointers (or runs
`Project(path).init()` for `--full-tree`), renders AGENTS.md for the pointer-only
case, then registers the member.

### Step 3: `src/templates/package/AGENTS.md.jinja2`

Rendered for pointer-only packages only (a full tree gets the standard project
AGENTS.md from `Project.init()`, which is correct — it *is* a governing tree).
Only AGENTS.md is rendered, with a CLAUDE.md symlink, per `agentskills_migration`;
no near-duplicate CLAUDE.md template is added.

Content, all of it computed rather than boilerplate:

- what a pointer-only package is, and that it deliberately mints no namespace;
- **where the governing docs live** — the nearest enclosing tree from
  `project.find_enclosing_tree`, as a relative path, with the trunk files to read
  first; when there is none (the walk stops at the workspace-root boundary), it says
  so plainly: bare `docs/...` refs from here resolve to nothing, so every reference
  must be qualified `<member>::docs/...` or expressed as a pointer;
- the intent this package consumes: one row per interest edge with its `why:`;
- how to add another edge later (`ve external point <member> <artifact> --why`);
- **how to opt into a full tree later** (`ve init --project-dir <path>` +
  `ve workspace add`), with the cost stated: a trunk makes this directory an
  addressing root and bare refs beneath it stop resolving upward.

### Step 4: `src/cli/package.py` + registration

`ve package scaffold PATH [--name] [--interest ...] [--full-tree]`, echoing created
files, each interest edge, and either the registration or the reason it was skipped.
Registered in `src/cli/__init__.py` **above** the `install_tree_discovery(cli)` line.
No parameter is named `project_dir`: the scaffold creates a tree, so an upward
redirect would be exactly wrong (the same reason `init` is in `EXEMPT_COMMANDS`).
CLI tests in `tests/test_package_scaffold_cli.py` cover the reported output, the
skip-registration message, and nonzero exit on the error paths.

### Step 5: `ve init` workspace advisory

`Project._workspace_advisory()`, wired into `Project.init()`; unit tests that it
fires inside a workspace with an enclosing tree, and stays silent for a plain
single-repo `ve init` (no manifest above) and for a re-init of an existing tree.

### Step 6: Pointer-only resolution test (criterion 2)

Scaffold a pointer-only package inside a workspace whose root tree has a trunk, then
assert against `src/project.py` (no code change expected — this locks the property
the GOAL claims): `find_enclosing_tree(pkg/src/mod.py)` is the *enclosing* tree, not
the package; `is_ve_tree(pkg)` is False while `workspace.is_ve_tree(pkg)` is True;
`load_external_ref` still resolves the package's own pointers; and with no enclosing
governing tree, resolution is None rather than a guess.

### Step 7: Operator documentation

README "Monorepos With Multiple Trees" gains a "Scaffolding a new package"
subsection (DEC-003: operator-facing commands are documented in the README), and
`docs/trunk/EXTERNAL.md` gains a short "Pointer-only trees" subsection inside the
peer-reference section — inserted there rather than appended at the end, to keep the
merge surface away from the other chunks in this wave.

## Dependencies

- `federation_workspace_manifest` (merged): `load_workspace`, `add_member`,
  `is_ve_tree`, `relativize_to_workspace`, `suggest_member_names`.
- `federation_peer_refs` (merged): `create_peer_yaml`, `tree:` pointers,
  `ve external point` as the post-scaffold way to add an edge.
- `federation_tree_discovery` (merged): `find_enclosing_tree`, `TREE_MARKERS`,
  `BOUNDARY_MARKERS`.

## Risks and Open Questions

- **Command name.** `ve workspace scaffold` reads better than `ve package scaffold`,
  but `src/cli/workspace.py` is owned by a concurrent chunk this wave, and the
  instruction is to add no new CLI surface there. The group lives in its own module,
  so moving the command under `workspace` later is a two-line change. Flagged for
  the operator.
- **Registration requires a tree on disk.** `add_member` validates `is_ve_tree`, so
  files must exist before registration — hence validate-everything-first, so a
  rejected scaffold leaves nothing behind. A registration failure after file
  creation is still possible in principle (concurrent manifest edit); the result
  reports it as a warning with the exact `ve workspace add` to run.
- **`--interest` requires a manifest.** A `tree:` pointer names a member, so
  pointer-only scaffolding outside a workspace cannot work. The error points at
  `ve workspace init` instead of silently writing an unresolvable pointer.
- **No ADR.** The pointer-only membership tier is arguably ADR-worthy, but
  `docs/trunk/DECISIONS.md` appends are a merge hot spot while two sibling chunks
  run; raised as a handoff instead.

## Deviations

- **The named files were the wrong files.** The GOAL points at `src/task_init.py`
  and `src/templates/task/`; both were left untouched, because reading them showed
  `ve task init` mints no namespace (it *requires* every participating repo to be
  VE-initialized already) and the task templates contain only prose. Editing them
  would have satisfied the file list and none of the success criteria. The criteria
  attach instead to a new surface — `ve package scaffold` — which is what a package
  template calls. See Approach for the evidence.
- **Added: a `ve init` advisory** (Step 5), not requested by the GOAL. Without it,
  the chunk only helps operators whose template calls the new command, while the
  common case — a human or agent running `ve init` in a new package — still mints an
  addressing root silently. Advisory only; no behavior change.
- **`--interest` is required for a pointer-only scaffold.** The GOAL forbids an empty
  `docs/chunks/`, and `docs/` with nothing under it is not a registrable member tree,
  so there is no such thing as a pointer-only package with zero edges. The error says
  what to do instead of inventing an empty namespace to register.
- **Unresolvable interest targets are refused, not warned.** The narrative's
  born-dangling refs (`run_rate_cloud_capital_split`, `rsv2_pybusiness_model`) are
  the case for failing at creation; `ve external point` already made the same call,
  so the two surfaces agree. A missing `why:` only warns, matching the model.
