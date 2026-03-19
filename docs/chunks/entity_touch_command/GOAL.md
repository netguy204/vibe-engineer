---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/models/entity.py
  - src/entities.py
  - src/cli/entity.py
  - tests/test_entities.py
  - tests/test_entity_cli.py
code_references:
  - ref: src/models/entity.py#TouchEvent
    implements: "Pydantic model for touch events serialized to JSONL touch log"
  - ref: src/entities.py#Entities::find_memory
    implements: "Resolves memory_id to file path across all tiers (core → consolidated → journal)"
  - ref: src/entities.py#Entities::touch_memory
    implements: "Updates last_reinforced timestamp and appends touch event to session log"
  - ref: src/entities.py#Entities::read_touch_log
    implements: "Reads JSONL touch log for shutdown skill to review session memory usage"
  - ref: src/cli/entity.py#touch
    implements: "CLI command: ve entity touch <name> <memory_id> [reason]"
narrative: null
investigation: agent_memory_consolidation
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_memory_schema
created_after: []
---

# Chunk Goal

## Minor Goal

Implement the `ve entity touch <memory_id> [reason]` command that records runtime reinforcement of core memories. When an agent notices itself applying a core memory during its workday, it runs this command to signal that the memory is actively useful.

The touch command:
1. Updates the memory's `last_reinforced` timestamp
2. Appends the touch event to a session touch log (for the shutdown skill to review)
3. Optionally records a brief reason (useful for debugging and consolidation)

This provides the second reinforcement signal (alongside consolidation-time association) that drives the decay system. Memories that are frequently touched during workdays resist decay; memories never touched are candidates for demotion.

The investigation's H6 experiment validated that agents can self-report core memory usage with 100% precision and no over-reporting (see `docs/investigations/agent_memory_consolidation/prototypes/touch_log.jsonl`).

## Success Criteria

- `ve entity touch <entity_name> <memory_id> [reason]` CLI command exists and works
- Updates `last_reinforced` on the specified memory file
- Appends touch event to a session log (`.entities/<name>/touch_log.jsonl`)
- The shutdown skill can read the touch log to identify which memories were actively used
- Command is fast enough to not interrupt agent workflow (< 100ms)