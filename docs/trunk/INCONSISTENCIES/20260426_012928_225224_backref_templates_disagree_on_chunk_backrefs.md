---
discovered_by: claude
discovered_at: 2026-04-26T01:29:28Z
severity: medium
status: resolved
resolved_by: "subsystem template aligned to PLAN template (fix path 1) — both # Subsystem: and # Chunk: declared valid; cross-reference to ARTIFACTS.md for the canonical convention"
artifacts:
  - src/templates/chunk/PLAN.md.jinja2
  - src/templates/subsystem/OVERVIEW.md.jinja2
  - docs/chunks/code_to_docs_backrefs/GOAL.md
---

# Chunk and subsystem templates disagree on whether `# Chunk:` backreferences are valid

## Claim

Two templates that both teach agents the backreference convention give
contradictory guidance:

`src/templates/chunk/PLAN.md.jinja2` lines 113-115:

```
**Valid backreference types:**
- `# Subsystem: docs/subsystems/<name>` - For architectural patterns
- `# Chunk: docs/chunks/<name>` - For implementation work
```

`src/templates/subsystem/OVERVIEW.md.jinja2` lines 178-183:

```
# Subsystem: docs/subsystems/short_name - Brief subsystem description
```

> Subsystems are the only valid code backreference type. Only subsystems represent
> enduring architectural patterns that warrant code backreferences.

The chunk PLAN template explicitly endorses `# Chunk:` backrefs as a first-class
type; the subsystem OVERVIEW template explicitly forbids them ("subsystems are the
only valid code backreference type").

The originating intent in `docs/chunks/code_to_docs_backrefs/GOAL.md` describes
both `# Chunk:` and `# Subsystem:` comment forms as the convention, matching the
PLAN template.

## Reality

The repository contains many `# Chunk:` backreferences in `src/` (e.g.
`src/artifact_ordering.py`, `src/chunks.py`, `src/cli/chunk.py`, `src/cli/external.py`,
`src/narratives.py`, `src/project.py`, `src/repo_cache.py`,
`src/external_resolve.py`). New chunks landing today follow the PLAN template's
guidance and continue adding `# Chunk:` lines. The subsystem template's
"subsystems only" prescription is not what the codebase or the
`code_to_docs_backrefs` chunk actually establish.

Reproduction:

```
grep -rn "^# Chunk:" src/*.py | wc -l
```

returns dozens of hits.

## Workaround

None applied in this audit pass — the audit only logs cross-artifact
inconsistencies. Agents reading the subsystem template alone will be misled
about what the project's actual convention is.

## Fix paths

Ranked:

1. **Fix the subsystem OVERVIEW.md template** to align with the chunk PLAN
   template and current code: list both `# Subsystem:` and `# Chunk:` as valid
   backreference types, with subsystem comments preferred for canonical
   pattern implementations and chunk comments used for incremental work.
   Sole-source the convention text in one place if practical (e.g., a shared
   include or a pointer to CLAUDE.md's "Code Backreferences" section).
   This matches the originating intent in `code_to_docs_backrefs` and avoids
   invalidating ~hundreds of in-tree `# Chunk:` comments.

2. **Tighten the convention to subsystems-only and remove `# Chunk:` backrefs.**
   Update PLAN.md.jinja2 and CLAUDE.md.jinja2 to drop the `# Chunk:` form,
   then sweep `src/` to delete existing `# Chunk:` comments. This is a much
   bigger change and would require an ACTIVE chunk owning the policy shift,
   plus marking `code_to_docs_backrefs` HISTORICAL once a successor owns the
   new (narrower) intent.

The smaller fix (path 1) is appropriate as a focused ACTIVE chunk, e.g.
`backref_template_alignment`.
