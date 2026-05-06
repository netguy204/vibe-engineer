---
title: 'Stuck-merge unblock: discard identical local'
category: skill
valence: neutral
salience: 4
tier: journal
last_reinforced: '2026-05-04T13:06:54.772870Z'
recurrence_count: 0
source_memories: []
---

When orchestrator COMPLETE-phase merge aborts with 'uncommitted changes would be overwritten' but the local diff is identical to the branch's diff for that file, run 'git checkout -- <file>' to discard the redundant local copy, then 'git merge orch/<chunk> --no-edit' fast-forwards cleanly. After the work-unit reaches DONE, also run git push (CM1).
