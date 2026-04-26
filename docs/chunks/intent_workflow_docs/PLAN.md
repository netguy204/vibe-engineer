# Implementation Plan

## Approach

This is a documentation-only sweep. Every file touched is either a Jinja2 template
or a Markdown document. The strategy is:

1. **Reference, don't restate.** Where docs currently describe chunks, add a
   cross-reference to `docs/trunk/CHUNKS.md` (the canonical source, landed by
   `intent_principles`) and adjust the surrounding prose so it frames chunks as
   the artifact for *intent-bearing* work rather than the default mechanism for
   *all* work.

2. **Minimal-diff edits.** Each file gets the smallest edit that corrects the
   framing. We are not rewriting sections wholesale — just qualifying language
   and adding references.

3. **Twin templates stay in sync.** `CLAUDE.md.jinja2` and `AGENTS.md.jinja2`
   are near-identical templates for different agent surfaces. Every edit to one
   is mirrored in the other.

4. **Render and verify.** After template edits, `uv run ve init` re-renders
   output files. `uv run pytest tests/` confirms nothing broke.

No test changes are expected — this chunk touches only prose and template content,
not runtime behavior.

## Dependencies

- `intent_principles` must have landed `docs/trunk/CHUNKS.md` and the
  cross-reference in `docs/trunk/ARTIFACTS.md`. Both are confirmed present in
  the worktree.

## Sequence

### Step 1: Update `src/templates/claude/CLAUDE.md.jinja2` — Chunks section header

**Location:** `src/templates/claude/CLAUDE.md.jinja2`, lines 22–30

The current text reads:

> Work is organized into "chunks" - discrete units of implementation stored in `docs/chunks/`.

Replace with language that frames chunks as the artifact for intent-bearing work
and references CHUNKS.md principle 2. Add a brief note on when *not* to create a
chunk (typo fixes, dep bumps, mechanical renames). Something like:

> Work that carries architectural intent is organized into "chunks" — discrete
> units of intent stored in `docs/chunks/`. Before creating a chunk, read
> [docs/trunk/CHUNKS.md](docs/trunk/CHUNKS.md) — especially principle 2.
> Intent-less work (typo fixes, dependency bumps, mechanical renames) bypasses
> the chunk system entirely.

Keep the existing bullet list of GOAL.md / PLAN.md and the `ve chunk list`
guidance that follows.

### Step 2: Update `src/templates/claude/CLAUDE.md.jinja2` — Getting Started section

**Location:** `src/templates/claude/CLAUDE.md.jinja2`, line 190

Current text:

> 3. Use `/chunk-create` to start new work

Qualify to:

> 3. Use `/chunk-create` to start new intent-bearing work (see `docs/trunk/CHUNKS.md` principle 2)

### Step 3: Update `src/templates/claude/CLAUDE.md.jinja2` — Available Commands `/chunk-create` line

**Location:** `src/templates/claude/CLAUDE.md.jinja2`, line 116

Current text:

> - `/chunk-create` - Create a new chunk and refine its goal

Qualify to:

> - `/chunk-create` - Create a new chunk for intent-bearing work and refine its goal

### Step 4: Mirror all Step 1–3 edits in `src/templates/claude/AGENTS.md.jinja2`

`AGENTS.md.jinja2` is a near-twin of `CLAUDE.md.jinja2`. Apply identical edits
at the same locations. Verify the two templates remain in sync by diffing
corresponding sections.

### Step 5: Update `src/templates/commands/chunk-create.md.jinja2` — frontmatter description

**Location:** `src/templates/commands/chunk-create.md.jinja2`, line 3

Current `description`:

> Create a new chunk of work and refine its goal. Use when the operator wants to start new work, chunk something, define a piece of work, or break work into a chunk.

Replace with:

> Create a new chunk of work and refine its goal. Use when the operator wants to start new intent-bearing work, chunk something, define a piece of work, or break work into a chunk.

This is the skill description that Claude uses for matching — it should signal
that chunks are for intent-bearing work, not all work.

### Step 6: Update `docs/trunk/ARTIFACTS.md` — chunk framing

**Location:** `docs/trunk/ARTIFACTS.md`

The file already has a cross-reference to CHUNKS.md on line 5 (added by
`intent_principles`). Two additional items:

a. In the "Choosing between artifacts" table (around line 57), the Chunk row
   currently reads "Know what needs to be done". Qualify to something like
   "Know what intent-bearing work needs to be done" or "Clear intent to
   capture (see CHUNKS.md principle 2)".

b. In the Code Backreferences section (line 138), the `# Chunk:` row says
   "Until SUPERSEDED/HISTORICAL". Update to "Until HISTORICAL" since
   SUPERSEDED has been retired from the taxonomy by `intent_principles`.

### Step 7: Update `README.md` — Working in Chunks section

**Location:** `README.md`, around line 69–71

Current text:

> Chunks are the units of change in the Vibe Engineering workflow. You don't
> have to edit your code using chunks, but if you do then you get the value of
> agent maintained documentation "for free".

This is the most prominent "chunks for everything" framing in the project. The
second sentence already hedges ("You don't have to"), but the first sentence
frames chunks as "units of change" which implies all change flows through them.

Reframe the opening to emphasize intent-bearing work. Something like:

> Chunks capture the *intent* behind your code — the constraints, contracts, and
> boundaries that should outlive any particular implementation. Not every change
> needs a chunk; typo fixes, dependency bumps, and mechanical renames bypass the
> chunk system entirely. The test: *does this code need to remember why it
> exists?* If yes, make a chunk. See `docs/trunk/CHUNKS.md` for the full
> principles.

Keep the existing CLI example and slash-command table that follows.

### Step 8: Render and verify

Run:

```bash
uv run ve init
```

Confirm it completes cleanly. Spot-check that `CLAUDE.md` in the project root
reflects the template changes from Steps 1–3.

### Step 9: Run tests

```bash
uv run pytest tests/
```

No test changes are expected. If any tests break, investigate — the failure
would indicate either a template rendering issue or an unexpected downstream
effect.

## Risks and Open Questions

- **README.md tone:** The README is operator-facing prose, not agent
  instructions. The rewrite in Step 7 should stay conversational and inviting,
  not bureaucratic. The exact wording is a suggestion — match the existing
  README's voice.

- **AGENTS.md.jinja2 drift:** If `AGENTS.md.jinja2` has diverged from
  `CLAUDE.md.jinja2` in ways not visible from the current read, Step 4 may
  need adjustment. Diff the two templates before editing.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->