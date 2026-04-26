---
discovered_by: claude
discovered_at: 2026-04-26T00:19:10Z
severity: medium
status: open
resolved_by: null
artifacts:
  - src/templates/chunk/GOAL.md.jinja2
  - src/orchestrator/  (validation in inject path; specific file TBD)
---

## Claim

`src/templates/chunk/GOAL.md.jinja2` line 241 (in the `DEPENDS_ON` schema doc block):

> `Dependencies on ACTIVE chunks are allowed (they've already completed)`

The chunk template tells operators and agents that they can declare a `depends_on` reference to any chunk that has reached ACTIVE status. The claim implies the orchestrator will treat ACTIVE deps as already-satisfied and proceed.

## Reality

The orchestrator's inject validation rejects any `depends_on` reference whose target is not either (a) currently in the same injection batch or (b) an existing work unit in the orchestrator's pool. ACTIVE chunks that completed manually (i.e., never went through `ve orch inject`) are not work units, so they fail the check.

Reproduction from this session, with chunks `intent_create_gate` etc. declaring `depends_on: ["intent_principles"]` (which is ACTIVE in trunk but never went through the orchestrator):

```
$ ve orch inject intent_create_gate
Error: Chunk 'intent_create_gate' depends on 'intent_principles' which is not in this batch and not an existing work unit
```

Same error fires for every chunk in the batch.

## Workaround

Stripped `intent_principles` from `depends_on` on the six new `intent_*` chunks (commit `9e789f0`). Chunk 7 (`intent_retire_superseded`) retains its dep on `intent_superseded_migration` because that chunk is FUTURE and still in flight, so the orchestrator can resolve it.

The workaround loses information: each chunk in the batch genuinely depends on `intent_principles` having been merged to trunk. Removing the explicit declaration means future readers can't see the dependency in the frontmatter.

## Fix paths

Operator confirmed (2026-04-26): the documented behavior is the intended one — `depends_on` should accept any ACTIVE chunk, even one the orchestrator has never seen.

1. **Preferred.** Fix the orchestrator's inject validation to treat any ACTIVE chunk as a satisfied dependency, regardless of whether it ever appeared as a work unit. The runtime catches up to the docs.
2. **Fallback** (only if 1 turns out to be hard for some reason). Update the chunk template doc to describe the actual constraint: `Dependencies on chunks that went through the orchestrator are allowed; manual completions can't be referenced.` Reverts the docs to match the runtime — but loses the friendlier semantics the operator wants.

The follow-up chunk should also revisit the workaround commit (`9e789f0`) to restore the `intent_principles` dependency declarations once the runtime supports them.
