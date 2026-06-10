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

---

### DEC-010: Plugin-based distribution replaces render-based distribution

**Date**: 2026-06-09

**Status**: ACCEPTED

**Decision**: Agent-facing workflow content (commands, skills, hooks, subagents) is distributed as a Claude Code plugin hosted in this repository. `.claude-plugin/plugin.json` defines the plugin, `.claude-plugin/marketplace.json` makes the repository an installable marketplace, and the plugin content lives in `commands/`, `skills/`, `agents/`, and `hooks/` at the repository root. This fully replaces the render-based channel where `ve init` wrote 36 Jinja2-rendered command skills into each consuming repository's `.agents/skills/` directory with `.claude/commands/` symlinks. The `ve` Python CLI remains separately installed (uv/pip) and remains the workflow engine; the plugin is the agent-facing layer that shells out to it.

**Context**: Before Claude Code had a plugin system, the only way to put workflow commands in front of an agent was to render them into each project. That approach has accumulated real costs: every consuming repository carries ~40 rendered files and symlinks that are not project-specific content; command updates only reach projects when someone re-runs `ve init` and commits the churn; and templates branch on `task_context`/`ve_config` at render time, so the same logical command exists in multiple rendered variants across repositories. Claude Code's plugin and marketplace system now provides a native distribution surface: users run `/plugin marketplace add <owner>/vibe-engineer` followed by `/plugin install vibe-engineer`, and command updates arrive through the plugin manager.

**Alternatives Considered**:
- *Dual-mode (plugin alongside rendering)*: Keep `ve init` rendering as a fallback while also shipping the plugin. Rejected — two distribution channels means two sources of truth for every command, doubling maintenance and guaranteeing drift. The operator chose full replacement.
- *Separate plugin repository*: A dedicated vibe-engineer-plugin repo that this repo publishes into. Rejected — co-versioning the plugin with the Python source keeps a single history, and marketplace.json can point at this repository directly; a publish pipeline adds moving parts with no current benefit.
- *MCP server exposing ve operations*: Expose chunk list / board send / etc. as MCP tools instead of shelling out. Rejected as out of scope — commands shell out to the `ve` CLI, which must be installed anyway; an MCP layer adds surface without removing that dependency.

**Rationale**: Native plugin distribution makes adoption a per-user install and updates a plugin-manager concern, leaving only genuinely project-owned documentation in consuming repositories. This directly serves the trunk goal's adoption properties: retrofitting a legacy project no longer means committing ~40 rendered files, and engineers who don't use the workflow no longer carry its artifacts in their checkouts. Hosting the plugin at the repository root (marketplace `source: "./"`) keeps the plugin and the CLI co-versioned with zero release machinery.

**Consequences**:
- Command distribution is tied to Claude Code's plugin system. The agent-agnostic `.agents/skills/` (agentskills.io) layout is dropped; non-Claude-Code agent support narrows to the AGENTS.md pointer file. This trade-off is accepted; if multi-agent support becomes a requirement later, a render channel can be reintroduced from the plugin sources.
- Command and skill updates reach users through plugin updates; re-running `ve init` ceases to be part of the upgrade story for commands.
- Plugin command files are static, so render-time conditionals must become runtime context detection (`.ve-task.yaml`, `.ve-config.yaml`) — established by the plugin_runtime_context chunk.
- `ve init` shrinks to project scaffolding only (trunk docs, artifact directories, .gitignore hygiene) — the plugin_init_slimdown chunk.
- A plugin install pulls the whole repository (Python source included), making installs larger than a dedicated plugin repo would be. Accepted for co-versioning simplicity.
- The plugin version and the Python package version can drift; a version-compatibility policy is defined by the plugin_session_hooks chunk.

**Revisit If**: Multi-agent (non-Claude-Code) support becomes a requirement, plugin install size becomes a practical friction point, or Claude Code's plugin system changes in ways that break repository-root marketplace hosting.

### DEC-011: Plugin/CLI version-compatibility policy — co-versioned, major.minor must match

**Date**: 2026-06-09

**Status**: ACCEPTED

**Decision**: The Claude Code plugin and the `ve` Python package are co-versioned: `.claude-plugin/plugin.json` `version` must equal the `pyproject.toml` `version` at every release (enforced by a test). An installed plugin and an installed CLI are **compatible** when their `major.minor` version components match; patch-level drift is silently tolerated. The version source on the CLI side is the new `ve --version` flag (click `version_option` reading installed package metadata). The plugin's SessionStart hook enforces the policy advisorily: a `major.minor` mismatch produces a single warning line naming both versions; a CLI that does not support `--version` predates this policy and is treated as an unknown-version mismatch with the same one-line warning. Warnings never block — the hook always exits 0.

**Context**: DEC-010 moved agent-facing content into a plugin while the `ve` CLI remains separately installed via uv/pip, so the two halves can drift: a user can update the plugin without upgrading the CLI, or vice versa. The plugin's commands and hooks shell out to `ve` and depend on its CLI surface (flags, subcommands, output formats). DEC-010 explicitly deferred the compatibility policy to the plugin_session_hooks chunk. The CLI previously had no version flag at all (`ve --version` exited 2), so any policy needed a version source first.

**Alternatives Considered**:
- *Supported-range declaration*: plugin.json (or a sidecar file) declares a supported ve version range (e.g., `>=0.2,<0.3`). Rejected — since both halves live in this repository and release together, a range adds a second thing to maintain that co-versioning makes redundant.
- *Exact-version match*: require full `major.minor.patch` equality. Rejected — patch releases fix bugs without changing the CLI surface; warning on every patch drift trains users to ignore the warning.
- *Hard failure on mismatch*: block the session or disable plugin commands. Rejected — a stale CLI is usually still mostly functional, and a session-start hook that blocks work is worse than the drift it guards against.
- *No policy (silent drift)*: rejected — DEC-010's consequence list called the drift risk out explicitly, and a one-line advisory warning is nearly free.

**Rationale**: Co-versioning is the cheapest honest policy for a single repository that ships both artifacts: there is exactly one version number to reason about, and "matching minor" maps directly onto how the CLI surface actually evolves (new commands and flags land in minor releases; patches do not change the contract). Treating a `--version`-less CLI as a mismatch gives pre-0.2.x installs a correct upgrade nudge without special-casing.

**Consequences**:
- Every release must bump `plugin.json` and `pyproject.toml` together; `tests/test_session_hook.py` fails the build if they disagree.
- The `ve` CLI now has a `--version` flag; downstream tooling may rely on its `ve, version X.Y.Z` output format.
- Users see at most one warning line per session on drift, with the upgrade command inline (`uv tool install --upgrade vibe-engineer` or a plugin update).
- A breaking CLI change within a minor release would evade the policy; the policy assumes semver discipline in this repository.

**Revisit If**: The plugin and CLI move to separate repositories or release cadences, the plugin grows features that genuinely need a version *range* (e.g., supporting older CLIs deliberately), or warning fatigue is observed in practice.

### DEC-012: Session-local parallel execution preferred over orchestrator background execution

**Status**: Accepted (2026-06-09)

**Context**: The orchestrator (`ve orch`) executes chunks as background
agents via the Agent SDK. Anthropic's billing change requires Agent SDK
consumers to pay standard API token rates, while sub-agents spawned inside an
interactive Claude Code session are covered by the operator's subscription
(Max plan). Separately, the claude_plugin_port narrative was executed
end-to-end with an interactive-session pattern — dependency-ordered waves of
sub-agents, git-worktree isolation for parallel chunks, per-wave merge-back
and verification — and the operator judged that execution preferable to the
orchestrator's worktree/injection machinery.

**Decision**: Session-local parallel execution via `/chunk-execute-all`
(waves of chunk-executor sub-agents, worktree isolation, per-wave merges) is
the preferred way to execute chunk batches. The orchestrator remains
functional but is no longer the recommended path; its deprecation is
contemplated as future work once `/chunk-execute-all` has proven itself on
real batches.

**Consequences**:
- Chunk batches execute inside the operator's session and bill under their
  subscription rather than at API token rates.
- The conflict oracle is not consulted on this path: `depends_on: null`
  chunks are serialized conservatively by the executing agent's own analysis.
- Execution occupies the interactive session for the duration of the run
  (waves are observable, and the operator is consulted at failures), whereas
  the orchestrator ran fully detached.
- Deprecating the orchestrator would follow the close-the-on-ramp pattern:
  stop recommending and injecting first, remove machinery later.

**Alternatives considered**:
- *Keep the orchestrator as the primary batch executor*: rejected — standard
  token rates make unattended SDK execution materially more expensive than
  subscription-covered session execution, and the operator prefers the
  session-local workflow.
- *Deprecate the orchestrator immediately*: rejected for now — large surface
  (daemon, scheduler, merge machinery, docs) and `/chunk-execute-all` should
  prove itself first.
