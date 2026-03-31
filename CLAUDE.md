<!-- VE:MANAGED:START -->
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

To understand recent work, use `ve chunk list --current` to find the currently IMPLEMENTING chunk, or `ve chunk list --recent` to see the 10 most recently completed chunks.

### Chunk Lifecycle

1. **Create** - Define the work and refine the goal
2. **Plan** - Break down the implementation approach
3. **Implement** - Write the code
4. **Complete** - Update code references and mark done


### Chunk Naming Conventions

Name chunks by the **initiative** they advance, not the artifact type or action verb. Good prefixes are domain concepts that group related work: `ordering_`, `taskdir_`, `template_`. Avoid generic prefixes: `chunk_`, `fix_`, `cli_`, `api_`, `util_`.

### Chunk Frontmatter References

Chunk GOAL.md files may reference other artifacts in their frontmatter (`narrative`, `investigation`, `friction_entries`). When you see these references, read the referenced artifact to understand the broader context.

See: `docs/trunk/ARTIFACTS.md` for details on each artifact type.

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

See: `docs/trunk/ARTIFACTS.md#friction-log`



### External Artifacts

Cross-repository artifact pointers (`external.yaml` files). **Read when**: encountering `external.yaml` files or working in multi-repo contexts.

See: `docs/trunk/EXTERNAL.md`


## Orchestrator (`ve orch`)

Manages parallel chunk execution across worktrees. **Read when**:
- User mentions "background", "parallel", or "orchestrator"
- Working with FUTURE chunks
- Managing concurrent workstreams

See: `docs/trunk/ORCHESTRATOR.md`

Commands: `/orchestrator-inject`, `/orchestrator-submit-future`, `/orchestrator-investigate`, `/orchestrator-monitor`

## Code Backreferences

Source code may contain backreference comments linking to documentation:

```python
# Subsystem: docs/subsystems/template_system - Unified template rendering
# Chunk: docs/chunks/auth_refactor - Authentication system redesign
```

When you see these, read the referenced artifact to understand context.

See: `docs/trunk/ARTIFACTS.md#code-backreferences` for valid types and usage.

## Available Commands

Use these slash commands for artifact management:

- `/chunk-create` - Create a new chunk and refine its goal
- `/chunk-plan` - Create a technical plan for the current chunk
- `/chunk-implement` - Implement the current chunk

- `/chunk-execute` - Run a chunk's full lifecycle (plan → implement → complete) in the current session

- `/chunk-review` - Review chunk implementation for alignment with documented intent
- `/chunk-complete` - Mark a chunk complete and update references

- `/cluster-rename` - Batch-rename chunks matching a prefix
- `/narrative-create` - Create a new narrative for multi-chunk initiatives
- `/narrative-compact` - Consolidate multiple chunks into a narrative
- `/subsystem-discover` - Document an emergent architectural pattern
- `/investigation-create` - Start a new investigation
- `/friction-log` - Capture a friction point

- `/validate-fix` - Iteratively fix validation errors until clean


### Steward

- `/steward-setup` - Set up a project steward via interactive interview
- `/steward-watch` - Run the steward watch-respond-rewatch loop
- `/steward-send` - Send a message to a project's steward
- `/steward-changelog` - Watch a project's changelog channel

- `/swarm-monitor` - Monitor all changelog channels in a swarm

- `/swarm-request-response` - Send a request and wait for the response on a channel pair


#### Cross-project messaging

To send a message to another project's steward, use the channel naming convention `<target-project>-steward`, where `<target-project>` is the project whose steward you're addressing — **not** the project you're sending from.

```
ve board send <target-project>-steward "<message>" --swarm <swarm_id>
```

For example, to tell the `vibe-engineer` steward something from any project in the swarm, send to `vibe-engineer-steward`:

```
ve board send vibe-engineer-steward "Requested API change is ready" --swarm my_swarm
```

**Common mistake:** Agents often find their local `STEWARD.md`, read its `channel` field, and send to their *own* project's steward channel instead of the target project's channel. Always derive the channel name from the **target** project, not from your local steward configuration.


## Creating Artifacts

**CRITICAL: Never manually create artifact files.** Do not use `mkdir` or write files directly to create GOAL.md, PLAN.md, or OVERVIEW.md files. Always use the appropriate creation command.

| Artifact Type | Creation Command | Slash Command |
|---------------|------------------|---------------|
| Chunk | `ve chunk create <name>` | `/chunk-create` |
| Investigation | `ve investigation create <name>` | `/investigation-create` |
| Narrative | `ve narrative create <name>` | `/narrative-create` |
| Subsystem | `ve subsystem create <name>` | `/subsystem-discover` |

**Why this matters:**

- Templates contain required YAML frontmatter with correct schema fields
- Templates include structural guidance and placeholder content
- Manually created files often miss required fields, causing validation errors and broken workflows
- The creation commands handle directory structure, initial status, and cross-references

If you encounter a situation where no creation command exists for an artifact type you need, ask the operator rather than creating files manually.

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

<!-- VE:MANAGED:END -->

## Development

This project uses UV for package management. Run tests with `uv run pytest tests/`.

**IMPORTANT**: When working on the vibe-engineer codebase, always run the `ve` command under UV to use the development version:

```bash
# Correct - uses development version
uv run ve init
uv run ve chunk list

# Incorrect - may use globally installed version
ve init
ve chunk list
```

This ensures you're testing your changes with the local development code, not a previously installed version.

## Template Editing Workflow

This is the vibe-engineer source repository. Many files are **rendered from Jinja2 templates** and should not be edited directly.

### Rendered Files and Their Sources

| Rendered File | Source Template |
|---------------|-----------------|
| `CLAUDE.md` | `src/templates/claude/CLAUDE.md.jinja2` |
| `.claude/commands/*.md` | `src/templates/commands/*.jinja2` |

### Editing Workflow

1. **Edit the source template** in `src/templates/`
2. **Re-render** by running `ve init`
3. **Verify** the rendered output matches expectations

### Why This Matters

Edits to rendered files will be **lost** when templates are re-rendered. Always modify the source template instead.

If you see a rendered file with an `AUTO-GENERATED` header, that file is managed by the template system and should not be edited directly.

## Design System
Always read DESIGN.md before making any visual or UI decisions.
All font choices, colors, spacing, and aesthetic direction are defined there.
Do not deviate without explicit user approval.
In QA mode, flag any code that doesn't match DESIGN.md.