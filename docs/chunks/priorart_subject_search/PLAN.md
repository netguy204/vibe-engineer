# Implementation Plan

## Approach

The directive is a single sentence appended to an existing line of the
VE-managed block. It adds no heading, no conditional branch, and no new
template variable, so the whole change is two edits to one template plus a
re-render.

The rendered `AGENTS.md` and the `CLAUDE.md` symlink are outputs. The edit lands
in the template; `ve init` regenerates the managed block in place.

## Trap Encountered, Then Removed

While implementing this chunk, `src/templates/claude/` held **two** templates —
`AGENTS.md.jinja2` and `CLAUDE.md.jinja2` — and only the first was live. Since
`agentskills_migration` made AGENTS.md canonical and CLAUDE.md a symlink to it,
`Project._init_claude_md` renders `AGENTS.md.jinja2`; nothing in `src/` read
`CLAUDE.md.jinja2`. Editing the dead one produced a `ve init` run reporting
"Updated the VE-managed block in AGENTS.md in place" while changing nothing.

The editor was sent there by this repository's own `AGENTS.md` table, below the
END marker, which still named `src/templates/claude/CLAUDE.md.jinja2` as the
source of `CLAUDE.md`. A stale documented pointer, trusted instead of checked —
the same shape as the failure this chunk's directive exists to prevent.

Both are now fixed as intent-less follow-on cleanup, so a future reader will not
find the trap described here still present:

- `src/templates/claude/CLAUDE.md.jinja2` and its golden fixture
  `tests/fixtures/claude_md_single_tree.md` are deleted.
- 50 `code_paths` / `code_references` entries across 46 chunks were retargeted
  onto `AGENTS.md.jinja2` with `ve refactor move` (0 ambiguous, git-rename
  evidence per entry).
- Six reference removals that `ve refactor move` could not carry — two naming
  the deleted fixture, four whose `implements:` described the deleted template
  as a "lockstep mirror" and would otherwise assert that `AGENTS.md.jinja2`
  mirrors itself — are recorded as grants D001–D006 in `docs/trunk/DELETIONS.md`.
- The two tests pinning the dead template (`test_single_tree_claude_md_...` and
  the templates-stay-in-lockstep test) are removed, with a comment at the
  latter's site saying why the coupling no longer exists.
- The `AGENTS.md` table now names `AGENTS.md.jinja2`, states that `CLAUDE.md` is
  a symlink rather than a render, and gives the re-render command per row
  (`ve init` vs `ve plugin render` — the old table's second row was stale too,
  naming a `src/templates/commands/` directory that does not exist).

## Sequence

### Step 1: Add the chunk backreference to the live template

Append `{# Chunk: docs/chunks/priorart_subject_search - ... #}` to the header
comment block of `src/templates/claude/AGENTS.md.jinja2`, matching the existing
per-chunk comments there. The `-#}` whitespace-control marker moves to the new
last line so the rendered output is unchanged.

### Step 2: Append the directive

Extend the `Read GOAL.md first ...` line in the Project Documentation section
with the agreed sentence. Keep it on one physical line: the surrounding
paragraphs in that section are unwrapped, and wrapping only begins further down
the template.

### Step 3: Re-render and verify

```bash
uv run ve init
git diff AGENTS.md
```

`ve init` emits `Discarded 1 line(s) from the VE-managed block`. This is
expected on **any** edit to a managed line: the discard check compares sets of
lines, so a replaced line reports as discarded. Confirm via `git diff` that the
only change is the intended one line — the warning is not evidence of lost
content, and the diff is what settles it.

### Step 4: Validate

```bash
uv run ve validate
```

Must exit zero. Pre-existing warnings about `crossref_rename_integrity` are
unrelated to this chunk and are not introduced by it.

## Testing

There is no behavioral code to test. Verification is the rendered artifact:

- `git diff AGENTS.md` shows exactly one changed line.
- The rendered sentence is byte-identical whether or not
  `project.in_workspace` is true, since the edit sits outside every
  `{%- if project.in_workspace %}` guard.
- `uv run ve validate` exits zero.

Per `docs/trunk/TESTING_PHILOSOPHY.md`, template-content changes of this shape
are verified by the rendered output rather than by a unit test asserting on
prose, which would only restate the template and would fail on every future
wording change.

## Dependencies

None. The edit touches one template that no other in-flight chunk modifies.

## Risks and Open Questions

**A future editor re-narrows the search scope.** The most likely regression is
someone "tightening" `grep the whole repository` back to `docs/`, which
reintroduces the false-empty failure. The GOAL's Rejected Ideas section exists
to catch this and names the consequence directly.

**The directive names grep rather than a command.** If a docs-search subcommand
is built, this sentence should be revised to invoke it, which would also remove
the need to enumerate directories. Recorded in Rejected Ideas.

**The directive is necessary, not sufficient.** A dangling `external.yaml`
pointing at a never-committed cross-repository target can absorb a correct
search and close the question harder than an empty result. See the GOAL's Known
Limit section. Out of scope here.
