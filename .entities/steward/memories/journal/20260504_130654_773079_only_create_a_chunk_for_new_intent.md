---
title: Only create a chunk for new intent
category: correction
valence: negative
salience: 5
tier: journal
last_reinforced: '2026-05-04T13:06:54.772870Z'
recurrence_count: 0
source_memories: []
---

Create a chunk only when there is genuinely new intent the code needs to hold. A follow-up correction to an existing chunk's intent — even if it spans multiple files and surfaces multiple bugs — is a fix, not a new chunk. When stopped mid-chunk-flight by the operator, delete the work-unit (ve orch work-unit delete <name>) and the chunk dir, then commit the actual fix on main. The chunk system pays for cross-time intent ownership, not for every code change.
