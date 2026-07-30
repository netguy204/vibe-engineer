# Implementation Plan

## Approach

Three pieces, in dependency order: a pure discovery helper, a single wiring
point that applies it to every CLI command, and the documented rule in the
CLAUDE.md template.

**1. Discovery helper (`src/project.py`, module level).** `find_enclosing_tree(
start) -> Path | None` walks `start` (its parent, if `start` is a file) and
each ancestor looking for a directory containing `docs/trunk/`. At each level
the order is: *is this a tree? → return it*; *is this a boundary? → stop*;
else go up. Boundaries are `.ve-workspace.yaml` (per the GOAL — existence
check by filename only; parsing belongs to `federation_workspace_manifest`),
`.ve-task.yaml` (a task directory is a different addressing regime — see
Risks), and the filesystem root. Checking "tree" before "boundary" means a
workspace root that is itself a tree still resolves to itself.

A second helper, `resolve_project_dir(start) -> TreeResolution`, is what the
CLI consumes: it returns the directory commands should use plus enough context
to report the choice. Its contract is the backward-compatibility guarantee:

- `start` is a tree → use `start` (the single-tree case; no notice, no change).
- `start` is not a tree but an ancestor is → use the ancestor, `redirected=True`.
- no enclosing tree at all → use `start` unchanged (today's behavior; the
  command then fails or succeeds exactly as it does now).

The third case is why this is safe to apply broadly: discovery never invents a
failure, it only replaces a directory that could not have worked with one that
can. This mirrors the existing upward-walk precedents `find_task_directory`
(`src/task/config.py:241`) and `resolve_project_root` (`src/board/storage.py:126`),
and follows the same "walk while `current != current.parent`, then test the
root" shape.

**2. CLI wiring (new `src/cli/tree_discovery.py`, 3 lines in `src/cli/__init__.py`).**
There are 88 `--project-dir` declarations across 13 modules. Editing each one
to add a `callback=` would be an 88-site diff in files a concurrent chunk may
also touch, and every new command would have to remember the callback. Instead,
one installer walks the assembled command tree once at import time and attaches
the discovery callback to every parameter named `project_dir`, with an explicit
exemption set. `init` is exempt because it *creates* a tree — walking up from a
directory that has no `docs/trunk/` is precisely what `ve init` must not do.
`None` values pass through untouched, so the 27 `ve orch` declarations that
default to `None` keep their own `resolve_orch_project_dir` semantics.

**3. The rule (`src/templates/claude/CLAUDE.md.jinja2` + `AGENTS.md.jinja2`).**
A subsection under "Code Backreferences" stating that a bare `# Chunk:` /
`# Narrative:` / `# Subsystem:` reference resolves against the nearest
enclosing tree *of the file containing it* — never the cwd, never the repo
root. The GOAL names `CLAUDE.md.jinja2`; the two templates are byte-identical
except for one comment line and `_init_agents_md` actually renders
`AGENTS.md.jinja2`, so both get the edit or the repo's own re-rendered
`AGENTS.md` would silently lack the rule.

Testing follows TESTING_PHILOSOPHY's boundary emphasis: the discovery helper is
pure and filesystem-driven, so it gets direct unit tests over a nested-tree
fixture, and the CLI behavior gets end-to-end `CliRunner` tests that assert the
*observable* consequence (which tree's chunks got listed), not that a callback
was installed.

## Subsystem Considerations

No existing subsystem covers project-directory resolution.
`docs/subsystems/workflow_artifacts` (DOCUMENTED) governs the artifact managers
that receive `project_dir`, but this chunk does not change how they use it — it
changes what value they are handed. No subsystem edits; a
resolution/addressing subsystem may be worth discovering once the later
federation chunks (qualified refs, global validator) land their own share of
this logic.

## Sequence

### Step 1: Failing tests for the discovery helper

Create `tests/test_tree_discovery.py` with a nested-tree fixture built by hand
(`mkdir docs/trunk`) rather than a conftest helper, because the existing
`make_ve_initialized_git_repo` deliberately creates `docs/chunks/` and friends
*without* `docs/trunk/`:

```
root/            docs/trunk/          <- outer tree
root/mid/                             <- between the trees
root/mid/inner/  docs/trunk/          <- inner tree
root/mid/inner/pkg/src/               <- deep inside the inner tree
```

Assertions (each traceable to a success criterion):
- a file in the inner tree resolves to the inner tree (GOAL: nested fixture)
- a directory between the two resolves to the outer tree (GOAL: nested fixture)
- a tree resolves to itself
- a directory with no tree above it returns `None` (stops at filesystem root)
- a `.ve-workspace.yaml` ancestor stops the walk before a tree *above* it
- a workspace root that is itself a tree still resolves to itself
- a `.ve-task.yaml` boundary stops the walk
- passing a file path starts from its parent

### Step 2: Implement `find_enclosing_tree` and `resolve_project_dir`

In `src/project.py`, module level, above the `Project` class: the marker
constants, `is_ve_tree`, `find_enclosing_tree`, the frozen `TreeResolution`
dataclass, and `resolve_project_dir`. Backreference each with
`# Chunk: docs/chunks/federation_tree_discovery`. Step 1's tests go green.

### Step 3: Failing CLI tests for redirected resolution

Add to `tests/test_tree_discovery.py` a class of `CliRunner` tests:
- `ve chunk list --project-dir <inner>/pkg/src` lists the *inner* tree's chunks
  and not the outer tree's (the criterion that matters: no silent misrouting)
- the same invocation emits one line naming the selected tree
- `ve chunk list --project-dir <inner>` (already a tree) emits no such line —
  the single-tree no-change guarantee
- `ve init --project-dir <root>/mid/fresh` initializes *that* directory and
  does not touch the enclosing tree (the exemption)
- a directory with no enclosing tree behaves exactly as before

### Step 4: Implement the installer

New `src/cli/tree_discovery.py`: the click callback (skip `None`; call
`resolve_project_dir`; echo the one-line notice to stderr when `redirected`;
return the resolved path) and `install_tree_discovery(group, exempt)` which
recurses through `group.commands`, composes with any pre-existing param
callback rather than clobbering it, and is idempotent (marks params it has
already wrapped, so a re-import or a second call cannot double-wrap). Wire it
at the bottom of `src/cli/__init__.py` after the last `add_command`.

### Step 5: Document the rule in the templates

Edit both `src/templates/claude/CLAUDE.md.jinja2` and
`AGENTS.md.jinja2` (identical managed content). Re-render with
`uv run ve init`, confirm the repo's own `AGENTS.md` picks the rule up inside
the `VE:MANAGED` markers and that the diff contains nothing else.

### Step 6: Full suite, then GOAL bookkeeping

Run `uv run pytest tests/` against the captured baseline. Populate
`code_paths` and `code_references` in the chunk's GOAL.md.

## Dependencies

None. `federation_workspace_manifest` (same wave) will define the
`.ve-workspace.yaml` format; this chunk only tests the filename's existence, so
the two do not need to be ordered.

## Risks and Open Questions

- **Task directories are a parallel addressing regime.** Commands route on
  `is_task_directory(project_dir)` and test fixtures pass task dirs as
  `--project-dir`. Silently rewriting such a value would break cross-repo
  routing, so `.ve-task.yaml` is a hard stop in the walk. Verified by the full
  suite (`tests/test_task_cli_context.py` and friends).
- **`docs/trunk/` as the sole tree marker.** Pointer-only trees (the shape
  `federation_template_pointers` will introduce: `external.yaml` edges, no
  trunk) will not be discoverable by this marker. Recorded as a handoff rather
  than guessed at here; the marker set is a module constant so a later chunk
  can extend it deliberately.
- **Installing callbacks by walking the command tree is indirect.** Someone
  reading a `@click.option("--project-dir", ...)` line will not see the
  discovery behavior there. Mitigated by the module docstring, the exemption
  set being explicit, and a test that asserts a representative command actually
  resolves — but it is a real legibility cost, taken to keep the diff small
  during a parallel wave.
- **Notice channel.** stderr keeps it out of `--json` payloads and out of
  stdout-parsing callers, and matches how the CLI already emits warnings
  (`warn_task_project_context`). Click 8.3's `CliRunner` separates streams, so
  tests must read `result.stderr`; confirm that during Step 3.

## Deviations

- **Step 5 (re-render).** `uv run ve init` verified the template edit but also
  ran the legacy-layout migration, deleting 68 tracked files under
  `.agents/skills/` and `.claude/commands/`, and rewrote `AGENTS.md` wholesale —
  importing pre-existing template drift unrelated to this chunk. All of that was
  reverted (`git checkout -- .agents .claude AGENTS.md`) and only the new
  section was applied to the rendered `AGENTS.md` by hand. The applied text was
  then verified byte-identical to a fresh render into a scratch project, so the
  rendered file is in sync for this change without carrying anyone else's drift
  into a parallel wave.

- **Path identity, not path equality.** The first cut resolved paths with
  `Path.resolve()`, which made two spellings of one directory look like a
  redirect (macOS `/var` vs `/private/var`, and a relative `"."` vs its absolute
  form) — every single-tree command would have printed a spurious notice.
  Resolution now walks on `os.path.abspath` and compares with a
  `_same_directory` helper over realpaths, and returns the caller's value
  verbatim when it already names the tree.

- **Extra tests beyond the planned sequence.** Added `TestInstaller`, which
  asserts that exactly one `project_dir` parameter (`init`) lacks discovery and
  that re-installing does not double-wrap callbacks. The installer is the
  load-bearing wiring, and it is invisible at the option declarations, so its
  contract is worth pinning down directly.

- **`code_references` omits module constants.** `TREE_MARKERS`,
  `BOUNDARY_MARKERS`, and `EXEMPT_COMMANDS` were listed first, but the symbol
  resolver indexes functions and classes only and reported them as unresolvable.
  Their meaning was folded into the descriptions of the functions that read
  them.
