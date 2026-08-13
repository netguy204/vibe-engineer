

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a prose-guidance change to the workspace-validate-fix skill, delivered
through the build-time plugin template collection: edit
`src/templates/plugin/skills/workspace-validate-fix.md.jinja2`, re-render with
`uv run ve plugin render`, and commit both the template and the regenerated
`skills/workspace-validate-fix/SKILL.md`. The drift test
(`tests/test_plugin_render.py`) enforces that the committed render stays in
lockstep with the template, so no new test code is needed — per
docs/trunk/TESTING_PHILOSOPHY.md, a string-presence assertion on skill prose
would be a trivial test with no behavioral signal.

**The trap being closed.** The skill's Invariants already say "Never delete a
reference," but the field failure (4 rows in the Cloud Capital archaeology)
shows agents route around that invariant with a specific rationalization:
"this tree already holds an `external.yaml` peer pointer covering the chunk,
so this backreference is redundant — removing it is deduplication, not
deletion." That reasoning is wrong because the pointer and the backreference
record different facts. The pointer records a tree-level interest edge, and a
chunk's own `code_references` typically name only its public surface. A
backreference on a private helper is frequently the *only* record anywhere
binding that helper to its governing intent. Deleting it because the pointer
"covers" the chunk silently drops that intent, and no validator ever reports
the loss — a resolving reference that gets deleted was never a defect row.

**The fix.** Two edits to the skill template, both prose:

1. Extend the **"Never delete a reference"** invariant bullet to name the
   pointer-coverage rationalization explicitly: pointer coverage is never
   grounds for deletion, and "redundant with the pointer" is not a fix class.
2. Add a short named callout in the `misrouted-bare` section (immediately
   after the "Two or more → create the interest edge... leave the references
   bare" branch, where an agent is most likely to be holding both the pointer
   and the references in mind) explaining what the pointer does and does not
   replace, and saying what to do instead: a peer pointer is what makes bare
   references *resolve*; the references themselves stay. A reference that
   resolves through a pointer is correct and finished — not a cleanup
   candidate. If a reference is broken, work its fix class; if the only
   remaining move appears to be deletion, that is an escalation.

The deletion-disposition machinery (an operator-authorized way to *record* a
sanctioned deletion) belongs to the sibling chunk `crossref_absence_evidence`
and is out of scope here; this chunk only closes the rationalization that
bypasses escalation.

## Sequence

### Step 1: Extend the "Never delete a reference" invariant

In `src/templates/plugin/skills/workspace-validate-fix.md.jinja2`, expand the
first Invariants bullet so it explicitly forecloses pointer coverage as a
deletion license. Keep the existing sentence structure; append the guard:
peer-pointer coverage of the artifact is never grounds for removing a
reference — the pointer records the tree's dependency and the chunk's
`code_references` typically name only its public surface, so a backreference
on a private helper may be the only record tying that code to its intent.

### Step 2: Add the pointer-coverage callout in `misrouted-bare`

In the same template's `misrouted-bare` section, after the qualify-or-point
decision (and near the existing "Is the candidate the owner, or another
reader?" callout style), add a bolded callout — **"Does the pointer make the
references redundant?"** — stating:

- No. The pointer is the resolution mechanism for bare references, not a
  replacement for them. Creating a pointer and deleting the references it
  serves would defeat the fix just applied.
- What the two records mean: pointer = tree-level interest edge over the
  chunk's public surface; per-symbol backreference = which code the intent
  governs, and for private helpers usually the only such record.
- What to do instead: leave resolving references alone (they are finished,
  not redundant); work broken references through their fix class; escalate
  when deletion seems like the only remaining move.

### Step 3: Re-render the plugin collection

Run `uv run ve plugin render` and verify `skills/workspace-validate-fix/SKILL.md`
picked up the new prose and nothing else changed.

### Step 4: Verify

- `uv run pytest tests/test_plugin_render.py -q` — drift test green.
- `uv run pytest tests/ -q` — full suite matches the pre-change baseline.
- `uv run ve validate` — clean.

### Step 5: Update chunk metadata

Fill `code_paths` in this chunk's GOAL.md (done at planning time) and, at
completion, `code_references` for the template file.

## Risks and Open Questions

- The guidance must not overcorrect into "references may never be touched":
  the skill's edit vocabulary (qualify, normalize, retarget, register,
  correct a path) still applies. The callout is scoped to *deletion* only.
- Wording must not collide with `crossref_absence_evidence`'s future
  operator-authorized deletion disposition; phrasing deletion as "an
  escalation, not a fix" (the invariant's existing frame) keeps the seam
  clean — that chunk can later define what an *authorized* deletion looks
  like without contradicting this text.

## Deviations

- The plan said no new test ("a string-presence assertion on skill prose
  would be a trivial test"). During completion, discovery of
  `tests/test_workspace_validate_fix_skill.py` showed the repository already
  treats this skill as a document contract, machine-checking that it states
  its invariants (`test_document_states_the_three_invariants`). Following
  that established convention, added
  `test_document_forecloses_pointer_coverage_as_deletion_grounds` so a future
  template edit cannot silently drop the guard. This is a contract test in
  the file's own idiom, not a trivial test.