---
title: Always run orchestrator-monitor after injection
category: correction
valence: negative
salience: 5
tier: consolidated
last_reinforced: '2026-04-13T14:00:17.847954Z'
recurrence_count: 1
source_memories:
- Always run orchestrator-monitor after injection
---

After injecting a chunk into the orchestrator, immediately set up /orchestrator-monitor with a cron loop. Without active monitoring, chunk completions go unnoticed and pushes are missed. This was added to the SOP after repeated failures to notice completed chunks.
