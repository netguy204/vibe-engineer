# Implementation Plan

## Approach

Mirror the existing `.ve-task.yaml` pattern exactly: a pydantic model in
`src/models/` (where `TaskConfig` already lives, per DEC-008), a CLI-free
loader module in `src/` (as `src/task/config.py` is to `TaskConfig`), and a
thin click command group in `src/cli/`. This keeps the criterion "loader is
importable by other subsystems without CLI coupling" structurally true rather
than merely intended: `src/workspace.py` imports nothing from `cli/`.

Three files of new code plus one two-line registration edit:

- `src/models/workspace.py` — `WorkspaceMember`, `WorkspaceManifest`, member
  name grammar. Shape validation only (grammar, path shape, duplicates) —
  nothing that needs the filesystem.
- `src/workspace.py` — manifest discovery (walk up for `.ve-workspace.yaml`),
  load/save, filesystem validation (paths exist and hold a VE tree), scan
  discovery, and member resolution (including longest-prefix lookup for nested
  members).
- `src/cli/workspace.py` — `ve workspace list | add | init`.
- `src/cli/__init__.py` — one import line, one `add_command` line.

### On-disk format

The manifest is a name→path mapping, as the GOAL specifies:

```yaml
members:
  pybusiness: packages/libs/pybusiness
  visualization: apps/viz
```

Paths are workspace-root-relative POSIX strings, consistent with DEC-004's
spirit (references are root-relative, not file-relative) — here the root is the
workspace root, which is exactly the anchor `<member>::` qualifiers need.

A mapping is the right shape for a lookup table, but `yaml.safe_load` silently
keeps the last of two duplicate keys, which would defeat the "duplicate name
rejection" criterion at the only layer where duplicates can actually appear (a
hand-edited file). So loading uses a `SafeLoader` subclass that raises on
duplicate keys within a mapping. The model additionally rejects duplicates for
programmatic construction, so `ve workspace add` cannot mint one either.

### Two predicates, deliberately different strictness

- **Membership validation** accepts a directory as a VE tree if `docs/` exists
  and contains `trunk/` or any artifact directory (`chunks/`, `narratives/`,
  `investigations/`, `subsystems/`). Permissive on purpose: the narrative's
  later `federation_template_pointers` chunk mints pointer-only trees that have
  `docs/chunks/<name>/external.yaml` and no `docs/trunk/`, and those must be
  registrable.
- **Scan discovery** only proposes directories containing `docs/trunk/`. Strict
  on purpose: `docs/trunk/` is the strongest available signal of an
  *intentional* tree, and a bootstrap scan that proposes every pointer stub
  would bury the operator. Scan is an aid, not the authority (see the GOAL's
  rejected ideas).

Scan does **not** prune below a discovered tree — nesting is the point, and the
case-study monorepo has trees inside trees.

### Nesting

Nested member paths are legal. The disambiguating rule is **longest prefix
wins**: `find_member_for_path` returns the innermost member containing a given
path. This is the primitive the later validator and peer-ref chunks need to
answer "which tree governs this file?", so it belongs here rather than being
re-derived per consumer. Round-tripping nested members through save/load is a
test, per the success criteria.

### Testing

TDD per docs/trunk/TESTING_PHILOSOPHY.md: tests first in
`tests/test_workspace_manifest.py`, covering the four criterion areas
(load/validate, scan with an excluded template tree, duplicate rejection,
bad-name rejection) as unit tests against the loader plus `CliRunner`
integration tests for the three commands. Model construction that only checks
storage is not tested (trivial); validation *rejections*, filesystem side
effects, scan output, and exit codes are.

A helper that builds a multi-tree workspace on disk is needed by most tests in
the file; it goes in `tests/conftest.py` only if a second file needs it —
for now it stays local to the test module, since `make_ve_initialized_git_repo`
is git-flavored and heavier than these tests need.

Update `code_paths` in docs/chunks/federation_workspace_manifest/GOAL.md with
the files above.

## Subsystem Considerations

- **docs/subsystems/cross_repo_operations** (DOCUMENTED): adjacent but not
  touched. That subsystem governs `org/repo` references resolved through a repo
  cache across *repositories*; a workspace member is a path within one working
  copy, resolved directly. No code is shared, so this chunk neither implements
  nor uses it. Once `federation_peer_refs` adds `tree:` targets to
  external.yaml — which *is* cross_repo_operations territory — the two meet;
  that chunk, not this one, owns recording the relationship.
- No other subsystem's scope is touched. No deviations discovered.

## Sequence

### Step 1: Failing tests for the model and loader

Create `tests/test_workspace_manifest.py` with a local helper that materializes
a workspace on disk (root manifest plus N member trees), then tests that fail
against the not-yet-existing modules:

- valid manifest loads and yields members in declared order with resolvable
  absolute paths
- bad member names are rejected: `Pybusiness` (uppercase), `pkg/lib` (slash),
  `a::b` (double colon), `""` (empty)
- duplicate member names in the YAML file are rejected with the name in the
  message
- a member path that does not exist, and one that exists but holds no VE tree,
  are reported by filesystem validation
- a pointer-only tree (`docs/chunks/x/external.yaml`, no `docs/trunk/`)
  validates as a member
- nested members round-trip through save/load, and `find_member_for_path`
  returns the innermost one
- absolute and `..`-escaping member paths are rejected
- `find_workspace_root` finds the manifest from a nested subdirectory and
  returns None when there is none
- scan finds trees with `docs/trunk/` (including nested ones), skips `.git` and
  `.venv`, and honors an `--exclude` glob that drops a cookiecutter template
  tree
- scan name suggestions collide-and-disambiguate when two trees share a
  directory name

### Step 2: `src/models/workspace.py`

`MEMBER_NAME_PATTERN = re.compile(r"^[a-z0-9_-]+$")` and a
`_validate_member_name` helper whose message names the grammar and calls out
`/` and `::` explicitly (those are what make a member name ambiguous against an
`org/repo` qualifier in the shared `::` syntax).

`WorkspaceMember(name, path)`: validates the name grammar; normalizes the path
to a relative POSIX string, rejecting absolute paths and any path that escapes
the workspace root via `..`.

`WorkspaceManifest(members: list[WorkspaceMember])`: a `mode="before"`
validator accepts the on-disk mapping form (`{name: path}`) and converts it to
the list form, preserving declaration order; a field validator rejects
duplicate names. Helpers: `get(name)`, `names()`, `to_mapping()`.

Re-export both plus `MEMBER_NAME_PATTERN` from `src/models/__init__.py`.

### Step 3: `src/workspace.py`

- `WORKSPACE_MANIFEST_NAME = ".ve-workspace.yaml"`
- `WorkspaceError`, `WorkspaceNotFoundError`, `WorkspaceManifestError`
- `_UniqueKeyLoader(yaml.SafeLoader)` raising on duplicate mapping keys
- `find_workspace_root(start)` — walk up from `start` (inclusive) for the
  manifest; return None if none found
- `Workspace` dataclass (`root`, `manifest`) with `resolve(name) -> Path`,
  `member_paths()`, `find_member_for_path(path)` (longest-prefix)
- `load_workspace(start)` — discover root, parse, validate shape; raises
  `WorkspaceNotFoundError` with a message naming the file and suggesting
  `ve workspace init`
- `save_workspace(workspace)` / `write_manifest(root, manifest)`
- `is_ve_tree(path)` (permissive) and `has_trunk(path)` (scan predicate)
- `validate_member_paths(workspace) -> list[str]` — one message per defect
- `scan_for_trees(root, exclude=())` — walk skipping `.git`, `.venv`,
  `node_modules`, `__pycache__`, `.claude/worktrees`; return root-relative
  sorted paths of directories with `docs/trunk/`, honoring `fnmatch` excludes
- `suggest_member_names(rel_paths)` — directory name lowercased with
  out-of-grammar characters replaced by `_`, disambiguated against collisions
  by prefixing the parent component, then a numeric suffix

Module-level and function-level `# Chunk:
docs/chunks/federation_workspace_manifest` backreferences throughout.

### Step 4: `src/cli/workspace.py`

`@click.group() workspace`, all commands taking
`--workspace-dir` (default `.`) — deliberately *not* `--project-dir`, which is
being reworked concurrently by `federation_tree_discovery` and means something
different (a single tree, not the workspace).

- `list` — prints `name  path` aligned, marking any member whose path is not a
  VE tree with ` [missing]`; exits 1 with a clear message when no manifest
  exists anywhere above the directory
- `add NAME PATH` — validates grammar, rejects duplicates, requires the path to
  exist and hold a VE tree, appends, writes, confirms
- `init [--scan] [--exclude GLOB]... [-y]` — refuses to overwrite an existing
  manifest; without `--scan` writes an empty manifest; with `--scan` prints
  numbered candidates with suggested names, tells the operator how to drop junk
  with `--exclude`, then asks for one confirmation before writing (`-y` skips
  the prompt)

### Step 5: CLI tests

Extend the test module with `CliRunner` tests: `list` on a good workspace and
its nonzero exit with no manifest; `add` happy path plus duplicate, bad-name,
missing-path, and not-a-tree rejections (each nonzero, manifest unchanged);
`init --scan` with a declined prompt (nothing written), with `-y`, and with
`--exclude` dropping the cookiecutter template tree.

### Step 6: Register and verify

Add the import and `add_command` lines to `src/cli/__init__.py`, run
`uv run pytest tests/`, and confirm `uv run ve workspace --help` lists the
three commands.

## Risks and Open Questions

- **Predicate divergence.** `federation_tree_discovery` (same wave) defines
  nearest-enclosing-tree discovery in `src/project.py` around `docs/trunk/`.
  This chunk deliberately keeps a more permissive membership predicate, so two
  notions of "is a VE tree" will briefly coexist. Consolidating them belongs to
  `federation_global_validator`, which is the first consumer of both; flag it as
  a handoff rather than reaching into `src/project.py` here.
- **Member name grammar allows leading `-`.** The GOAL states the grammar as
  `[a-z0-9_-]+`, which admits `-foo`. Implemented as specified; a leading-dash
  member name would be awkward as a future CLI argument. Noted, not
  pre-emptively narrowed.
- **Scan on a large monorepo.** A full walk of a 29-tree repository must not
  descend into `.git`, `node_modules`, or `.venv`, or the scan becomes slow
  enough to look broken. Pruning is part of Step 3, not an optimization.

## Deviations

- **Step 3 gained `add_member` and `relativize_to_workspace`.** The plan put
  duplicate/existence/tree checks in the CLI. They moved into `src/workspace.py`
  so the same guarantees hold for any future non-CLI caller (the validator and
  the fix-loop skill both need to register a member), leaving
  `src/cli/workspace.py` as pure argument handling and output.

- **README.md added to the files touched.** Not listed at planning time; DEC-003
  requires operator-facing commands to be documented in the README, and
  `ve workspace` is operator-facing. Added a "Monorepos With Multiple Trees"
  section beside the existing cross-repository section.

- **Scan pruning changed from an allowlist of junk names to "skip all hidden
  directories".** Discovered during review by scanning the vibe-engineer repo
  itself: the original skip list proposed nine phantom trees, because VE keeps
  worktree checkouts under `.claude/worktrees/` and `.ve/chunks/*/worktree`,
  each a full copy of the repo's own tree. The same tree offered under five
  paths is exactly the confusion this chunk exists to remove, so the rule became
  categorical (a VE tree inside a hidden directory is never an intentional
  member) plus a short list of non-hidden build/vendor directories. Covered by
  `test_scan_skips_worktree_checkouts_of_the_same_repo`.

- **`ve workspace list` distinguishes two defect markers** (`path does not
  exist` vs `no VE tree at this path`) rather than the single marker planned.
  The two have different fixes — re-point the member versus initialize the tree
  — so collapsing them would have made the output less actionable.
