# Design Decisions

<!--
This document logs significant design choices. Not every decision—just the
ones where there were real alternatives and the reasoning matters.

This is an append-only log. Don't delete old decisions; if a decision is
revisited, add a new entry that references the old one.

Each entry should be self-contained enough that someone can understand
the decision without reading the entire document.
-->

## Decision Log

<!--
Use the template below for each decision. Number decisions sequentially
(DEC-001, DEC-002, etc.) so they can be referenced from other documents.
-->

### DEC-001: [Short title describing the decision]

**Date**: YYYY-MM-DD

**Status**: ACCEPTED | SUPERSEDED BY DEC-XXX | UNDER REVIEW

**Decision**: 
<!--
One or two sentences stating what was decided. Be direct.
Example: "Use segment-based storage with fixed-size segments of 64MB."
-->

**Context**:
<!--
What situation prompted this decision? What constraints or requirements
were in play? This helps future readers understand why this decision
was being made at all.
-->

**Alternatives Considered**:
<!--
What other options were evaluated? For each, briefly note why it wasn't chosen.

Example:
- Single append-only file: Simpler, but compaction requires rewriting entire file
- Embedded database (RocksDB): Capable, but adds 10MB dependency and opaque internals
- Memory-mapped segments: Better read performance, but complex crash recovery
-->

**Rationale**:
<!--
Why was this alternative chosen over the others? What properties does it
optimize for? What tradeoffs does it accept?
-->

**Consequences**:
<!--
What follows from this decision? What becomes easier? What becomes harder?
What future decisions does this constrain or enable?
-->

**Revisit If**:
<!--
Under what conditions should this decision be reconsidered?
Example: "Revisit if segments larger than 1GB become common, or if we need
transactions across multiple messages."
-->

---

### DEC-001: uvx based cli utility

**Date**: 2026-01-07

**Status**: ACCEPTED

**Decision**: All of the capabilities of Vibe Engineer are accessible via a
command line utility that can be executed with no dependencies other than uvx. 

**Alternatives considered**:
- many separate scripts that are deeply embedded in the agentic tooling (like speckit)
- an installable cli

**Rationale**: The core documents that implement the Vibe Engineer workflow are
lightweight and can be orthogonal to the agents that consume them. We don't need
to make all of the decisions about how they're used at the same time, and can
provide the end user with more flexibility if we give them a command line
utility that makes implementing all or part of the workflow easy to do
consistently. 

**Revisit if**: If the core documents aren't actually orthogonal to the agents
that consume them, and it's not valuable to be able to produce them quickly
outside the intended workflow, then it might be useful to further constrain the
user to keep them on the intended workflow to avoid actions that cause problems. 

## DEC-002: git not assumed

**Date**: 2026-01-07

**Status**: ACCEPTED

**Decision**: The root of the Vibe engineering workflow document store is not
assumed to be a Git repository. 

**Alternatives considered**:
- all vibe engineering docs are tied to a single repository
- trunk vibe engineering docs are tied to an external system like linear

**Rationale**: My experience with being unable to use SpecKit and conductor for
work that was intrinsically multi-repository has convinced me that assuming that
a body of work is tied to a single repository is always wrong. 

By not assuming that the Vibe Engineer document root is in a Git repository, we
free the user to create short-lived Vibe engineering workflows against mature
projects spanning multiple repositories. 

**Revisit if**: If my natural usage of Vibe Engineering leads me to creating
only ephemeral trunks, then I haven't solved the problem.

---

### DEC-003: Document operator-facing commands in README

**Date**: 2026-01-08

**Status**: ACCEPTED

**Decision**: The README.md file should document commands that are part of an operator's standard workflow, making them discoverable without reading implementation details.

**Context**: As the project adds more slash commands and CLI utilities, operators need a clear reference for their day-to-day workflow. Currently, command discovery requires reading CLAUDE.md or exploring the codebase.

**Alternatives Considered**:
- Document commands only in CLAUDE.md: Keeps documentation minimal but requires operators to know where to look
- Create a separate COMMANDS.md: More comprehensive but adds another file to maintain
- Rely on `--help` output only: Standard for CLIs but doesn't show workflow context

**Rationale**: An operator should be able to understand their cohesive workflow by consuming just the README.md file. Commands that fit into the narrative of that workflow belong there, giving operators a single source for understanding how to use the system end-to-end.

**Consequences**: README.md becomes a living document that must be updated when workflow-relevant commands change. CLAUDE.md remains the authoritative source for agent instructions, while README serves human operators.

**Revisit If**: If the command surface grows large enough that README becomes unwieldy, consider a dedicated commands reference or generated documentation.

---

### DEC-004: Markdown references relative to project root

**Date**: 2026-01-08

**Status**: ACCEPTED

**Decision**: All file and directory references within markdown documentation files must be relative to the project root, not relative to the markdown file's location.

**Context**: Agents working within the project need to navigate file references reliably. When an agent reads a markdown file that references `src/utils/foo.ts`, it must be able to resolve that path confidently from its current working directory (the project root).

**Alternatives Considered**:
- Relative to the markdown file's location: Common in documentation but requires agents to compute paths from the file's directory
- Absolute paths: Unambiguous but not portable across machines
- Mixed approach: Flexible but inconsistent and error-prone

**Rationale**: Agents typically operate from the project root as their working directory. Project-root-relative paths allow direct resolution without path manipulation. This makes references predictable and reduces errors when agents follow documentation links.

**Consequences**: Authors must think in terms of project root when writing references (e.g., `docs/chunks/0001/GOAL.md` instead of `../chunks/0001/GOAL.md`). Agents navigating from task directories will need special handling, which is deferred to a future decision.

**Revisit If**: If task directory navigation becomes a significant use case that this convention makes awkward, or if tooling emerges that makes file-relative paths easier for agents to handle.

---

### DEC-005: Commands do not prescribe git operations

**Date**: 2026-01-11

**Status**: ACCEPTED

**Decision**: Vibe Engineering commands and slash command templates must not prescribe when or how git operations (commits, pushes, etc.) occur. Git history management is the operator's responsibility.

**Context**: As DEC-002 establishes, vibe engineering does not assume a git repository. Beyond that assumption, even when git is present, different operators have different commit strategies: some prefer atomic commits per feature, others squash, others use conventional commits, etc. Prescribing commit behavior couples the workflow to operator preferences it has no business dictating.

**Alternatives Considered**:
- Include commit steps in slash commands: Convenient but assumes git and imposes commit granularity
- Make commit steps optional via flags: Adds complexity and still implies a default behavior
- Leave git operations entirely to the operator: Respects autonomy and DEC-002

**Rationale**: The vibe engineering workflow produces artifacts (chunks, narratives, investigations, subsystems). How those artifacts flow through version control is orthogonal to the workflow itself. Operators may:
- Not use git at all
- Use git but prefer manual commit timing
- Use automated tooling that handles commits
- Work across multiple repositories with different strategies

By staying silent on git operations, ve commands remain composable with any version control strategy.

**Consequences**:
- Slash command templates must not include commit/push steps
- CLI commands should not auto-commit (they may check for clean working tree as a safety measure, but that's validation, not prescription)
- Documentation may mention git as one recovery option among others, but should not present it as the assumed workflow

**Revisit If**: If a compelling use case emerges where ve-managed commits provide significant value that cannot be achieved through external tooling.

---

### DEC-006: External references always resolve to HEAD

**Date**: 2026-01-23

**Status**: ACCEPTED

**Decision**: External artifact references (external.yaml) always resolve to the current HEAD of the tracked branch. The `pinned` field is deprecated and ignored. The `ve sync` command and `--at-pinned` option are removed.

**Context**: The original design included a `pinned` SHA field in external.yaml files and a `ve sync` command to update these SHAs. This was intended to provide point-in-time archaeology - the ability to see what an external artifact looked like when the reference was created.

However, in practice:
1. Archaeology via pinned SHA was never actually used
2. The sync command added operational complexity
3. The mental model was confusing (when to sync? what happens if you forget?)
4. The simpler model ("external references point at latest") matches user expectations

**Alternatives Considered**:
- Keep pinned SHAs and sync: Original design, but adds complexity without demonstrated value
- Remove pinned but keep sync for other purposes: No other purpose was identified
- Make pinned optional per-reference: Adds complexity for marginal benefit

**Rationale**: External references exist to share artifacts across repositories. The common use case is "I want to see the current state of this artifact in another repo." Point-in-time archaeology, while theoretically useful, was never used in practice and can be achieved through git history if needed.

By always resolving to HEAD, we:
- Simplify the mental model (references are always current)
- Eliminate the sync ceremony
- Remove dead code and reduce maintenance burden
- Make the system more predictable

**Consequences**:
- External references always show current content
- No sync step required when external content changes
- Historical archaeology requires git checkout, not ve tooling
- The `pinned` field in existing external.yaml files is parsed but ignored for backward compatibility

**Revisit If**: A concrete use case emerges where point-in-time artifact snapshots are needed and git history is insufficient.

---

### DEC-007: Orchestrator Daemon with HTTP API

**Date**: 2026-02-07

**Status**: ACCEPTED

**Decision**: The orchestrator runs as a persistent daemon process, exposing a Unix socket for local CLI communication and a TCP port for the browser-based dashboard.

**Context**: The orchestrator needs to coordinate long-running work across multiple CLI invocations. Chunks may take minutes to hours to complete, and the orchestrator must track state, manage worktrees, and report progress across these spans.

**Alternatives Considered**:
- Direct CLI execution (no daemon): Each `ve orch inject` would run to completion. This prevents parallelism across invocations and loses state between commands.
- Background jobs with polling: CLI spawns background processes and polls for status. Complex state management, race conditions, and no central coordination.
- Separate microservice: Full server deployment with Docker/systemd. Significant operational overhead for a developer tool.

**Rationale**: A daemon provides a single point of coordination while remaining lightweight. The Unix socket enables fast local IPC for CLI commands (`ve orch status`, `ve orch inject`). The TCP port enables the browser dashboard to display real-time progress and allows programmatic access for CI integration.

**Consequences**:
- The daemon must be started before orchestrator commands work (`ve orch start`)
- State persists across CLI invocations
- Dashboard can show live progress via HTTP polling or WebSocket
- Shutdown requires explicit `ve orch stop` or process termination

**Revisit If**: If the daemon model proves too heavy for casual use, consider an on-demand spawn model where the daemon starts automatically on first use and shuts down after idle timeout.

---

### DEC-008: Pydantic for Frontmatter Models

**Date**: 2026-02-07

**Status**: ACCEPTED

**Decision**: Use Pydantic `BaseModel` for all frontmatter schema definitions, including chunk, subsystem, investigation, and narrative frontmatter.

**Context**: Frontmatter validation is central to the ve workflow. Invalid frontmatter should produce clear error messages. The schema must be enforceable at parse time and serializable back to YAML.

**Alternatives Considered**:
- Manual dict validation: Parse YAML to dict, validate keys manually. Error-prone, verbose, inconsistent error messages across artifact types.
- dataclasses with validators: Python dataclasses with custom `__post_init__` validation. Less powerful validation primitives, no built-in serialization.
- marshmallow: Established schema library. More verbose than Pydantic, less Pythonic field definition syntax, weaker IDE support.

**Rationale**: Pydantic provides type coercion, validation, and serialization in one package. `BaseModel` inheritance enables shared behavior (e.g., common fields across artifact types). `StrEnum` integration provides type-safe status values. Validation errors include field paths and expected types, making debugging straightforward.

**Consequences**:
- Pydantic is a runtime dependency
- Schema changes require updating model definitions
- Custom validators can be added for complex rules (e.g., status transition validation)
- YAML round-tripping works via `model.model_dump()` and `ruamel.yaml`

**Revisit If**: If Pydantic's validation overhead becomes measurable in large projects (1000+ chunks), or if a lighter-weight alternative emerges that provides comparable developer experience.

---

### DEC-009: ArtifactManager Template Method Pattern

**Date**: 2026-02-07

**Status**: ACCEPTED

**Decision**: Use the Template Method pattern via an `ArtifactManager` abstract base class to share common artifact lifecycle operations across chunks, narratives, investigations, and subsystems.

**Context**: The four artifact types share common operations: parse frontmatter, validate status, enumerate artifacts in a directory, update status. Each artifact type has its own directory structure and frontmatter schema, but the lifecycle algorithm is the same.

**Alternatives Considered**:
- Composition with helper functions: Each manager imports and calls shared functions. Leads to duplicated method calls and inconsistent signatures across managers.
- Mixin classes: Define mixins for parse, validate, enumerate. Complex inheritance hierarchy, harder to reason about method resolution order.
- Standalone functions per artifact type: Fully separate implementations for each artifact. Significant code duplication, divergent behavior over time.

**Rationale**: Template Method captures the shared algorithm (enumerate directory, parse file, validate frontmatter, return typed result) while allowing subclasses to define artifact-specific configuration via abstract properties. Subclasses define `artifact_dir`, `frontmatter_model`, and `file_name` properties; the base class provides `list()`, `get()`, and `validate()` methods.

**Consequences**:
- New artifact types require only a subclass with three property definitions
- Shared behavior changes propagate to all artifact types automatically
- Testing can focus on the base class algorithm and subclass configuration
- The pattern is explicit—reading `ArtifactManager` reveals the lifecycle contract

**Revisit If**: If artifact types diverge significantly in their lifecycle needs (e.g., one needs async operations, another needs caching), the Template Method may become a constraint rather than an enabler.
