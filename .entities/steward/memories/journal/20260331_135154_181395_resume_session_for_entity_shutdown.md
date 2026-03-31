---
title: Resume session for entity shutdown
category: confirmation
valence: positive
salience: 4
tier: journal
last_reinforced: '2026-03-31T13:51:54.181227Z'
recurrence_count: 0
source_memories: []
---

When designing the ve entity claude wrapper, the operator confirmed that `claude --resume <sessionId> --prompt "/entity-shutdown <name>"` is just as robust as post-exit transcript extraction. The primary shutdown strategy should be resume-first (agent self-reflects with full session context), with API-driven transcript extraction as a fallback.
