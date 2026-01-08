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
