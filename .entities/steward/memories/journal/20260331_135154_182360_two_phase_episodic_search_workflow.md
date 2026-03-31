---
title: Two phase episodic search workflow
category: skill
valence: positive
salience: 4
tier: journal
last_reinforced: '2026-03-31T13:51:54.181227Z'
recurrence_count: 0
source_memories: []
---

Episodic search uses two phases: (1) BM25 search returns compact ranked snippets, (2) expand reads ±N turns around a hit for full conversation context. The expand phase reveals corrections, follow-ups, and outcomes that snippets miss. Sliding window of 5 with 50% overlap is the best chunking strategy.
