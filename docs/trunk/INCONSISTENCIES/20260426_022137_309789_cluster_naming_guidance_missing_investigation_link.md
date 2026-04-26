---
discovered_by: audit batch 9c
discovered_at: 2026-04-26T02:21:37Z
severity: low
status: open
artifacts:
  - docs/chunks/cluster_naming_guidance/GOAL.md
  - src/templates/claude/CLAUDE.md.jinja2
---

# cluster_naming_guidance section omits the investigation reference

## Claim

`docs/chunks/cluster_naming_guidance/GOAL.md` Success Criteria #4:

> References the alphabetical_chunk_grouping investigation for detailed rationale

## Reality

The rendered section in `src/templates/claude/CLAUDE.md.jinja2` (lines 41-44):

```
{# Chunk: docs/chunks/cluster_naming_guidance - Naming convention guidance section #}
### Chunk Naming Conventions

Name chunks by the **initiative** they advance, not the artifact type or action verb. Good prefixes are domain concepts that group related work: `ordering_`, `taskdir_`, `template_`. Avoid generic prefixes: `chunk_`, `fix_`, `cli_`, `api_`, `util_`.
```

There is no link or text reference to the `alphabetical_chunk_grouping` investigation in the section itself. The chunk's frontmatter does carry `investigation: alphabetical_chunk_grouping`, but SC #4 is most naturally read as a requirement on the rendered guidance text — it asks operators reading CLAUDE.md to be able to reach the investigation for detailed rationale, which the current single-paragraph section does not enable.

The other substantive criteria (initiative-noun framing, good vs bad prefix examples, template renders) are met. SC #5 (template renders) is generic and was filtered.

## Workaround

None needed.

## Fix paths

1. **(preferred)** Append a short rationale pointer to the section, e.g. `See: docs/investigations/alphabetical_chunk_grouping/OVERVIEW.md for detailed rationale.` Mechanical fix; preserves the section's brevity. Re-render via `ve init`.
2. Loosen SC #4 if the chunk authors decide section brevity outweighs discoverability; capture as a deviation in the chunk and mark this entry resolved.
