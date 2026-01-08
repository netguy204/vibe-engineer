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

Work is organized into "chunks" - discrete units of implementation stored in `docs/chunks/`. Each chunk directory (e.g., `docs/chunks/0001-feature_name/`) contains:

- **GOAL.md** - What this chunk accomplishes and its success criteria
- **PLAN.md** - Technical breakdown of how the chunk will be implemented

Chunks are numbered sequentially. To understand recent work, read the highest-numbered chunk's GOAL.md.

### Chunk Lifecycle

1. **Create** - Define the work and refine the goal
2. **Plan** - Break down the implementation approach
3. **Implement** - Write the code
4. **Complete** - Update code references and mark done

## Available Commands

Use these slash commands for chunk management:

- `/chunk-create` - Create a new chunk and refine its goal
- `/chunk-plan` - Create a technical plan for the current chunk
- `/chunk-complete` - Mark a chunk complete and update references
- `/chunk-update-references` - Update code references in a chunk's GOAL.md

## Getting Started

1. Read `docs/trunk/GOAL.md` to understand the project
2. Check `docs/chunks/` for recent and in-progress work
3. Use `/chunk-create` to start new work
