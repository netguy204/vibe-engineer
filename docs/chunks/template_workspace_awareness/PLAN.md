

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Thread a single boolean — "does this project sit in a workspace?" — from
`Project._init_agents_md` through `TemplateContext` into the `claude`
template collection, and gate every piece of workspace-aware content on it
with Jinja2 whitespace control chosen so that the `False` branch renders
byte-for-byte what the template renders today.

Three moving parts:

1. **Context**: `TemplateContext` gains an `in_workspace: bool = False`
   field. Because `as_dict()` exposes the context as `project`, templates
   read it as `project.in_workspace`. The default keeps every other call
   site (`_init_trunk`, `_init_reviewers`, plugin render, tests) unchanged.

2. **Detection**: `Project._init_agents_md` calls
   `find_workspace_root(self.project_dir)` (already imported in
   `src/project.py` from `src/workspace.py`) and sets
   `in_workspace=result is not None`. A tree that *is* the workspace root
   also gets `True` — the manifest governs it too.

3. **Template**: `src/templates/claude/AGENTS.md.jinja2` (and its
   near-duplicate `CLAUDE.md.jinja2`, kept in lockstep) gains:
   - a `### Working Across VE Trees in This Workspace` section inserted
     after "Resolving a Backreference: Nearest Enclosing Tree" (whose last
     line — "references that cross a tree boundary must say so explicitly"
     — it completes), genericized from the field-written raw material,
     with subsections for: the member-qualified `member::docs/...` form,
     peer pointers (`ve external point`, `tree:` vs `repo:`) with the
     1-reader-qualify / 2+-readers-pointer rule preserved in spirit
     verbatim, `ve workspace validate` over `ve validate`,
     `code_references` (with `#Symbol::method` anchors and `implements:`
     prose) preferred over legacy `code_paths`, and `ve deletion record` /
     `docs/trunk/DELETIONS.md` for gone-target references.
   - the rename-mandate fix (highest priority): the "File Moves and
     Renames" bash block prescribes
     `uvx --from vibe-engineer ve workspace validate` when
     `project.in_workspace`, with a short paragraph explaining why the
     single-tree validator must not be run at a workspace root.

**Byte-identity technique**: conditional blocks use `{%- if ... %}` /
`{%- endif %}` so the skipped branch leaves no whitespace residue; the
in-block command swap uses an inline
`{% if %}...{% else %}...{% endif %}` on the command line itself. The new
chunk backreference comment uses `-#}` so it emits nothing. This is pinned
by golden-fixture tests: the exact bytes of today's render (captured from
the pre-change template) are checked into `tests/fixtures/` and the
single-tree render is asserted equal to them.

Testing follows docs/trunk/TESTING_PHILOSOPHY.md: template-level tests in
`tests/test_template_system.py` (golden pin + workspace-content
assertions), integration tests in `tests/test_project.py` (`ve init`
inside/outside a manifest-bearing directory).

## Subsystem Considerations

- **docs/subsystems/template_system** (status: see subsystem doc): this
  chunk USES the unified template rendering subsystem —
  `TemplateContext` + `render_template` — and extends the context dataclass
  in the pattern already established (optional fields with inert
  defaults). No deviations discovered.

## Sequence

### Step 1: Capture golden fixtures of today's renders

Before touching the template, render `claude/AGENTS.md.jinja2` and
`claude/CLAUDE.md.jinja2` with a default `TemplateContext` and check the
exact output into `tests/fixtures/agents_md_single_tree.md` and
`tests/fixtures/claude_md_single_tree.md`. These are the byte-identity
regression targets.

### Step 2: Add `in_workspace` to TemplateContext

`src/template_system.py`: add `in_workspace: bool = False` to the
`TemplateContext` dataclass with a docstring note that the AGENTS.md
template keys workspace-aware content off it. No change to `as_dict()` or
`render_template` signatures is needed — the field rides through
`project.in_workspace`.

### Step 3: Detect the workspace in Project._init_agents_md

`src/project.py`: in `_init_agents_md`, build the context as
`TemplateContext(in_workspace=find_workspace_root(self.project_dir) is not None)`.
Add a chunk backreference comment.

### Step 4: Make the templates workspace-aware

Edit `src/templates/claude/AGENTS.md.jinja2` and mirror the same edits in
`CLAUDE.md.jinja2`:

- Insert the workspace section (see Approach) between the
  Nearest-Enclosing-Tree section and "File Moves and Renames", wrapped in
  `{%- if project.in_workspace %}` … `{%- endif %}`.
- Swap the rename-mandate command inline:
  `{% if project.in_workspace %}uvx --from vibe-engineer ve workspace validate{% else %}uvx --from vibe-engineer ve validate{% endif %}`,
  plus a conditional explanatory paragraph after the code block.
- Genericize the raw material: no tree counts, no CI job names, no
  reporter package names; command syntax verified against the current CLI
  (`ve external point MEMBER ARTIFACT --why`, `ve deletion record
  REFERENCE --location --by --reason --evidence`, `ve workspace list`,
  `ve workspace validate`, `ve exists`).

### Step 5: Template-level tests

`tests/test_template_system.py`, new test class:

- single-tree render (default context, and explicit
  `in_workspace=False`) is byte-identical to the golden fixtures — both
  templates;
- workspace render prescribes `uvx --from vibe-engineer ve workspace
  validate` in the rename mandate and does not prescribe the single-tree
  command;
- workspace render demonstrates the qualified `member::docs/...` form and
  points at `ve workspace list`;
- workspace render documents `ve external point`, `tree:` vs `repo:`, and
  states the 1-reader-qualify / 2+-readers-pointer rule;
- workspace render prefers `code_references` with `#Symbol::method` /
  `implements:` over `code_paths`;
- workspace render points at `ve deletion record` and
  `docs/trunk/DELETIONS.md`;
- single-tree render contains none of the workspace-only content;
- `TemplateContext()` defaults `in_workspace` to `False`.

### Step 6: Integration tests through ve init

`tests/test_project.py`:

- `init()` in a plain temp dir produces an AGENTS.md whose content equals
  the golden fixture (full-file byte pin through the real code path);
- `init()` in a project directory that sits under (or at) a
  `.ve-workspace.yaml` produces an AGENTS.md containing the workspace
  section and the workspace-validate mandate.

### Step 7: Full test run and validation

`uv run pytest tests/` and `uv run ve validate` both clean. Update the
chunk GOAL.md `code_references` at completion time.

## Dependencies

None beyond code already merged: `find_workspace_root`
(`src/workspace.py`) and the `ve workspace` / `ve external` / `ve
deletion` CLI surfaces shipped in 0.4.0.

## Risks and Open Questions

- Jinja2 whitespace control is fiddly; the golden-fixture pin is the
  guard. If a `{%-` strips one newline too many the test fails loudly.
- `CLAUDE.md.jinja2` is not rendered by `Project._init_agents_md` (which
  renders `AGENTS.md.jinja2` only) but is kept in lockstep so the two
  templates cannot drift apart in meaning.
- The golden fixtures pin *today's* bytes; future intentional template
  changes must regenerate them deliberately. The fixture test docstring
  says so.

## Deviations

- Step 2 claimed `render_template` needed no change because the field would
  "ride through" the context. Wrong for call sites that pass `context=None`
  (three existing tests and any future caller): Jinja2's default `Undefined`
  raises on `project.in_workspace` attribute access. `render_template` now
  substitutes a default `TemplateContext()` when no context is given, so
  templates can test `project.in_workspace` unguarded. `kwargs` still
  override the context dict, so no call site changed behavior — pinned by
  `test_single_tree_render_without_context_matches_golden`.
