---
title: Ack every message including no-ops
category: skill
valence: negative
salience: 5
tier: consolidated
last_reinforced: '2026-03-31T13:48:59.585325Z'
recurrence_count: 1
source_memories:
- Ack every message including no-ops
---

Every steward message must be acked, even questions that don't produce chunks. Without acking, the cursor stays in place and the next watch re-delivers the same message, causing an infinite loop.
