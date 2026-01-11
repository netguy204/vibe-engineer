<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a documentation-only cleanup task that removes references to the deprecated
sequential numbering scheme from slash command files. The artifact subsystem now uses
short names as canonical identifiers, with `created_after` providing causal ordering
(per the workflow_artifacts subsystem documentation).

**Strategy:**
1. Search all `.claude/commands/*.md` files for deprecated patterns
2. Update each file to use short name references and direct CLI usage patterns
3. Verify no deprecated patterns remain via grep

**No tests required** - this is pure documentation cleanup with no code changes.
The `ve chunk validate` CLI command can verify that frontmatter and references remain
syntactically correct after changes.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk USES the workflow_artifacts
  subsystem's directory naming conventions. The subsystem documents that the `NNNN-`
  prefix is legacy and short names are now canonical. This chunk enforces that convention
  in the slash command documentation.

## Sequence

### Step 1: Fix chunk-complete.md

**Location:** `.claude/commands/chunk-complete.md`

**Issue:** Step 3 instructs agents to "Extract the sequential ID for the chunk from
the prefix number in the chunk directory."

**Fix:** Replace step 3 with instructions to use the chunk directory name directly
as the `<chunk_id>` (the short name). The `ve` CLI accepts short names directly -
no extraction needed.

**Before:**
```
3. Extract the sequential ID for the chunk from the prefix number in the chunk
   directory. We will call this <chunk_id> below.
```

**After:**
```
3. The chunk directory short name (e.g., `audit_seqnum_refs` from
   `docs/chunks/audit_seqnum_refs`) is the `<chunk_id>` used by CLI commands below.
```

### Step 2: Fix chunk-update-references.md

**Location:** `.claude/commands/chunk-update-references.md`

**Issue:** Line 44 shows example backreference format with `NNNN-short_name` pattern.

**Fix:** Update the backreference format example to use short-name-only format.

**Before:**
```
- Backreference format: `# Chunk: docs/chunks/NNNN-short_name - Brief description`
```

**After:**
```
- Backreference format: `# Chunk: docs/chunks/short_name - Brief description`
```

### Step 3: Fix subsystem-discover.md

**Location:** `.claude/commands/subsystem-discover.md`

**Issue:** Line 24 shows pattern matching with `NNNN-*` prefix for existing subsystems.

**Fix:** Update to show short-name-only pattern, noting that legacy prefixes are still
recognized for reading.

**Before:**
```
1. **Existing subsystem** (continuing discovery): If `$ARGUMENTS` matches pattern
   `docs/subsystems/NNNN-*` or just `NNNN-*` (e.g., `0001-validation`,
   `docs/subsystems/0002-frontmatter`), this is a request to continue discovery
```

**After:**
```
1. **Existing subsystem** (continuing discovery): If `$ARGUMENTS` matches pattern
   `docs/subsystems/<short_name>` or just `<short_name>` (e.g., `validation`,
   `docs/subsystems/frontmatter`), this is a request to continue discovery
```

Also update line 78 example from `docs/subsystems/0003-frontmatter_handling` to
`docs/subsystems/frontmatter_handling`.

### Step 4: Verify no deprecated patterns remain

Run grep across all command files to confirm cleanup is complete:

```bash
grep -riE "sequence|sequential|NNNN|prefix.?number" .claude/commands/
```

The only expected match should be `chunk-plan.md` line 22 which uses "sequence" in
the phrase "sequence of steps" (referring to implementation steps, not artifact
numbering). This usage is correct and should NOT be changed.

### Step 5: Final verification with ve CLI

Run `ve chunk validate audit_seqnum_refs` to ensure the chunk's frontmatter and
structure remain valid after documentation changes.

## Dependencies

None. This chunk only modifies documentation files that exist.

## Risks and Open Questions

- **False positives in grep:** The word "sequence" appears legitimately in contexts
  unrelated to artifact numbering (e.g., "sequence of steps"). The verification step
  must distinguish these from deprecated usage.

- **Incomplete coverage:** There may be other documentation files outside
  `.claude/commands/` that reference the deprecated numbering scheme. This chunk
  explicitly scopes to slash commands only; CLAUDE.md and other docs are out of scope.

## Deviations

<!-- Populate during implementation if the plan changes significantly. -->