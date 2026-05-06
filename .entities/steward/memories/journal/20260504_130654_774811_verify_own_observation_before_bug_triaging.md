---
title: Verify own observation before bug-triaging
category: skill
valence: positive
salience: 4
tier: journal
last_reinforced: '2026-05-04T13:06:54.772870Z'
recurrence_count: 0
source_memories: []
---

When a reporter claims a vibe-engineer bug (e.g., counter not resetting, watch dying at 144s), check the steward's own watch log first. Multiple times this session, my own watch process showed the opposite of the reported behavior (attempts staying at 1, watch surviving 23 hours), proving the fix was live and the reporter was running stale code. Cite the evidence on the changelog response so the reporter has something concrete to act on.
