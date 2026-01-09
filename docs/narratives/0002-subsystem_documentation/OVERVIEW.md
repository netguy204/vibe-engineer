---
status: DRAFTING
advances_trunk_goal: "Required Properties: Following the workflow must maintain the health of documents over time and should not grow more difficult over time."
chunks:
  - prompt: "Subsystem schemas and data model"
    chunk_directory: "0014-subsystem_schemas_and_model"
  - prompt: "Subsystem directory structure and CLI scaffolding"
    chunk_directory: "0016-subsystem_cli_scaffolding"
  - prompt: "Subsystem OVERVIEW.md template"
    chunk_directory: "0017-subsystem_template"
  - prompt: "Chunk-subsystem bidirectional references"
    chunk_directory: "0018-bidirectional_refs"
  - prompt: "Subsystem status transitions"
    chunk_directory: "0019-subsystem_status_transitions"
---

## Advances Trunk Goal

**Required Properties** from docs/trunk/GOAL.md states:

> "Following the workflow must maintain the health of documents over time and should not grow more difficult over time."

This narrative introduces subsystem documentation to help agents recognize cross-cutting concerns that already exist in the codebase. Without explicit subsystem documentation, agents repeatedly rediscover (or worse, reinvent) established patterns. This creates document drift as chunks describe redundant implementations rather than referencing shared subsystems.

Additionally, from **Problem Statement**:

> "deeply understanding the goal and the correctness constraints around the project are the entire engineering problem that remains"

Subsystems capture invariants and implementation locations for emergent patterns—knowledge that's currently implicit and easily lost.

## Driving Ambition

Subsystems are cross-cutting patterns that emerge organically as a codebase evolves. Unlike chunks (which are planned forward) or narratives (which decompose ambitions into work), subsystems are discovered backward—we notice "oh, we've built a validation system" or "there's a consistent pattern for how we update frontmatter."

Today, this knowledge lives in developers' heads or is scattered across chunk documents. Agents working in the codebase have no way to know these patterns exist, leading them to reinvent solutions or create inconsistent implementations.

Subsystem documentation formalizes this emergent knowledge:
- **Intent**: What problem does this subsystem solve?
- **Scope**: What's in and out of bounds?
- **Invariants**: What must always be true?
- **Implementation locations**: Where does this subsystem live in code?
- **Chunk relationships**: Which chunks implement vs. use this subsystem?

The lifecycle acknowledges that subsystems are often discovered in an inconsistent state. The `DOCUMENTED` status signals "we know about the inconsistencies but choose to live with them for now," while `REFACTORING` signals "we're actively consolidating—agents should consider expanding scope for consistency improvements."

Bidirectional references between subsystems and chunks help agents understand both "what chunks contributed to this subsystem" and "what subsystems does this chunk touch."

## Data Model

### Subsystem Statuses

| Status | Meaning | Agent Behavior |
|--------|---------|----------------|
| `DISCOVERING` | Exploring codebase, documenting pattern and inconsistencies | Agent assists with exploration and documentation |
| `DOCUMENTED` | Inconsistencies known; consciously deferred | Agents should NOT expand chunk scope to fix inconsistencies |
| `REFACTORING` | Actively consolidating via chunks | Agents MAY expand chunk scope for consistency improvements |
| `STABLE` | Consistently implemented and documented | Subsystem is authoritative; agents should follow its patterns |
| `DEPRECATED` | Being phased out | Agents should avoid using; may suggest alternatives |

### Chunk-Subsystem Relationships

Chunks can relate to subsystems in two ways:

- **implements**: The chunk adds to or modifies the subsystem's implementation (contributes code)
- **uses**: The chunk consumes the subsystem's capabilities without modifying it (depends on it)

This distinction helps agents prioritize: read "implements" chunks to understand internals, read "uses" chunks to understand the API/interface.

## Chunks

### Dependency Graph

```
[1. Schemas] ──────┬──> [2. Directory & CLI]
                   │
                   ├──> [3. Template]
                   │
                   └──> [4. Bidirectional refs]
                              │
[2. Directory & CLI] ─────────┼──> [5. Status transitions]
                              │
[3. Template] ────────────────┼──> [6. Agent command]
                              │
[4. Bidirectional refs] ──────┼──> [8. Impact resolution]
                              │
[5, 6, 8] ────────────────────┴──> [7. Spec & docs]
```

### Chunk Prompts

1. **Subsystem schemas and data model**: Define Pydantic models for subsystem OVERVIEW.md frontmatter including status enum (DISCOVERING, DOCUMENTED, REFACTORING, STABLE, DEPRECATED), chunk relationships with "implements" vs "uses" distinction, and code_references. Add utility functions to detect subsystem directories and parse subsystem metadata.

2. **Subsystem directory structure and CLI scaffolding**: Create `docs/subsystems/` directory structure following the `{NNNN}-{short_name}` pattern. Implement `ve subsystem discover <shortname>` to create a new subsystem directory with OVERVIEW.md template, and `ve subsystem list` to show existing subsystems with their status.

3. **Subsystem OVERVIEW.md template**: Create the subsystem template with sections for: Intent (what problem it solves), Scope (boundaries), Invariants (what must always be true), Implementation Locations (code references), Chunk Relationships (implements/uses with chunk IDs), and Consolidation Chunks (planned refactoring work). Include agent guidance comments for the discovery conversation.

4. **Chunk-subsystem bidirectional references**: Extend chunk GOAL.md frontmatter schema to include optional `subsystems` field with entries specifying subsystem ID and relationship type (implements/uses). Update subsystem frontmatter to include `chunks` field with the inverse relationship. Add validation that referenced subsystems/chunks exist.

5. **Subsystem status transitions**: Implement `ve subsystem status <id> <new-status>` command with transition validation (e.g., can only move to REFACTORING from DOCUMENTED, can only move to STABLE from REFACTORING). Update templates and agent commands to guide appropriate status changes.

6. **Agent discovery command**: Create `/subsystem-discover` agent command that guides the discovery workflow: prompts agent to search for pattern implementations, identify inconsistencies, document invariants, map to existing chunks, and draft consolidation chunk prompts if needed.

7. **Specification and documentation updates**: Update SPEC.md to document subsystems as a new artifact type including directory structure, frontmatter schema, lifecycle statuses, and relationship semantics. Update CLAUDE.md template to include subsystems in the workflow overview.

8. **Subsystem impact resolution during chunk completion**: Integrate subsystem code references into the chunk completion impact resolution process. Add `ve subsystem overlap <chunk_id>` to find subsystems whose code_references overlap with a chunk's changes. Update the `/chunk-complete` workflow to verify subsystem documentation accuracy and chunk-subsystem alignment when overlap is detected.

## Completion Criteria

When complete, an operator and agent can:

1. **Discover and document subsystems** - Run `/subsystem-discover` to collaboratively explore an emergent pattern, with the agent searching the codebase and the operator providing context, resulting in a populated OVERVIEW.md

2. **Signal consolidation intent via status** - Use `DOCUMENTED` to indicate "known inconsistencies, not addressing now" vs `REFACTORING` to indicate "actively consolidating, agents should consider scope expansion"

3. **Navigate chunk-subsystem relationships** - From a chunk, see which subsystems it implements or uses; from a subsystem, see which chunks contribute to or depend on it

4. **Guide agents away from reinvention** - Agents reading CLAUDE.md are directed to check `docs/subsystems/` before implementing patterns that might already exist

5. **Plan consolidation work** - Draft chunk prompts within a subsystem's OVERVIEW.md to address discovered inconsistencies, then create those chunks when ready to refactor

6. **Maintain subsystem documentation health** - During chunk completion, automatically detect when changes touch subsystem code and verify documentation remains accurate. Subsystem invariants are validated, and any drift is surfaced for operator review.

The archaeological property is preserved: subsystem documents capture point-in-time knowledge about cross-cutting concerns, and their relationship to chunks provides traceability for how patterns evolved.
