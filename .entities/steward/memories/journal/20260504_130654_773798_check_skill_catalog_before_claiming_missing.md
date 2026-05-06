---
title: Check skill catalog before claiming missing
category: skill
valence: neutral
salience: 4
tier: journal
last_reinforced: '2026-05-04T13:06:54.772870Z'
recurrence_count: 0
source_memories: []
---

Before triaging a 'skill X is missing' bug report, search the available-skills catalog from the session-start system reminder and run 'ls .claude/commands/ src/templates/commands/' to verify the skill doesn't already ship. /steward-send and /steward-changelog both already existed when an agent reported them as missing — the skill was simply not surfaced in their session catalog. Answer as a question on the changelog, not a chunk.
