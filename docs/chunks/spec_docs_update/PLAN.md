<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk is purely documentation work—no code changes are required. The goal is to update SPEC.md and the CLAUDE.md template so that subsystems are documented as a first-class artifact type, capturing all the implementation work done in chunks 0014-0020 of this narrative.

The approach is:
1. Update SPEC.md to add subsystem terminology, directory structure, frontmatter schema, lifecycle statuses, CLI commands, and guarantees
2. Update the CLAUDE.md template to guide agents to check subsystems before implementing patterns

The documentation must accurately reflect the actual implementation in `src/models.py` and `src/subsystems.py`.

## Sequence

### Step 1: Add Subsystem to SPEC.md Terminology Section

Add "Subsystem" to the Artifacts section of the Terminology block in `docs/trunk/SPEC.md`.

**Definition**: A subsystem is a cross-cutting pattern that emerged organically in the codebase and has been documented for agent guidance. Stored in `docs/subsystems/`.

Location: `docs/trunk/SPEC.md`, Terminology > Artifacts section (around line 49-52)

### Step 2: Add Subsystem Directory Structure to SPEC.md

Add the subsystems directory to the Directory Structure diagram in `docs/trunk/SPEC.md`.

Add under `docs/`:
```
    subsystems/
      {NNNN}-{short_name}/         # Subsystem directories
        OVERVIEW.md                 # Subsystem documentation with frontmatter
```

Location: `docs/trunk/SPEC.md`, Directory Structure section (around lines 67-87)

### Step 3: Document Subsystem OVERVIEW.md Frontmatter Schema

Add a new section after "Chunk GOAL.md Frontmatter" documenting the subsystem frontmatter schema.

**Section: Subsystem OVERVIEW.md Frontmatter**

```yaml
---
status: DISCOVERING | DOCUMENTED | REFACTORING | STABLE | DEPRECATED
chunks:
  - chunk_id: "{NNNN}-{short_name}"
    relationship: implements | uses
code_references:
  - ref: path/to/file.ext#ClassName::method_name
    implements: "Description of what this code implements"
    compliance: COMPLIANT | PARTIAL | NON_COMPLIANT
---
```

Include a table documenting each field (status, chunks, code_references).

Location: `docs/trunk/SPEC.md`, after Chunk GOAL.md Frontmatter section (after line 128)

### Step 4: Document Subsystem Status Enum Values

Add a subsection documenting the subsystem status values and their meanings.

**Status Values**:
| Status | Meaning | Agent Behavior |
|--------|---------|----------------|
| `DISCOVERING` | Exploring codebase, documenting pattern and inconsistencies | Agent assists with exploration and documentation |
| `DOCUMENTED` | Inconsistencies known; consciously deferred | Agents should NOT expand chunk scope to fix inconsistencies |
| `REFACTORING` | Actively consolidating via chunks | Agents MAY expand chunk scope for consistency improvements |
| `STABLE` | Consistently implemented and documented | Subsystem is authoritative; agents should follow its patterns |
| `DEPRECATED` | Being phased out | Agents should avoid using; may suggest alternatives |

**Valid Status Transitions** (must match `VALID_STATUS_TRANSITIONS` in `src/models.py`):
- DISCOVERING → DOCUMENTED, DEPRECATED
- DOCUMENTED → REFACTORING, DEPRECATED
- REFACTORING → STABLE, DOCUMENTED, DEPRECATED
- STABLE → DEPRECATED, REFACTORING
- DEPRECATED → (terminal state)

Location: `docs/trunk/SPEC.md`, within the new subsystem frontmatter section

### Step 5: Document Chunk-Subsystem Relationship Types

Add documentation for the bidirectional relationship between chunks and subsystems.

**In chunk GOAL.md frontmatter** (update existing documentation around line 99-112):
- Add `subsystems` field to the frontmatter schema
- Document `implements` vs `uses` relationship types

**In subsystem OVERVIEW.md frontmatter** (new section):
- Document `chunks` field with inverse relationship
- Explain when to use each relationship type

Location: `docs/trunk/SPEC.md`, update chunk frontmatter section and add to subsystem frontmatter section

### Step 6: Add Subsystem CLI Commands to API Surface

Add documentation for the subsystem CLI commands in the API Surface section.

**Commands to document**:

#### ve subsystem discover SHORT_NAME [--project-dir PATH]
Create a new subsystem directory with OVERVIEW.md template for guided discovery.

#### ve subsystem list [--project-dir PATH]
List existing subsystems with their status.

#### ve subsystem status SUBSYSTEM_ID NEW_STATUS [--project-dir PATH]
Update a subsystem's status with transition validation.

For each command, document:
- Arguments and options
- Preconditions
- Postconditions
- Behavior
- Errors
- Exit codes

Location: `docs/trunk/SPEC.md`, API Surface > CLI section (after `ve chunk activate`)

### Step 7: Update Guarantees Section

Add subsystem-specific guarantees to the Guarantees section.

**Add to guarantees**:
- **Subsystem isolation**: Each subsystem directory is self-contained. Subsystem documents reference chunks and code but don't affect chunk behavior.

**Add to "Not guaranteed"**:
- **Subsystem completeness**: A subsystem's code_references may not cover all code that follows or deviates from the pattern.

Location: `docs/trunk/SPEC.md`, Guarantees section (around lines 252-260)

### Step 8: Add Subsystems Section to CLAUDE.md Template

Add a new section to `src/templates/CLAUDE.md` explaining subsystems and when to check them.

**Section: Subsystems (`docs/subsystems/`)**

Content should cover:
- What subsystems are (emergent cross-cutting patterns)
- When to check them (before implementing patterns that might already exist)
- How to read them (OVERVIEW.md contains intent, scope, invariants, implementation locations)
- How subsystem status affects behavior (especially DOCUMENTED vs REFACTORING)

Location: `src/templates/CLAUDE.md`, after the Chunks section and before Available Commands

### Step 9: Add /subsystem-discover to CLAUDE.md Available Commands

Add `/subsystem-discover` to the Available Commands section in `src/templates/CLAUDE.md`.

```markdown
- `/subsystem-discover` - Guide collaborative discovery of an emergent subsystem
```

Location: `src/templates/CLAUDE.md`, Available Commands section

### Step 10: Verify Consistency with Implementation

Final review step: verify that all documented schemas and behaviors match the actual implementation:

1. Compare subsystem frontmatter schema in SPEC.md against `SubsystemFrontmatter` model in `src/models.py`
2. Compare status enum values and transitions against `SubsystemStatus` and `VALID_STATUS_TRANSITIONS` in `src/models.py`
3. Compare CLI command documentation against actual implementation in `src/ve.py` and `src/subsystems.py`

Fix any discrepancies found.

## Dependencies

All prior chunks in the narrative (0014-0020) must be complete. This chunk documents what they implemented.

## Risks and Open Questions

- **Schema drift risk**: If the implementation was modified since planning, the documentation may not match. Mitigated by Step 10's consistency verification.
- **Template vs instance**: The CLAUDE.md template in `src/templates/` is what `ve init` copies. The project's own `CLAUDE.md` may differ. This chunk updates the template; the project's instance is a separate concern.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
