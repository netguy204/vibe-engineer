---
title: Entity session lifecycle architecture
category: domain
valence: neutral
salience: 3
tier: consolidated
last_reinforced: '2026-03-31T13:51:54.181227Z'
recurrence_count: 1
source_memories:
- Entity session lifecycle architecture
---

The entity session harness follows: launch claude with /entity-startup → user works → capture session ID from ~/.claude/sessions/<pid>.json → archive transcript → attempt shutdown via resume → fallback to API extraction → log session to sessions.jsonl. Two API calls for fallback (extraction + consolidation).
