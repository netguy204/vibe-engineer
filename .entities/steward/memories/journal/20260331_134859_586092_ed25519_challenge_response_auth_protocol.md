---
title: Ed25519 challenge-response auth protocol
category: domain
valence: neutral
salience: 2
tier: journal
last_reinforced: '2026-03-31T13:48:59.586078Z'
recurrence_count: 0
source_memories: []
---

The swarm authenticates WebSocket clients via Ed25519 challenge-response: server sends random 32-byte nonce, client signs it with the swarm private key, server verifies against stored public key using @noble/ed25519. All post-auth operations (including channel delete) are gated on this.
