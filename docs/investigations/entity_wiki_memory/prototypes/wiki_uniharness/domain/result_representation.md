---
title: Result Representation - Static vs Entity
created: 2026-03-31
updated: 2026-03-31
---

# Result Representation

## The Return-Path Problem

Tool calling is bidirectional. The library must abstract not just how tools are presented to models, but how tool results go back into the conversation. This was added after the initial design (DEC-004) when the operator identified it as a missing dimension.

## Two Modes

### Static Results

Immutable tool responses appended to the conversation. Standard model: tool returns a result, it gets added as a message, done.

**Example**: Python execution output (stdout, stderr, exit code).

### Entity Results

Mutable slots that are refreshed in-place as other tool calls impact them. The entity model is motivated by the editor use case: a file's content changes with each edit, and the model should see the current state, not the history of all previous versions.

**Entity Lifecycle**: create -> refresh -> release

## Implementation Approaches

For MVP, the simplest entity implementation is **conversation history rewriting** -- replace the previous file-content message with the updated one. Native mutable blocks (where APIs support them) can come later.

Different APIs map differently:
- Some have native mutable content blocks
- Others require history rewriting (replacing earlier messages)
- The strategy must handle both transparently

## Design Principle

The library manages result placement in the conversation, but the caller owns the conversation loop. This is an explicit scope boundary.

## Open Questions (DRAFT)

- Exact refresh mechanics for entities
- Per-API mapping of entity semantics
- Whether entity release needs explicit lifecycle management or can be implicit (one file per session, released at end)
