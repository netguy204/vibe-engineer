# Design Decisions

<!--
This document logs significant design choices. Not every decision—just the
ones where there were real alternatives and the reasoning matters.

This is an append-only log. Don't delete old decisions; if a decision is
revisited, add a new entry that references the old one.

Each entry should be self-contained enough that someone can understand
the decision without reading the entire document.
-->

## Decision Log

<!--
Use the template below for each decision. Number decisions sequentially
(DEC-001, DEC-002, etc.) so they can be referenced from other documents.
-->

### DEC-001: [Short title describing the decision]

**Date**: YYYY-MM-DD

**Status**: ACCEPTED | SUPERSEDED BY DEC-XXX | UNDER REVIEW

**Decision**: 
<!--
One or two sentences stating what was decided. Be direct.
Example: "Use segment-based storage with fixed-size segments of 64MB."
-->

**Context**:
<!--
What situation prompted this decision? What constraints or requirements
were in play? This helps future readers understand why this decision
was being made at all.
-->

**Alternatives Considered**:
<!--
What other options were evaluated? For each, briefly note why it wasn't chosen.

Example:
- Single append-only file: Simpler, but compaction requires rewriting entire file
- Embedded database (RocksDB): Capable, but adds 10MB dependency and opaque internals
- Memory-mapped segments: Better read performance, but complex crash recovery
-->

**Rationale**:
<!--
Why was this alternative chosen over the others? What properties does it
optimize for? What tradeoffs does it accept?
-->

**Consequences**:
<!--
What follows from this decision? What becomes easier? What becomes harder?
What future decisions does this constrain or enable?
-->

**Revisit If**:
<!--
Under what conditions should this decision be reconsidered?
Example: "Revisit if segments larger than 1GB become common, or if we need
transactions across multiple messages."
-->

---

<!--
Copy the template above for each new decision.
Delete this comment block once you have at least one real decision logged.

Example decisions that often warrant logging:
- Choice of primary data structure or storage format
- Choice of language or major dependencies
- Concurrency model
- Error handling strategy
- Public API style
- Testing approach for hard-to-test properties
-->