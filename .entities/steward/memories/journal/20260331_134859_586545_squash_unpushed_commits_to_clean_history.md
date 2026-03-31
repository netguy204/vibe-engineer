---
title: Squash unpushed commits to clean history
category: skill
valence: positive
salience: 2
tier: journal
last_reinforced: '2026-03-31T13:48:59.586529Z'
recurrence_count: 0
source_memories: []
---

When the operator asks to amend or clean up commits that haven't been pushed yet, use git reset --soft origin/main to squash them into a single clean commit. This is safe because the commits haven't left the local repo.
