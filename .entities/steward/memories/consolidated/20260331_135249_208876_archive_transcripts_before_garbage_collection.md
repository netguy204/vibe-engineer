---
title: Archive transcripts before garbage collection
category: domain
valence: negative
salience: 5
tier: consolidated
last_reinforced: '2026-03-31T13:51:54.181227Z'
recurrence_count: 1
source_memories:
- Archive transcripts before garbage collection
---

Claude Code garbage collects old session transcripts over time. We observed 47 sessions indexed but only 12 JSONL files on disk. Entity transcripts must be archived into .entities/<name>/sessions/ immediately after session exit, before Claude Code can clean them up.
