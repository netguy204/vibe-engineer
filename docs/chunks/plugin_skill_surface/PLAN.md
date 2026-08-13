

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The surface move is a change to one mapping function plus its consumers. The
template collection already renders committed output; only the output *contract*
changes, from `commands/<name>.md` to `skills/<name>/SKILL.md`. The bodies are
untouched, so the Claude flavor keeps its inline backtick probes and no shipped
content loses pre-gathered context.

Three consumers follow the contract: the wheel force-include that publishes the
surface as `orchestrator/skills` package data, the orchestrator's phase-prompt
lookup that reads it back at runtime, and the test suites that locate the
surface by path.

## Approach (detail)

<!--
How will you build this? Describe the strategy at a high level.
What patterns or techniques will you use?
What existing code will you build on?

Reference docs/trunk/DECISIONS.md entries where relevant.
If this approach represents a new significant decision, ask the user
if we should add it to DECISIONS.md and reference it here.

Always include tests in your implementation plan and adhere to
docs/trunk/TESTING_PHILOSOPHY.md in your planning.

Remember to update code_paths in the chunk's GOAL.md (e.g., docs/chunks/plugin_skill_surface/GOAL.md)
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
- **docs/subsystems/validation** (DOCUMENTED): This chunk USES the validation
  subsystem to check input
- **docs/subsystems/error_handling** (REFACTORING): This chunk IMPLEMENTS a
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
  - Added to docs/subsystems/validation Known Deviations
  - Action: Will not address (subsystem is DOCUMENTED; deviation outside chunk scope)
-->

## Sequence

1. Rename `src/templates/plugin/commands/` to `.../skills/` so the collection's
   kind names match what they emit.
2. Teach `plugin_render.output_path` the per-skill layout: a `skills/` template
   renders to `skills/<name>/SKILL.md`; `agents/` renders in place.
3. Delete the committed `commands/` tree and re-render.
4. Move the packaging contract: force-include `skills` (not `commands`) as
   `orchestrator/skills`, and the sdist include alongside it.
5. Retarget `AgentRunner.get_skill_path` to `<name>/SKILL.md` in both the
   packaged and development-checkout branches.
6. Retarget shipped content that names the old paths — the chunk-executor agent
   template's fallback instructions.
7. Retarget the test suites that locate the surface by path, and move skill
   identity from the file stem to the directory name.

## Sequence (original template guidance)

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

When implementing code, add backreference comments to help future agents trace
code back to its governing documentation.

**Valid backreference types:**
- `# Subsystem: docs/subsystems/<name>` - For architectural patterns
- `# Chunk: docs/chunks/<name>` - For implementation work

Place comments at the appropriate level:
- **Module-level**: If this code implements the subsystem/chunk's core functionality
- **Class-level**: If this class is part of the pattern
- **Method-level**: If this method implements a specific behavior

Format (place immediately before the symbol):
```
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact manager pattern
# Chunk: docs/chunks/auth_refactor - Authentication system redesign
```

Do NOT add narrative backreferences. Narratives decompose into chunks; reference
the implementing chunk instead.

**Task context note**: In multi-project tasks, always use local paths (e.g.,
`docs/chunks/chunk_name`) for chunk backreferences, not paths to the external
artifact repo. Each project has `external.yaml` pointers that resolve to the
actual chunk content.
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

- Slash invocation of the retired `/`-commands must still reach every entry
  point via the skills surface. Personal skills at `~/.claude/skills/<name>/SKILL.md`
  are slash-invocable, which is the same layout, but this should be confirmed
  against an installed build of the plugin before release.
- The `GENERATED` marker is an HTML comment ahead of the body; confirm the
  agentskills.io spec tolerates it. It comes from one idiom macro, so a flavor
  override is the fix if not.

## Risks and Open Questions (original template guidance)

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