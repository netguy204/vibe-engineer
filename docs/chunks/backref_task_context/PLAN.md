<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a documentation-only change. We need to update two templates:

1. **CLAUDE.md.jinja2** - The "Code Backreferences" section currently instructs agents
   to remove `# Chunk:` comments. This was correct when chunks lived in a scratchpad,
   but chunks now live in `docs/chunks/` and are valid backreference targets. We need
   to re-enable chunk backreferences alongside subsystem backreferences.

2. **PLAN.md.jinja2** (or chunk-implement.md.jinja2) - The backreference guidance in
   the Sequence section needs to be updated to:
   - Allow chunk backreferences alongside subsystem backreferences
   - Provide task context guidance: in multi-project tasks, code backreferences should
     point to the local `docs/chunks/<name>/` directory (which contains `external.yaml`),
     not to paths in the external artifact repo

Per DEC-004 (markdown references relative to project root), all backreference paths
will be relative to the project root.

The template_system subsystem is STABLE, so we'll follow its patterns for any
template changes.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system.
  We are editing Jinja2 templates that are rendered via the canonical template_system
  module. No code changes to the template_system itself—only template content changes.

## Sequence

### Step 1: Update CLAUDE.md.jinja2 - Code Backreferences section

**Location**: `src/templates/claude/CLAUDE.md.jinja2` (lines ~386-404)

**Current text** (problematic):
```markdown
## Code Backreferences

Source code may contain backreference comments that link code back to the subsystem documentation that governs it:

```python
# Subsystem: docs/subsystems/template_system - Unified template rendering
```

**What backreferences mean:**
- `# Subsystem: ...` - This code is part of a documented subsystem. Read the subsystem's OVERVIEW.md for patterns and invariants.

Subsystems are the only valid code backreference type. They represent enduring architectural documentation that lives in the repository.

**When implementing code:** Add `# Subsystem:` backreference comments when code implements or extends a documented subsystem. This links code to its governing patterns and invariants.

**When you encounter other backreference types:** Remove them.
- `# Chunk: ...` - Chunks are legacy backreferences that are no longer valid. Remove these references.
- `# Narrative: ...` - Narratives are legacy backreferences that are no longer valid. Remove these references.
```

**Replace with**:
```markdown
## Code Backreferences

Source code may contain backreference comments that link code back to documentation:

```python
# Subsystem: docs/subsystems/template_system - Unified template rendering
# Chunk: docs/chunks/auth_refactor - Authentication system redesign
```

**Valid backreference types:**

- `# Subsystem: docs/subsystems/<name>` - Links to enduring architectural patterns. Use when code implements or extends a documented subsystem.
- `# Chunk: docs/chunks/<name>` - Links to implementation work. Use when code was created or significantly modified by a chunk.

**When to use each type:**

| Type | Purpose | Lifespan | When to add |
|------|---------|----------|-------------|
| Subsystem | Architectural pattern | Enduring | Code follows a documented subsystem's patterns |
| Chunk | Implementation work | Until SUPERSEDED/HISTORICAL | Code created or significantly modified by the chunk |

**Chunk backreferences and task context:**

When adding chunk backreferences in a multi-project task, always use the local path within the current repository (e.g., `docs/chunks/chunk_name`), not cross-repository paths. Each participating project has `external.yaml` pointers for chunks that live in the external artifacts repo. The local path is universally resolvable from within the project.

**Narrative backreferences:** Do NOT add `# Narrative:` backreferences. Narratives decompose into chunks; reference the implementing chunk instead.
```

### Step 2: Update PLAN.md.jinja2 - Backreference guidance

**Location**: `src/templates/chunk/PLAN.md.jinja2` (lines ~106-124)

**Current text** (inside the HTML comment in Sequence section):
```markdown
**BACKREFERENCE COMMENTS**

When implementing code that relates to a documented subsystem, add backreference
comments to help future agents trace code back to its governing documentation.
Subsystems are the only valid code backreference type.

Place comments at the appropriate level:
- **Module-level**: If this code implements the subsystem's core functionality
- **Class-level**: If this class is part of the subsystem pattern
- **Method-level**: If this method implements a specific subsystem behavior

Format (place immediately before the symbol):
```
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact manager pattern
```

Do NOT add chunk or narrative backreferences. Only subsystems represent enduring
architectural patterns that warrant code backreferences.
```

**Replace with**:
```markdown
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
```

### Step 3: Regenerate rendered files

Run `uv run ve init` to regenerate:
- `CLAUDE.md` (from `CLAUDE.md.jinja2`)
- `.claude/commands/chunk-plan.md` (if it renders PLAN.md content)

### Step 4: Verify rendered output

1. Check that `CLAUDE.md` no longer instructs agents to remove chunk backreferences
2. Check that the chunk backreference guidance is clear and includes task context note
3. Ensure the rendered markdown is well-formed

## Dependencies

None. This is a documentation-only change to existing templates.

## Risks and Open Questions

1. **Chunk backreference lifespan**: Chunks can become SUPERSEDED or HISTORICAL.
   Should we add guidance about when to remove chunk backreferences? The current
   approach assumes agents will update backreferences when chunks become stale,
   but this isn't explicitly documented.

2. **Consistency with existing codebase**: There may be existing `# Chunk:` comments
   that were previously marked for removal. After this change, those comments become
   valid again. No action needed—they were always pointing to valid locations.

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