---
title: Handshake timeout kills watch process
category: domain
valence: neutral
salience: 3
tier: consolidated
last_reinforced: '2026-03-31T13:48:59.587664Z'
recurrence_count: 1
source_memories:
- Handshake timeout kills watch process
---

The watch reconnect logic catches ConnectionClosedError but not TimeoutError or SSLCertVerificationError during WebSocket handshake. These transient errors kill the watch process. The board_watch_handshake_retry chunk adds retry logic for these.
