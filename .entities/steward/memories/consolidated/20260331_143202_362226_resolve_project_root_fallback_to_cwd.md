---
title: Resolve project root fallback to CWD
category: skill
valence: negative
salience: 4
tier: consolidated
last_reinforced: '2026-03-31T14:26:09.603896Z'
recurrence_count: 2
source_memories:
- Resolve project root fallback to CWD
- Dotenv walks all parents not just first
---

resolve_project_root() from board.storage fails silently in projects that don't have the board subsystem configured. Any code depending on it must catch the failure and fall back to Path.cwd(). Environment loading must walk ALL .env files from project root to filesystem root, not stop at the first one found.
