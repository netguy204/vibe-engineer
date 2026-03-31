---
title: Maintain client-server protocol synchronization
category: skill
valence: negative
salience: 5
tier: core
last_reinforced: '2026-03-31T13:48:59.584050Z'
recurrence_count: 1
source_memories:
- Deploy before restarting watch after worker changes
---

When changes affect both client and server code (especially workers/), deploy the server first before resuming client operations. Protocol mismatches cause runtime failures.
