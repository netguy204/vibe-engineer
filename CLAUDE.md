# Vibe Engineering Workflow

This project uses a documentation-driven development workflow. As an agent working on this codebase, familiarize yourself with these key locations.

## Project Documentation (`docs/trunk/`)

The `docs/trunk/` directory contains the stable project documentation:

- **GOAL.md** - The project's problem statement, required properties, constraints, and success criteria. This is the anchor for all work.
- **SPEC.md** - Technical specification describing how the project achieves its goals.
- **DECISIONS.md** - Architectural decision records (ADRs) documenting significant choices and their rationale.
- **TESTING_PHILOSOPHY.md** - The project's approach to testing and quality assurance.

Read GOAL.md first to understand the project's purpose before making changes.

## Chunks (`docs/chunks/`)

Work is organized into "chunks" - discrete units of implementation stored in `docs/chunks/`. Each chunk directory (e.g., `docs/chunks/feature_name/`) contains:

- **GOAL.md** - What this chunk accomplishes and its success criteria
- **PLAN.md** - Technical breakdown of how the chunk will be implemented

To understand recent work, use `ve chunk list --latest` to find the most recently created chunk.

### Chunk Lifecycle

1. **Create** - Define the work and refine the goal
2. **Plan** - Break down the implementation approach
3. **Implement** - Write the code
4. **Complete** - Update code references and mark done

### Chunk Frontmatter References

Chunk GOAL.md files may reference other artifact types in their frontmatter:

- **narrative**: References a narrative directory (e.g., `investigations`) that this chunk helps implement
- **subsystems**: List of subsystem relationships indicating which subsystems this chunk implements or uses

When you see these references, read the referenced artifact to understand the broader context.

## Narratives (`docs/narratives/`)

Narratives are multi-chunk initiatives that capture a high-level ambition decomposed into implementation steps. Each narrative directory contains an OVERVIEW.md with:

- **Advances Trunk Goal** - How this narrative advances the project's goals
- **Chunks** - List of chunk prompts and their corresponding chunk directories

When a chunk references a narrative, read the narrative's OVERVIEW.md to understand the larger initiative the chunk belongs to.

## Subsystems (`docs/subsystems/`)

Subsystems document emergent architectural patterns discovered in the codebase. Each subsystem directory contains an OVERVIEW.md describing:

- **Intent** - What the subsystem accomplishes
- **Scope** - What's in and out of scope
- **Invariants** - Rules that must always hold
- **Code References** - Symbolic references to implementations

Subsystem status values: `DISCOVERING`, `DOCUMENTED`, `REFACTORING`, `STABLE`, `DEPRECATED`

**When to check subsystems**: Before implementing patterns that might already exist in the codebase, check `docs/subsystems/` for existing documentation. Subsystems capture how things *should* work, including known inconsistencies.

**Subsystem status affects your behavior**:
- `DISCOVERING` / `DOCUMENTED`: The pattern is documented but may have inconsistencies. Do NOT expand chunk scope to fix inconsistencies unless explicitly asked.
- `REFACTORING`: Active consolidation work. You MAY expand scope for consistency improvements.
- `STABLE`: The subsystem is authoritative. Follow its patterns for new code.
- `DEPRECATED`: Avoid using this pattern; may suggest alternatives.

When a chunk references a subsystem with relationship `implements`, the chunk contributes code to that subsystem. When the relationship is `uses`, the chunk depends on the subsystem's patterns.

## Investigations (`docs/investigations/`)

Investigations are exploratory documents for understanding something before committing to action—either diagnosing an issue or exploring a concept. Each investigation contains an OVERVIEW.md with:

- **Trigger** - What prompted the investigation
- **Success Criteria** - What "done" looks like
- **Testable Hypotheses** - Beliefs to verify or falsify
- **Proposed Chunks** - Work items that emerge from findings

Investigation status values: `ONGOING`, `SOLVED`, `NOTED`, `DEFERRED`

## Available Commands

Use these slash commands for artifact management:

- `/chunk-create` - Create a new chunk and refine its goal
- `/chunk-plan` - Create a technical plan for the current chunk
- `/chunk-implement` - Implement the current chunk
- `/chunk-complete` - Mark a chunk complete and update references
- `/cluster-rename` - Batch-rename chunks matching a prefix (e.g., `/cluster-rename old_prefix new_prefix`)
- `/narrative-create` - Create a new narrative for multi-chunk initiatives
- `/subsystem-discover` - Document an emergent architectural pattern
- `/investigation-create` - Start a new investigation (or redirect to chunk if simple)

## Getting Started

1. Read `docs/trunk/GOAL.md` to understand the project
2. Check `docs/chunks/` for recent and in-progress work
3. Use `/chunk-create` to start new work

## Code Backreferences

Source code may contain backreference comments that link code back to the documentation that created or governs it:

```python
# Chunk: docs/chunks/symbolic_code_refs - Symbolic code reference format
# Subsystem: docs/subsystems/template_system - Unified template rendering
```

**What backreferences mean:**
- `# Chunk: ...` - This code was created or modified by the referenced chunk. Read the chunk's GOAL.md for business context.
- `# Subsystem: ...` - This code is part of a documented subsystem. Read the subsystem's OVERVIEW.md for patterns and invariants.

**When you see backreferences:** Follow the path to understand why the code exists. Multiple chunk references indicate code that evolved over several iterations.

**When implementing code:** Add backreference comments at the appropriate semantic level (module, class, or method) to help future agents trace code back to its documentation.