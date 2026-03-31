---
title: Always verify working directory before commands
category: correction
valence: negative
salience: 5
tier: core
last_reinforced: '2026-03-31T13:51:54.181227Z'
recurrence_count: 3
source_memories:
- CWD affects ve orch commands
- CWD matters for chunk creation too
- Deploy CWD trap after worker deploy
---

ve commands resolve paths relative to CWD. Deploy workflows change directory and leave you in subdirectories. Always verify or reset to project root before running ve commands to avoid failures and misplaced artifacts.
