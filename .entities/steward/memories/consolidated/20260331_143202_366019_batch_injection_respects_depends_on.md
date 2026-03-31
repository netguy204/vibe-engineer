---
title: Batch injection respects depends_on
category: domain
valence: positive
salience: 3
tier: consolidated
last_reinforced: '2026-03-31T13:48:59.586769Z'
recurrence_count: 1
source_memories:
- Batch injection respects depends_on
---

When injecting multiple chunks with ve orch inject, pass them all in one command. The orchestrator reads each chunk's depends_on field and schedules accordingly — blocked chunks wait for their dependencies to complete before starting.
