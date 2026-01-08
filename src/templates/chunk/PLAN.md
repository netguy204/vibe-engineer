<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

<!--
How will you build this? Describe the strategy at a high level.
What patterns or techniques will you use?
What existing code will you build on?

Reference docs/trunk/DECISIONS.md entries where relevant.
If this approach represents a new significant decision, ask the user
if we should add it to DECISIONS.md and reference it here.

Always include tests in your implementation plan and adhere to
docs/trunk/TESTING_PHILOSOPHY.md in your planning.

Remember to update code_paths in the chunk's GOAL.md (e.g., docs/chunks/{{ chunk_directory }}/GOAL.md)
with references to the files that you expect to touch.
-->

## Sequence

<!--
Ordered steps to implement this chunk. Each step should be:
- Small enough to reason about in isolation
- Large enough to be meaningful
- Clear about its inputs and outputs

This sequence is your contract with yourself (and with agents).
Work through it in order. Don't skip ahead.

Example:

### Step 1: Define the SegmentHeader struct

Create the struct that represents a segment's header with fields for:
- magic number (4 bytes)
- version (2 bytes)
- segment_id (8 bytes)
- message_count (4 bytes)
- checksum (4 bytes)

Location: src/segment/format.rs

### Step 2: Implement header serialization

Add `to_bytes()` and `from_bytes()` methods to SegmentHeader.
Use little-endian encoding per SPEC.md Section 3.1.

### Step 3: ...
-->

## Dependencies

<!--
What must exist before this chunk can be implemented?
- Other chunks that must be complete
- External libraries to add
- Infrastructure or configuration

If there are no dependencies, delete this section.
-->

## Risks and Open Questions

<!--
What might go wrong? What are you unsure about?
Being explicit about uncertainty helps you (and agents) know where to
be careful and when to stop and ask questions.

Example:
- fsync behavior may differ across filesystems; need to verify on ext4 and APFS
- Unclear whether concurrent reads during write are safe; may need mutex
- Performance target is aggressive; may need to iterate on buffer sizes
-->

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->