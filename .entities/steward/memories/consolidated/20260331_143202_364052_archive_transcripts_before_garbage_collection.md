---
title: Archive transcripts before garbage collection
category: domain
valence: negative
salience: 5
tier: consolidated
last_reinforced: '2026-03-31T14:26:09.603896Z'
recurrence_count: 2
source_memories:
- Archive transcripts before garbage collection
- Sessions index is unreliable
---

Claude Code garbage collects old session transcripts over time and its sessions-index.json has zero overlap with actual JSONL files on disk. Entity transcripts must be archived immediately after session exit by scanning filesystem directly for .jsonl files, never rely on the index.
