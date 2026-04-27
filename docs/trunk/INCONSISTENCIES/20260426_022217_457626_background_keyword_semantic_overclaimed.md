---
discovered_by: claude
discovered_at: 2026-04-26T02:22:17+00:00
severity: medium
status: open
resolved_by: null
artifacts:
  - docs/chunks/background_keyword_semantic/GOAL.md
  - docs/trunk/ORCHESTRATOR.md
  - CLAUDE.md
  - src/templates/claude/CLAUDE.md.jinja2
---

# background_keyword_semantic GOAL points at the wrong target file

## Claim

`docs/chunks/background_keyword_semantic/GOAL.md` (line 28) states:

> "Document the 'background' keyword semantic for agent-orchestrator
> interaction in `CLAUDE.md`."

Success criterion #1 (line 60) reinforces this:

> "**CLAUDE.md updated**: The 'Working with the Orchestrator' section
> includes a subsection explaining the 'background' keyword semantic"

Success criterion #2 enumerates trigger phrases:
> - "do this in the background"
> - "handle this in the background"
> - "run this in the background"
> - "in the background"

## Reality

The "background" keyword documentation lives in
`docs/trunk/ORCHESTRATOR.md` lines 178-218 (under heading `## The
"Background" Keyword`), not in `CLAUDE.md`. The chunk's own
`code_references` correctly identify `docs/trunk/ORCHESTRATOR.md` as
the target ("Background keyword documentation section (moved from
CLAUDE.md)"), but the chunk's GOAL prose and success criterion #1
were not updated to match the move.

`grep -i "background" CLAUDE.md` returns only one hit
(`- User mentions "background", "parallel", or "orchestrator"`),
which is a generic reference, not the documented semantic the chunk
claims.

The trigger phrases in `ORCHESTRATOR.md` differ from those in the
GOAL.md: the doc has `"execute [chunk] in the background"`, `"run
[chunk] in the orchestrator"`, `"inject [chunk]"` for existing-chunk
execution, and `"do this in the background"`, `"create a future
chunk"` for new-chunk creation. None of `"handle this in the
background"` or `"run this in the background"` (as listed in the
GOAL) appear verbatim in the doc.

The chunk template (`src/templates/chunk/GOAL.md.jinja2` line 41)
does include the "in the background" guidance — success criterion #5
is met (with a path typo: GOAL says
`src/templates/chunks/GOAL.md.jinja2`, real path is `chunk/`).

## Workaround

None — the audit only logs. A reader of this GOAL.md will look for
the documentation in CLAUDE.md and not find it; `code_references`
correctly point at `ORCHESTRATOR.md` so a reader checking those will
find the actual content.

## Fix paths

1. **Update the GOAL prose**: rewrite line 28 and success criterion
   #1 to reference `docs/trunk/ORCHESTRATOR.md` instead of
   `CLAUDE.md`. Reconcile the trigger-phrase list (success criterion
   #2) with what the doc actually documents: distinguish
   "execute/inject existing chunk" phrases from "create new chunk for
   background execution" phrases. Fix the `chunks/` → `chunk/` path
   typo in success criterion #5.
2. **Move the docs back to CLAUDE.md**: if the operator's intent
   really was to keep this in CLAUDE.md, move the section back from
   `ORCHESTRATOR.md` and update `code_references` accordingly. The
   move-out was likely a deliberate choice (CLAUDE.md is intentionally
   slimmer; subsystem details live in trunk docs), so this is the
   less-preferred path.
