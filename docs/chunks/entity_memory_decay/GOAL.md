---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/entity_decay.py
  - src/models/entity.py
  - src/entity_shutdown.py
  - src/entities.py
  - tests/test_entity_decay.py
  - tests/test_entity_decay_integration.py
code_references: []
narrative: null
investigation: agent_memory_consolidation
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_shutdown_skill
- entity_touch_command
created_after: []
---

# Chunk Goal

## Minor Goal

Implement decay mechanics for all memory tiers, integrated into the shutdown skill's consolidation step. Without decay, core memories grow monotonically and eventually overwhelm the startup context budget. Decay ensures the memory system stays bounded regardless of how long an entity runs.

Two complementary mechanisms:

1. **Recency-based decay**: Every memory carries a `last_reinforced` timestamp (updated by both consolidation-time association and runtime `ve entity touch` calls). Memories unreinforced for N consolidation cycles lose salience, then demote, then expire:
   - Tier 2 → loses salience → demotes to tier 1 → eventually expires
   - Tier 1 → loses salience → expires
   - Tier 0 → expires after M cycles without association

2. **Capacity pressure**: Each tier has a soft budget. When exceeded, the least-recently-reinforced memories are demoted or expired first. This creates competitive dynamics — new core memories must earn their place, and old ones must continue proving relevance through reinforcement.

Combined effect: skills used daily stay core forever; skills critical during a past project phase but no longer relevant gradually fade.

## Success Criteria

- Tier-0 memories expire after N consolidation cycles without association (N is configurable, suggest default 5)
- Tier-1 memories decay salience and eventually expire without reinforcement
- Tier-2 memories can be demoted to tier-1 when unreinforced and under capacity pressure
- Tier-2 capacity budget is configurable (suggest default 15 memories)
- Both reinforcement signals are respected: consolidation-time association AND runtime touch events
- After 20+ simulated consolidation cycles, the memory set remains bounded (startup payload stays under 4K tokens)
- Decay is logged so the operator can audit what was forgotten and why

## Rejected Ideas

### Immortal core memories

Making tier-2 memories exempt from decay. Rejected because without decay at all tiers, core memories grow monotonically. The investigation's prototype produced 11 core memories from just 6 days — extrapolated to months, this exceeds the context budget. The LSTM analogy applies here: the forget gate operates on cell state too.