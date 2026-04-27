---
discovered_by: audit batch 9c
discovered_at: 2026-04-26T02:21:37Z
severity: medium
status: open
artifacts:
  - docs/chunks/friction_chunk_workflow/GOAL.md
  - src/templates/commands/chunk-create.md.jinja2
---

# friction_chunk_workflow over-claims /chunk-create integration

## Claim

`docs/chunks/friction_chunk_workflow/GOAL.md` (Success Criteria 1, 2, 3) asserts:

- `/chunk-create` skill prompts operator to specify friction entries being addressed (if any)
- When friction entries are specified, they are added to chunk frontmatter's `friction_entries` array
- `/chunk-create` updates referenced friction entry status from OPEN to ADDRESSED

## Reality

`src/templates/commands/chunk-create.md.jinja2` (the source-of-truth template for the `/chunk-create` skill) contains **no mention of "friction"** — case-insensitive grep returns zero hits across all 206 lines:

```
grep -in "friction\|FRICTION" src/templates/commands/chunk-create.md.jinja2
# (no output)
```

The chunk-complete side IS implemented — `src/templates/commands/chunk-complete.md.jinja2` step 14 reads chunk frontmatter `friction_entries` and reports resolution status (matching SC #4, #5, #7). But the chunk-create-side workflow (SC #1, #2, #3) has no implementation in the template.

The `code_references` field declares `src/templates/commands/chunk-complete.md.jinja2` as the only template implementation site — quietly conceding the chunk-create side is missing — but the GOAL.md text still asserts both sides are delivered.

## Workaround

None needed for this audit pass.

## Fix paths

1. **(preferred)** Implement the missing `/chunk-create` friction prompts in `src/templates/commands/chunk-create.md.jinja2`: prompt for friction entries, append to chunk frontmatter, transition referenced entries from OPEN to ADDRESSED. Re-render via `ve init`. Then resolve this entry.
2. Narrow the chunk's success criteria to only the chunk-complete side that actually shipped, and split out a follow-up chunk for the chunk-create integration. Honest but loses the bidirectional-workflow framing the chunk promised.
