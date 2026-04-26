---
discovered_by: claude
discovered_at: 2026-04-26T04:44:29+00:00
severity: high
status: open
resolved_by: null
artifacts:
  - docs/chunks/respect_future_intent/GOAL.md
  - src/templates/commands/chunk-create.md.jinja2
---

# respect_future_intent over-claims scope

## Claim

`docs/chunks/respect_future_intent/GOAL.md` is ACTIVE and asserts five
substantive success criteria:

1. **User intent detection** — the `/chunk-create` instructions tell the
   agent to scan for FUTURE-preference signals (`future`, `later`, `queue`,
   `backlog`, `upcoming`, `not now`, `after current work`).
2. **Priority order documented** — explicit user signals > existing
   implementing chunk check > default behavior.
3. **IMPLEMENTING intent detection** — detect explicit `now`,
   `immediately`, `start working on`, `next up` signals.
4. **Conflict handling** — when intent conflicts with current state, the
   agent offers to pause the current implementing chunk so the new chunk
   can become IMPLEMENTING.
5. **Safe pause protocol** — before pausing, the agent must run tests,
   add a "Paused State" section to the prior PLAN.md, and only then
   change status from IMPLEMENTING to FUTURE.

The prose around these criteria is written as if the chunk has been (or
is being) realized: "This chunk improves the slash command to analyze
the user's input for explicit signals…"

## Reality

The chunk's own frontmatter contradicts the prose:

```yaml
code_references:
  - ref: src/templates/commands/chunk-create.md.jinja2
    implements: "Basic existing-implementing-chunk detection (Step 9 only); does NOT implement user intent detection, priority order, conflict handling, or safe pause protocol from success criteria"
    status: partial
```

The single `code_reference` admits `status: partial` and explicitly lists
four of the five success criteria as **not implemented**. Only the
pre-existing "implementing chunk already exists" check (Step 9 of the
template) is in place — and that predates this chunk; it is the *default
heuristic* the chunk is supposed to override, not the override itself.

So the chunk asserts a state of the world (the slash command respects
explicit user intent with priority ordering, conflict handling, and a
safe pause protocol) that the rendered template
(`src/templates/commands/chunk-create.md.jinja2`) and its source do not
realize. Any agent reading the GOAL.md and assuming the behavior exists
will be wrong.

## Workaround

None — the audit only logs. A subsequent agent picking up this chunk
needs to treat it as unimplemented work, not as completed work to
describe in present tense. The `intent_active_audit` veto rule blocks a
tense rewrite here precisely because rewriting the prose to present tense
would substitute one false claim ("the system does X") for another ("the
system has been changed to do X"), when in fact neither is true.

## Fix paths

1. **Implement the missing pieces** (preferred): extend
   `src/templates/commands/chunk-create.md.jinja2` with the user-intent
   scan, priority ordering, conflict handling, and safe pause protocol
   the success criteria describe; then update the `code_references` to
   drop `status: partial`. Only after that should the GOAL.md prose be
   rewritten in present tense.
2. **Narrow the goal**: shrink the success criteria down to what the
   single `code_references` row actually delivers (essentially nothing
   beyond the pre-existing Step 9 check), and demote this chunk to
   `COMPLETED` or split the unrealized criteria into a successor chunk.
   This is dishonest unless the operator explicitly decides the original
   ambition was wrong.
