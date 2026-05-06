---
title: Every steward message requires acknowledgment
category: skill
valence: negative
salience: 5
tier: consolidated
last_reinforced: '2026-03-31T16:30:00.609051Z'
recurrence_count: 1
source_memories:
- Ack every message including no-ops
---

All steward messages must be acked to advance the cursor, even informational responses that don't create chunks. Unacked messages cause infinite loops on the next watch.
