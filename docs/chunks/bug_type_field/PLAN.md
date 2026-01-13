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

Remember to update code_paths in the chunk's GOAL.md (e.g., docs/chunks/bug_type_field/GOAL.md)
with references to the files that you expect to touch.
-->

## Subsystem Considerations

<!--
Before designing your implementation, check docs/subsystems/ for relevant
cross-cutting patterns.

QUESTIONS TO CONSIDER:
- Does this chunk touch any existing subsystem's scope?
- Will this chunk implement part of a subsystem (contribute code) or use it
  (depend on it)?
- Did you discover code during exploration that should be part of a subsystem
  but doesn't follow its patterns?

If no subsystems are relevant, delete this section.

WHEN SUBSYSTEMS ARE RELEVANT:
List each relevant subsystem with its status and your relationship:
- **docs/subsystems/0001-validation** (DOCUMENTED): This chunk USES the validation
  subsystem to check input
- **docs/subsystems/0002-error_handling** (REFACTORING): This chunk IMPLEMENTS a
  new error type following the subsystem's patterns

HOW SUBSYSTEM STATUS AFFECTS YOUR WORK:

DOCUMENTED subsystems: The subsystem's patterns are captured but deviations are not
being actively fixed. If you discover code that deviates from the subsystem's
patterns, add it to the subsystem's Known Deviations section. Do NOT prioritize
fixing those deviations—your chunk has its own goals.

REFACTORING subsystems: The subsystem is being actively consolidated. If your chunk
work touches code that deviates from the subsystem's patterns, attempt to bring it
into compliance as part of your work. This is "opportunistic improvement"—improve
what you touch, but don't expand scope to fix unrelated deviations.

WHEN YOU DISCOVER DEVIATING CODE:
- Add it to the subsystem's Known Deviations section
- Note whether you will address it (REFACTORING status + relevant to your work)
  or leave it for future work (DOCUMENTED status or outside your chunk's scope)

Example:
- **Discovered deviation**: src/legacy/parser.py#validate_input does its own
  validation instead of using the validation subsystem
  - Added to docs/subsystems/0001-validation Known Deviations
  - Action: Will not address (subsystem is DOCUMENTED; deviation outside chunk scope)
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

---

**BACKREFERENCE COMMENTS**

When implementing code, add backreference comments to help future agents trace code
back to the documentation that motivated it. Place comments at the appropriate level:

- **Module-level**: If this chunk creates the entire file
- **Class-level**: If this chunk creates or significantly modifies a class
- **Method-level**: If this chunk adds nuance to a specific method

Format (place immediately before the symbol):
```
# Chunk: docs/chunks/short_name - Brief description of what this chunk does
```

When multiple chunks have touched the same code, list all relevant chunks:
```
# Chunk: docs/chunks/symbolic_code_refs - Symbolic code reference format
# Chunk: docs/chunks/bidirectional_refs - Bidirectional chunk-subsystem linking
```

If the code also relates to a subsystem, include subsystem backreferences:
```
# Chunk: docs/chunks/short_name - Brief description
# Subsystem: docs/subsystems/short_name - Brief subsystem description
```
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