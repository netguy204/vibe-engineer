---
title: Dotenv walks all parents not just first
category: correction
valence: negative
salience: 5
tier: journal
last_reinforced: '2026-03-31T13:48:59.587207Z'
recurrence_count: 0
source_memories: []
---

The .env loader must collect and load ALL .env files from project root up to filesystem root, not stop at the first one found. Intermediate .env files (e.g., ~/Tasks/.env) would shadow ~/.env if only the first is loaded. Closer files take precedence via first-write-wins.
