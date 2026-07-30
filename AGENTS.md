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

Work that carries architectural intent is organized into "chunks" — discrete units of intent stored in `docs/chunks/`. Before creating a chunk, read [docs/trunk/CHUNKS.md](docs/trunk/CHUNKS.md) — especially principle 2. Intent-less work (typo fixes, dependency bumps, mechanical renames) bypasses the chunk system entirely.

Each chunk directory (e.g., `docs/chunks/feature_name/`) contains:

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

VE supports additional artifact types. When you encounter these situations, read the linked documentation:

- **Narratives** (`docs/narratives/`) - Multi-chunk initiatives with upfront decomposition. See: `docs/trunk/ARTIFACTS.md#narratives`
- **Investigations** (`docs/investigations/`) - Exploratory documents for understanding before acting. See: `docs/trunk/ARTIFACTS.md#investigations`
- **Subsystems** (`docs/subsystems/`) - Emergent architectural patterns. See: `docs/trunk/ARTIFACTS.md#subsystems`
- **Friction Log** (`docs/trunk/FRICTION.md`) - Accumulative ledger for pain points. See: `docs/trunk/ARTIFACTS.md#friction-log`
- **External Artifacts** (`external.yaml` files) - Cross-repository artifact pointers. See: `docs/trunk/EXTERNAL.md`
- **Orchestrator** (`ve orch`) - Parallel chunk execution across worktrees. See: `docs/trunk/ORCHESTRATOR.md`

## Code Backreferences

Source code may contain backreference comments linking to documentation:

```python
# Subsystem: docs/subsystems/template_system - Unified template rendering
# Chunk: docs/chunks/auth_refactor - Authentication system redesign
```

When you see these, read the referenced artifact to understand context.

See: `docs/trunk/ARTIFACTS.md#code-backreferences` for valid types and usage.


### Resolving a Backreference: Nearest Enclosing Tree

A bare reference (`docs/chunks/...`, `docs/narratives/...`, `docs/subsystems/...`)
resolves against the **nearest enclosing VE tree of the file that contains it** —
the closest ancestor directory of that file holding a `docs/trunk/`.

- **Not** your current working directory. The file's location decides, not yours.
- **Not** the repository root. In a repository containing several VE trees, the
  root tree is just another tree; it has no addressing privilege.

This matters when a repository holds more than one tree. If you read
`packages/libs/pybusiness/savings/realized.py` and it says
`# Subsystem: docs/subsystems/commitment_baseline`, that means
`packages/libs/pybusiness/docs/subsystems/commitment_baseline` when
`packages/libs/pybusiness/` is a VE tree. Resolving it from the repository root
can land you in a *different, real* directory of the same name — a wrong answer
that looks right. When in doubt, walk up from the file until you find
`docs/trunk/`, and read the reference there.

References that cross a tree boundary must say so explicitly rather than relying
on this rule.


## Creating Artifacts

**CRITICAL: Never manually create artifact files.** Do not use `mkdir` or write files directly to create GOAL.md, PLAN.md, or OVERVIEW.md files. Always use the appropriate creation command:

| Artifact Type | Creation Command |
|---------------|------------------|
| Chunk | `ve chunk create <name>` |
| Investigation | `ve investigation create <name>` |
| Narrative | `ve narrative create <name>` |
| Subsystem | `ve subsystem create <name>` |

Templates contain required frontmatter and structure; manually created files cause validation errors and broken workflows. If no creation command exists for an artifact type you need, ask the operator rather than creating files manually.

## Workflow Commands (Claude Code Plugin)

The workflow slash commands (`/chunk-create`, `/chunk-plan`, `/chunk-implement`, `/chunk-complete`, and the rest) are distributed via the **vibe-engineer Claude Code plugin** — they are not stored in this repository. Install them in Claude Code:

```
/plugin marketplace add netguy204/vibe-engineer
/plugin install vibe-engineer
```

Command documentation and updates travel with the plugin (`/plugin update vibe-engineer`). The `ve` CLI is installed separately (via uv/pip) and is the workflow engine the commands shell out to.

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