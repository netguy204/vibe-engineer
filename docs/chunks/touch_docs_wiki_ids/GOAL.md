---
status: HISTORICAL
ticket: null
parent_chunk: entity_touch_protocol_docs
code_paths:
- src/entities.py
- src/templates/commands/entity-startup.md.jinja2
code_references:
- ref: src/entities.py#Entities::startup_payload
  implements: "Touch Protocol prose updated to acknowledge both timestamp-prefixed and slug ID formats"
- ref: src/templates/commands/entity-startup.md.jinja2
  implements: "Step 8 examples show both tiered-memory and wiki-based entity ID formats"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: implementation
depends_on: []
created_after:
- orch_worktree_process_reap
---

# Chunk Goal

## Minor Goal

Update Touch Protocol docs to show both memory ID formats: timestamp-prefixed
IDs (tiered-memory entities) and slug IDs (wiki-based entities).

The `entity_touch_protocol_docs` chunk fixed the 3-arg signature but its
example still shows only the timestamp-prefixed format:

```
ve entity touch aria 20260414_120742_089450_template_editing_workflow "..."
```

Wiki-based entities use slug IDs like `trust-the-canonical-synthesis` or
`cloud-capital-roll-call`. The startup payload shows the correct ID for each
entity, but the example format in both the startup payload and skill template
only demonstrates one shape, which confuses first-time wiki entity users.

### The fix

Update the Touch Protocol example in both `src/entities.py` (startup payload)
and `src/templates/commands/entity-startup.md.jinja2` to show both formats
or use a format-agnostic example. Ideally, note that the memory_id is whatever
the `ID:` field shows next to each core memory — the format varies by entity
type.

## Success Criteria

- Touch Protocol docs acknowledge both ID formats (timestamp-prefixed and slug)
- Example is clear that the ID to use is whatever the startup payload shows
- No confusion for wiki-based entity users on first read

## Relationship to Parent

Parent `entity_touch_protocol_docs` fixed the 3-arg signature. This chunk
fixes the example ID format to cover wiki-based entities too.

## Relationship to Parent

<!--
DELETE THIS SECTION if parent_chunk is null.

If this chunk modifies work from a previous chunk, explain:
- What deficiency or change prompted this work?
- What from the parent chunk remains valid?
- What is being changed and why?

This context helps agents understand the delta and avoid breaking
invariants established by the parent.
-->

## Rejected Ideas

<!-- DELETE THIS SECTION when the goal is confirmed if there were no rejected
ideas.

This is where the back-and-forth between the agent and the operator is recorded
so that future agents understand why we didn't do something.

If there were rejected ideas in the development of this GOAL with the operator,
list them here with the reason they were rejected.

Example:

### Store the queue in redis

We could store the queue in redis instead of a file. This would allow us to scale the queue to multiple nodes.

Rejected because: The queue has no meaning outside the current session.

---

-->