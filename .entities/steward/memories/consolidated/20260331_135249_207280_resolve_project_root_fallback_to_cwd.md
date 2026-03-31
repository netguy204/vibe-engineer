---
title: Resolve project root fallback to CWD
category: skill
valence: negative
salience: 4
tier: consolidated
last_reinforced: '2026-03-31T13:48:59.587442Z'
recurrence_count: 1
source_memories:
- Resolve project root fallback to CWD
---

resolve_project_root() from board.storage fails silently in projects that don't have the board subsystem configured. Any code depending on it for non-board purposes (like dotenv loading) must catch the failure and fall back to Path.cwd().
