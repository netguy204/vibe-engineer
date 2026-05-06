---
title: Batch injection respects depends_on
category: domain
valence: positive
salience: 3
tier: consolidated
last_reinforced: '2026-04-13T14:00:17.847954Z'
recurrence_count: 2
source_memories:
- Batch injection respects depends_on
- Batch chunk creation and single monitor
---

When injecting multiple chunks, create all chunks first, commit in one batch, then inject all in a single command. The orchestrator reads each chunk's depends_on field and schedules accordingly. Set up one monitor cron that tracks all chunk names.
