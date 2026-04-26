---
discovered_by: claude
discovered_at: 2026-04-26T01:43:41
severity: low
status: resolved
resolved_by: "audit batch 5f — present-tense rewrite of GOAL"
artifacts:
  - docs/chunks/entity_episodic_skill/GOAL.md
  - src/templates/commands/entity-startup.md.jinja2
---

## Claim

`docs/chunks/entity_episodic_skill/GOAL.md` (pre-rewrite) instructed:

> Add a new step after Step 6 (touch protocol) — Step 7: Episodic memory.
> (Also renumber the current Step 7 "Restore active state" to Step 8.)

The body framed the episodic-memory addition as Step 7, sitting just after a
Step 6 touch protocol.

## Reality

`src/templates/commands/entity-startup.md.jinja2` numbers the steps as:

- Step 5: Orient with your wiki
- Step 6: Commit to wiki maintenance
- Step 7: Note the consolidated memory index
- Step 8: Follow the touch protocol
- Step 9: Episodic memory
- Step 10: Follow your Standard Operating Procedures

Touch protocol is Step 8 (not Step 6) and the episodic-memory step is Step 9
(not Step 7). The chunk's own `code_references` already acknowledged the drift
("renumbered from Step 7 by entity_startup_wiki which added Steps 5-6 for wiki
orientation"), but the body of GOAL.md still carried the original numbering.

## Workaround

Rewrote the GOAL body to reference the touch-protocol anchor and `Step <N>` as
a placeholder, so subsequent re-numbering does not contradict the chunk doc.

## Fix paths

- (FIXED) Rewrite GOAL body to anchor on the touch-protocol step rather than a
  literal step number, matching the present rendered template.
- Alternative: hard-code the current step numbers (9 / 10) in GOAL.md and
  re-audit if the startup skill is renumbered again.
