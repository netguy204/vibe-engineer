---
title: Deploy before restarting watch after worker changes
category: skill
valence: negative
salience: 5
tier: consolidated
last_reinforced: '2026-03-31T13:48:59.584050Z'
recurrence_count: 1
source_memories:
- Deploy before restarting watch after worker changes
---

When a completed chunk has code_paths starting with workers/, deploy the Durable Object worker BEFORE restarting the channel watch. Client and server code must stay in sync — protocol mismatches cause crashes.
