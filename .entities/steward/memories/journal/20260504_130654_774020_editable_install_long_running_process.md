---
title: Editable install + long-running process
category: skill
valence: neutral
salience: 4
tier: journal
last_reinforced: '2026-05-04T13:06:54.772870Z'
recurrence_count: 0
source_memories: []
---

/Users/btaylor/.local/share/uv/tools/vibe-engineer/bin/ve is an editable install pointing at /Users/btaylor/Projects/vibe-engineer/src via a .pth file. New ve invocations pick up code changes immediately. BUT long-running Python processes (like ve board watch) hold their original modules in memory and do NOT pick up code changes until killed and restarted. When verifying a fix is live, also confirm the process was restarted post-fix.
