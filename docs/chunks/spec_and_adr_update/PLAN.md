<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a documentation-only chunk that brings trunk documents (SPEC.md and DECISIONS.md) into alignment with the current implementation. No code changes are required.

The approach:
1. **Fix command references**: Search SPEC.md for all occurrences of `ve chunk start` and replace with `ve chunk create`. This was renamed but the spec was not updated.

2. **Add orchestrator worktree context**: The SPEC.md documents the single-IMPLEMENTING constraint (line ~216) but doesn't explain how the orchestrator maintains this via worktrees. Add a clarifying note that each worktree has at most one IMPLEMENTING chunk, and the orchestrator manages multiple worktrees in parallel.

3. **Record missing ADRs**: Add three architectural decision records to DECISIONS.md following the existing format (DEC-001 through DEC-006 already exist):
   - **DEC-007**: Orchestrator daemon + HTTP API architecture
   - **DEC-008**: Pydantic for frontmatter models
   - **DEC-009**: ArtifactManager Template Method pattern

## Subsystem Considerations

No subsystems are relevant to this documentation-only chunk.

## Sequence

### Step 1: Fix `ve chunk start` references in SPEC.md

Search for and replace `ve chunk start` with `ve chunk create` at line ~443 (the CLI command section). Verify:
- Command signature is updated
- All occurrences in the file are updated
- The command description still makes sense (the actual CLI uses "create" as the primary command with "start" as an alias)

Location: `docs/trunk/SPEC.md`

### Step 2: Add orchestrator worktree note to IMPLEMENTING constraint

Add a clarifying note after the IMPLEMENTING status description (line ~216) explaining:
- The single-IMPLEMENTING constraint applies per-worktree
- The orchestrator manages multiple parallel worktrees
- Each worktree has its own IMPLEMENTING chunk scope
- This preserves the constraint's intent (focused work) while enabling parallel execution

Location: `docs/trunk/SPEC.md` (Status Values section, around line 216)

### Step 3: Add DEC-007 - Orchestrator Daemon Architecture

Add an ADR documenting the orchestrator's daemon + HTTP API design:

**Context**: The orchestrator needs to manage long-running work across CLI invocations
**Decision**: Persistent daemon process with Unix socket (local) + TCP port (dashboard)
**Alternatives considered**:
- Direct CLI execution (no parallelism across invocations)
- Background jobs with polling (complex state management)
- Separate microservice (operational overhead)

**Rationale**: Daemon provides single point of coordination; HTTP API enables browser dashboard and programmatic access; Unix socket provides fast local IPC

Location: `docs/trunk/DECISIONS.md`

### Step 4: Add DEC-008 - Pydantic for Frontmatter Models

Add an ADR documenting the choice of Pydantic for frontmatter validation:

**Context**: Frontmatter needs schema validation with clear error messages
**Decision**: Use Pydantic BaseModel for all frontmatter schemas
**Alternatives considered**:
- Manual dict validation (error-prone, verbose)
- dataclasses with validators (less powerful validation)
- marshmallow (another schema library, less pythonic)

**Rationale**: Pydantic provides type coercion, validation, and serialization in one package; BaseModel inheritance enables shared behavior; StrEnum integration for status types

Location: `docs/trunk/DECISIONS.md`

### Step 5: Add DEC-009 - ArtifactManager Template Method Pattern

Add an ADR documenting the ArtifactManager abstract base class:

**Context**: Four artifact types (chunks, narratives, investigations, subsystems) share common lifecycle operations
**Decision**: Template Method pattern via `ArtifactManager` ABC with abstract properties
**Alternatives considered**:
- Composition with helper functions (duplicated method calls)
- Mixin classes (complex inheritance, harder to reason about)
- Standalone functions per artifact type (code duplication)

**Rationale**: Template Method captures shared algorithm (parse frontmatter, validate status, enumerate artifacts) while allowing subclasses to define artifact-specific configuration

Location: `docs/trunk/DECISIONS.md`

### Step 6: Verify consistency

- Read through all changes to ensure no contradictions with actual CLI behavior
- Verify ADR numbering follows the existing convention (DEC-007, DEC-008, DEC-009)
- Verify ADR format matches existing entries in DECISIONS.md

## Dependencies

No dependencies. This is a documentation-only chunk that can be completed independently.

## Risks and Open Questions

- **ADR scope**: The three ADRs cover significant architectural decisions but are retrospective (capturing existing decisions rather than making new ones). Ensure the rationale accurately reflects why these decisions were made, not just what was decided.

- **Worktree explanation**: The orchestrator worktree model is subtle. The note should be clear that the constraint's purpose (focused work, predictable state) is preserved even with parallel worktrees. May need to iterate on wording.

## Deviations

*(To be populated during implementation)*