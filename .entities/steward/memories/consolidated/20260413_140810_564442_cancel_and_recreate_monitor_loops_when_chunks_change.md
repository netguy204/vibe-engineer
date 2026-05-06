---
title: Cancel and recreate monitor loops when chunks change
category: skill
valence: positive
salience: 3
tier: consolidated
last_reinforced: '2026-04-13T14:00:17.847954Z'
recurrence_count: 2
source_memories:
- Cancel and recreate monitor loops when chunks change
- Update monitor cron when chunks change
---

When new chunks are injected, cancel the existing monitor cron (CronDelete) and create a new one that tracks all active chunks. Never run multiple overlapping monitor crons. Stale loops miss newly injected work.
