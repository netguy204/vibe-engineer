---
title: PID file scope is per-project not global
category: domain
valence: neutral
salience: 3
tier: journal
last_reinforced: '2026-05-04T13:06:54.772870Z'
recurrence_count: 0
source_memories: []
---

The 've board watch' safety-net kill (one watch per channel) reads from {project_root}/.ve/board/cursors/{channel}.watch.pid. Two agents running watch on the same channel from DIFFERENT project_roots have independent PID files and cannot kill each other. Cross-kill only happens within the same project_root. When asked about cross-agent kills, trace via storage.py's watch_pid_path before speculating.
