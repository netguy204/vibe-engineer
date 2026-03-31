---
title: Reinstall tool after code changes
category: correction
valence: negative
salience: 4
tier: consolidated
last_reinforced: '2026-03-31T13:48:59.586989Z'
recurrence_count: 1
source_memories:
- Reinstall tool after code changes
---

When fixing bugs in vibe-engineer source code, the globally installed ve tool still runs the old code. The operator must run 'uv tool install -e ~/Projects/vibe-engineer' to pick up changes. Always remind the operator to reinstall after pushing fixes.
