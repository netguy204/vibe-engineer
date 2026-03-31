---
title: Cancel and recreate monitor loops when chunks change
category: skill
valence: positive
salience: 3
tier: journal
last_reinforced: '2026-03-31T13:48:59.585591Z'
recurrence_count: 0
source_memories: []
---

When new chunks are injected, cancel the existing CronCreate monitor loop and create a new one that tracks all active chunks. Stale loops miss newly injected work.
