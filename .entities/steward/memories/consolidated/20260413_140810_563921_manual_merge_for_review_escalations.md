---
title: Manual merge for review escalations
category: skill
valence: positive
salience: 4
tier: consolidated
last_reinforced: '2026-04-13T14:00:17.847954Z'
recurrence_count: 3
source_memories:
- Manual merge for review escalations
- Review escalation manual merge pattern
- Stash local changes before orchestrator merge
---

When the orchestrator escalates a review (NEEDS_ATTENTION with SCOPE reason), stash local changes first, then manually merge the branch with git merge orch/<chunk> --no-edit, git stash pop, and mark DONE. Unstaged changes (especially templates) often cause merge failures.
