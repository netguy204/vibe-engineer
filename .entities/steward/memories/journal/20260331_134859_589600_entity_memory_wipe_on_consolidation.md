---
title: Entity memory wipe on consolidation
category: domain
valence: neutral
salience: 3
tier: journal
last_reinforced: '2026-03-31T13:48:59.589588Z'
recurrence_count: 0
source_memories: []
---

The consolidation pipeline originally overwrote memory directories instead of merging. Empty LLM response = wipe all existing memories. Fixed by entity_shutdown_memory_wipe to use merge-based updates with pre-consolidation snapshots.
