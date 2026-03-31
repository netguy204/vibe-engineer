---
title: Sessions index is unreliable
category: domain
valence: negative
salience: 4
tier: journal
last_reinforced: '2026-03-31T13:51:54.181227Z'
recurrence_count: 0
source_memories: []
---

Claude Code's sessions-index.json has zero overlap with JSONL files actually on disk. Never rely on it for finding session transcripts — always scan the filesystem directly for .jsonl files.
