# Prototype Narrative: Core Chunk Lifecycle

This is a prototype to test whether a narrative provides better semantic value than the 8 individual chunk backreferences in `src/chunks.py`.

## Current state: 8 chunk backreferences

```python
# Chunk: docs/chunks/0001-implement_chunk_start - Initial chunk management
# Chunk: docs/chunks/0002-chunk_list_command - List and latest chunk operations
# Chunk: docs/chunks/0004-chunk_overlap_command - Overlap detection
# Chunk: docs/chunks/0005-chunk_validate - Validation framework
# Chunk: docs/chunks/0012-symbolic_code_refs - Symbolic reference support
# Chunk: docs/chunks/0013-future_chunk_creation - Current/activate chunk operations
# Chunk: docs/chunks/0018-bidirectional_refs - Subsystem validation
# Chunk: docs/chunks/0032-proposed_chunks_frontmatter - List proposed chunks
```

An agent following these must read 8 GOAL.md files to understand why this code exists.

---

## Proposed: Single narrative backreference

```python
# Narrative: docs/narratives/0001-chunk_lifecycle - Core chunk management system
```

### Draft OVERVIEW.md for this narrative:

---

## Advances Trunk Goal

This narrative implements the core chunk lifecycle management layer that enables the documentation-driven development workflow. Chunks are the atomic unit of work in the vibe-engineering system—this code provides the infrastructure to create, discover, validate, and maintain them.

## The Arc

The chunk system evolved through three phases:

**Phase 1: Foundation (Chunks 0001-0002)**
Established the basic primitives: creating chunk directories from templates, listing existing chunks, finding the latest chunk. These enable the fundamental workflow of "start work → find what exists."

**Phase 2: Integrity (Chunks 0004-0005, 0018)**
Added validation and overlap detection. As chunks accumulate, their code references can drift. This phase added tooling to detect when one chunk's changes affect another's references, enabling agents to maintain referential integrity rather than discovering drift later.

**Phase 3: Expressiveness (Chunks 0012-0013, 0032)**
Extended the reference system beyond line numbers to symbolic references (function names, class names) which are more stable across edits. Added support for future/proposed chunks and cross-artifact chunk discovery.

## Why This Matters

An agent trying to understand `src/chunks.py` should know:

1. **This is lifecycle infrastructure** - It manages the creation, discovery, and validation of documentation artifacts, not business logic.

2. **Referential integrity is a core concern** - Much of the complexity exists to detect and repair reference drift between chunks.

3. **The evolution was additive** - Each phase built on the previous without replacing it. The code reflects this layered history.

---

## Evaluation

**Tokens saved:** Instead of reading 8 GOAL.md files (each ~50-100 lines), an agent reads 1 OVERVIEW.md (~40 lines) that synthesizes the story.

**Semantic value added:**
- "This is lifecycle infrastructure" immediately frames the code's purpose
- "Referential integrity is a core concern" explains the non-obvious complexity
- "The evolution was additive" helps parse the code's structure

**What's lost:**
- Detailed success criteria from individual chunks
- Specific implementation decisions at each phase
- Granular traceability for debugging "who changed this"

**Verdict:** For understanding code PURPOSE, the narrative is superior. For understanding code HISTORY, individual chunks remain valuable. This suggests a hybrid approach: narrative for context, chunks for archaeology.
