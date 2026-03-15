

# Implementation Plan

## Approach

Add two new subsections to README.md under "Usage", positioned after "Cross-Repository Work" (ends ~line 138) and before "Development Setup" (starts ~line 143). Each section provides a concise introduction, the key commands, and a short example workflow.

Content is distilled from:
- `docs/trunk/ORCHESTRATOR.md` for the orchestrator section
- `.claude/commands/steward-*.md` skill definitions for the steward section

Per DEC-003, operator-facing commands belong in the README so users can discover them without digging into CLAUDE.md or source code.

**Testing**: This chunk is documentation-only (README prose). Per the testing philosophy, we do not test template prose content. No new tests are needed.

## Sequence

### Step 1: Write the Orchestrator section

Insert a new `### Orchestrator` section after "Cross-Repository Work" in README.md with:

- A 2-3 sentence introduction: the orchestrator runs FUTURE chunks in parallel across isolated git worktrees, handling planning, implementation, and completion autonomously.
- A table of the key commands operators use day-to-day: `ve orch inject`, `ve orch ps`, `ve orch attention`, `ve orch answer`.
- A short example workflow showing: create a FUTURE chunk → inject it → check status → handle attention items.
- A pointer to `docs/trunk/ORCHESTRATOR.md` for full reference.

Source material: `docs/trunk/ORCHESTRATOR.md` (key commands table, "Creating and Submitting FUTURE Chunks", "Handling Attention Items").

Location: `README.md`, inserted between the "Cross-Repository Work" section and "Development Setup".

### Step 2: Write the Steward section

Insert a new `### Steward` section immediately after the Orchestrator section with:

- A 2-3 sentence introduction: the steward is a long-lived agent that watches an inbound message channel, triages requests according to an SOP, and delegates work to the orchestrator.
- The setup flow: run `/steward-setup` to create `docs/trunk/STEWARD.md` via an interactive interview (name, channel, behavior mode).
- The three behavior modes in brief: `autonomous` (creates and implements chunks), `queue` (creates work items for human review), `custom` (operator-defined).
- The core loop: `/steward-watch` reads the SOP, watches the channel, triages inbound messages, posts outcomes to a changelog channel, and re-watches.
- Cross-project messaging: `/steward-send` lets an operator in Project A send a message to Project B's steward without context-switching.
- A short example workflow: setup → watch → send a message from another project.

Source material: `.claude/commands/steward-setup.md`, `.claude/commands/steward-watch.md`, `.claude/commands/steward-send.md`.

Location: `README.md`, immediately after the Orchestrator section.

### Step 3: Update code_paths in GOAL.md

Add `README.md` to the `code_paths` frontmatter in `docs/chunks/readme_orch_steward_docs/GOAL.md`.

### Step 4: Review and verify

- Confirm both new sections are placed correctly between "Cross-Repository Work" and "Development Setup"
- Confirm existing README content is unmodified
- Confirm example CLI commands are present in both sections
- Confirm no broken markdown formatting

## Risks and Open Questions

- **Steward detail level**: The steward is newer and less documented than the orchestrator. The README section should stay high-level, pointing users to `/steward-setup` to get started rather than trying to explain all internals. If the steward commands or behavior modes change, this section will need updating.
- **Section heading level**: The existing "Cross-Repository Work" uses `###` (h3). We should match that heading level for consistency within the "Usage" area.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->