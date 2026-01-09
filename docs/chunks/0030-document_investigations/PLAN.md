# Implementation Plan

## Approach

This chunk is documentation-only—no code changes. We'll update two files:

1. **SPEC.md** - Add investigation documentation parallel to the existing chunk and subsystem sections:
   - Terminology entry
   - Directory naming convention
   - Frontmatter schema
   - Status values and their meanings
   - CLI command documentation

2. **CLAUDE.md** - Expand the investigations section and add the `/investigation-create` command:
   - Detailed guidance on investigation structure
   - When-to-use guidance (investigations vs narratives vs direct chunks)
   - Slash command listing

The approach follows DEC-004 (markdown references relative to project root) and mirrors the structure already established for chunks and subsystems.

Additionally, we need to link the `/investigation-create` slash command by symlinking the template to `.claude/commands/`.

## Sequence

### Step 1: Add Investigation to SPEC.md Terminology

In the Terminology → Artifacts section, add:

```markdown
- **Investigation**: An exploratory document for understanding something before committing to action—diagnosing an issue or exploring a concept. Stored in `docs/investigations/`.
```

Location: docs/trunk/SPEC.md (after the Subsystem entry, around line 52)

### Step 2: Add Investigation Directory Structure to SPEC.md

Update the Directory Structure section to include `docs/investigations/` with the naming pattern.

Location: docs/trunk/SPEC.md (in the directory tree around line 68-91)

### Step 3: Add Investigation Directory Naming Section to SPEC.md

Add a new section after "Subsystem Directory Naming":

```markdown
### Investigation Directory Naming

Format: `{investigation_id}-{short_name}`

- `investigation_id`: 4-digit zero-padded integer (0001, 0002, ...)
- `short_name`: lowercase alphanumeric with underscores/hyphens

Examples: `0001-memory_leak`, `0002-graphql_migration`
```

Location: docs/trunk/SPEC.md (after Subsystem Directory Naming section)

### Step 4: Add Investigation OVERVIEW.md Frontmatter Section to SPEC.md

Add the frontmatter schema documentation:

```yaml
---
status: ONGOING | SOLVED | NOTED | DEFERRED
trigger: {description} | null
proposed_chunks:
  - prompt: "Description of proposed work"
    chunk_directory: "{NNNN}-{short_name}" | null
---
```

Include the field descriptions table and status value meanings.

Location: docs/trunk/SPEC.md (after the Investigation Directory Naming section)

### Step 5: Add Investigation CLI Commands to SPEC.md

Document `ve investigation create` and `ve investigation list` commands following the existing pattern for other CLI commands.

Location: docs/trunk/SPEC.md (in the CLI section, after subsystem commands)

### Step 6: Expand CLAUDE.md Investigations Section

Replace the current minimal investigations section with comprehensive guidance including:
- What investigations contain (trigger, success criteria, hypotheses, exploration log, findings, proposed chunks, resolution)
- When to use investigations vs narratives vs direct chunks
- Investigation status values and what they mean

Location: CLAUDE.md (Investigations section, currently lines 63-72)

### Step 7: Add /investigation-create to CLAUDE.md Available Commands

Add the `/investigation-create` command to the Available Commands section.

Location: CLAUDE.md (Available Commands section, around line 84)

### Step 8: Link investigation-create.md to .claude/commands/

Create a symlink from `.claude/commands/investigation-create.md` to the template at `src/templates/commands/investigation-create.md.jinja2`.

This follows the pattern established by other slash commands.

## Dependencies

- Chunks 0027 (investigation template) and 0029 (investigation CLI commands) should be complete. The template and CLI commands already exist, so this appears to be the case.

## Risks and Open Questions

- None significant. This is straightforward documentation work following established patterns.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->