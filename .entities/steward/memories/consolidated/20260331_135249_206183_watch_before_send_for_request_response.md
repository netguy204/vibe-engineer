---
title: Watch before send for request-response
category: skill
valence: positive
salience: 4
tier: consolidated
last_reinforced: '2026-03-31T13:48:59.582979Z'
recurrence_count: 1
source_memories:
- Watch before send for request-response
---

The efficient request-response pattern over swarm channels is: advance the response channel cursor to head, start a background watch on it, THEN send the request. This prevents race conditions where the response arrives before the watch starts.
