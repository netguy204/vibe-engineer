---
discovered_by: audit batch 9j
discovered_at: 2026-04-26T02:20:06Z
severity: medium
status: open
artifacts:
  - docs/chunks/restore_template_content/GOAL.md
  - src/templates/claude/CLAUDE.md.jinja2
---

## Claim

`docs/chunks/restore_template_content/GOAL.md` Success Criterion #2
("CLAUDE.md.jinja2 restored") asserts that the following content has been
restored to `src/templates/claude/CLAUDE.md.jinja2` from commit `62b6d8f`:

- `investigation` frontmatter reference in "Chunk Frontmatter References" section
- "Proposed Chunks" section explaining the `proposed_chunks` frontmatter pattern
- Correct prose linking "Proposed Chunks" to `proposed_chunks` frontmatter
- Investigation lifecycle details (status table, when to use)
- "What Counts as Code" section (clarifying templates are code)
- Development section (`uv run` instructions for `ve` developers)

Success Criterion #3 ("Re-render produces correct output") asserts that
re-rendering produces `CLAUDE.md` and `.claude/commands/chunk-plan.md`
with all the restored content.

## Reality

Inspection of `src/templates/claude/CLAUDE.md.jinja2` and the rendered
`CLAUDE.md` shows partial restoration only:

- `investigation` frontmatter reference IS present
  (`src/templates/claude/CLAUDE.md.jinja2:48`).
- `chunk-plan.md.jinja2` cluster prefix step IS present
  (`src/templates/commands/chunk-plan.md.jinja2:23`), so Success Criterion
  #1 holds.
- "Proposed Chunks" section: NOT present in `CLAUDE.md.jinja2`. `grep -in
  "proposed chunks"` against the template returns no matches. The concept
  appears in narrative/investigation OVERVIEW templates and in
  `commands/narrative-create.md.jinja2`, but not in the CLAUDE.md template
  as a dedicated section.
- "What Counts as Code" section: NOT present. `grep -in "what counts as
  code"` against `src/templates/claude/CLAUDE.md.jinja2` returns no
  matches.
- Investigation lifecycle details (status table, when to use): NOT
  present in `CLAUDE.md.jinja2`. The template's investigations entry
  (lines 62-66) is a one-line "Read when" + "See:" pointer to
  `docs/trunk/ARTIFACTS.md#investigations`.
- Development section: present in the rendered `CLAUDE.md` (line 201) but
  OUTSIDE the `<!-- VE:MANAGED:END -->` marker (which closes at line
  199). It is project-local content, not template-rendered. So the
  template DOES NOT supply this section, contrary to the goal.

Reproduction:
```
grep -in "proposed chunks\|what counts as code\|^## development\|^### development" \
  src/templates/claude/CLAUDE.md.jinja2
# (no output)
```

The chunk's `code_references` do not declare `status: partial` for any
entry, so the symmetric verification step (not the declared-overclaim
veto) is what surfaces this. Four of the six bulleted items in Success
Criterion #2 are unsatisfied; Criterion #1 holds; Criterion #3 partially
holds (chunk-plan rendering is correct, CLAUDE.md rendering is missing
the bulk of the restored content).

## Workaround

None applied during this audit. The chunk is left in ACTIVE status with
its goal text intact (per audit veto rule: do not rewrite prose for tense
when over-claim is detected). A follow-up implementation pass needs to
either:

- finish backporting the missing sections from commit `62b6d8f` into
  `src/templates/claude/CLAUDE.md.jinja2` and re-render, or
- narrow the success criteria to match what was actually restored.

## Fix paths

1. **Finish the implementation** (preferred if the missing content is
   still wanted): extract the "Proposed Chunks" section, "What Counts as
   Code" section, Investigation lifecycle table, and Development section
   from `git show 62b6d8f -- CLAUDE.md` and add them to
   `src/templates/claude/CLAUDE.md.jinja2`. Re-render via `uv run ve
   init`. Verify each bulleted item appears in the rendered `CLAUDE.md`.

2. **Trim the goal** (preferred if the project has since decided some
   restorations are no longer wanted, e.g. the Investigations content was
   intentionally moved to `ARTIFACTS.md` by `progressive_disclosure_refactor`):
   amend Success Criterion #2 to drop the items that are intentionally
   omitted, leaving only what the project actually wants restored. Note
   in the chunk goal the rationale for each omission. The
   `progressive_disclosure_refactor` annotation already in the
   `code_references` ARTIFACTS.md note suggests at least the
   investigation-lifecycle item may have been deliberately moved rather
   than dropped.
