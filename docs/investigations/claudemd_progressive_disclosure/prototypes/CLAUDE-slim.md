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

To understand recent work, use `ve chunk list --recent` to see recently completed chunks, or `--current` to find the chunk currently being implemented.

### Chunk Lifecycle

1. **Create** - Define the work and refine the goal
2. **Plan** - Break down the implementation approach
3. **Implement** - Write the code
4. **Complete** - Update code references and mark done

### Chunk Naming Conventions

Name chunks by the **initiative** they advance, not the artifact type or action verb. Good prefixes are domain concepts that group related work: `ordering_`, `taskdir_`, `template_`. Avoid generic prefixes: `chunk_`, `fix_`, `cli_`, `api_`, `util_`.

## Extended Artifacts

VE supports additional artifact types for different scenarios. When you encounter these situations, read the linked documentation:

### Narratives (`docs/narratives/`)

Multi-chunk initiatives with upfront decomposition. **Read when**: planning large features, working on chunks that reference a narrative, or decomposing big ambitions.

See: `docs/trunk/ARTIFACTS.md#narratives`

### Investigations (`docs/investigations/`)

Exploratory documents for understanding before acting. **Read when**: diagnosing issues, exploring unfamiliar code, or validating hypotheses before committing to implementation.

See: `docs/trunk/ARTIFACTS.md#investigations`

### Subsystems (`docs/subsystems/`)

Emergent architectural patterns. **Read when**: implementing patterns that might already exist, or when code backreferences mention a subsystem.

See: `docs/trunk/ARTIFACTS.md#subsystems`

### Friction Log (`docs/trunk/FRICTION.md`)

Accumulative ledger for pain points. **Read when**: capturing friction, or when friction patterns suggest work.

### External Artifacts

Cross-repository artifact pointers. **Read when**: encountering `external.yaml` files or working in multi-repo contexts.

See: `docs/trunk/EXTERNAL.md`

## Orchestrator (`ve orch`)

Manages parallel chunk execution across worktrees. **Read when**:
- User mentions "background", "parallel", or "orchestrator"
- Working with FUTURE chunks
- Managing concurrent workstreams

See: `docs/trunk/ORCHESTRATOR.md`
Commands: `/orchestrator-submit-future`, `/orchestrator-investigate`

## Code Backreferences

Source code may contain backreference comments linking to documentation:

```python
# Subsystem: docs/subsystems/template_system - Unified template rendering
# Chunk: docs/chunks/auth_refactor - Authentication system redesign
```

When you see these, read the referenced artifact to understand context.

## Available Commands

Use these slash commands for artifact management:

- `/chunk-create` - Create a new chunk and refine its goal
- `/chunk-plan` - Create a technical plan for the current chunk
- `/chunk-implement` - Implement the current chunk
- `/chunk-complete` - Mark a chunk complete and update references
- `/narrative-create` - Create a new narrative for multi-chunk initiatives
- `/subsystem-discover` - Document an emergent architectural pattern
- `/investigation-create` - Start a new investigation
- `/friction-log` - Capture a friction point

## Getting Started

1. Read `docs/trunk/GOAL.md` to understand the project
2. Check `docs/chunks/` for recent and in-progress work
3. Use `/chunk-create` to start new work

## Learning Philosophy

You don't need to learn everything upfront. Vibe engineering is designed to meet you where you are:

1. **Start with chunks** - The create → plan → implement → complete cycle gives immediate, tangible progress.
2. **Discover larger artifacts when needed** - Narratives emerge when work is too big for one chunk. Subsystems emerge when you keep touching the same patterns.
3. **Graduate to orchestration** - When managing parallel workflows, the orchestrator automates scheduling and conflict detection.

The documentation teaches itself: follow backreferences in code to discover the subsystems that govern it.
