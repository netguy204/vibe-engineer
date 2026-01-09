---
status: ACTIVE
advances_trunk_goal: "Problem Statement: deeply understanding the goal and the correctness constraints around the project are the entire engineering problem that remains"
chunks:
  - prompt: "Create the investigation OVERVIEW.md template in src/templates/investigation/, following the patterns established by narrative and subsystem templates. Include sections for: trigger, success criteria, testable hypotheses, exploration log, findings, proposed chunks, and resolution rationale."
    chunk_directory: "0027-investigation_template"
  - prompt: "Add CLI commands for investigations: `ve investigation create <name>` to scaffold a new investigation directory, and `ve investigation list` to show investigations by status. Create the /investigation-create slash command to guide collaborative refinement of a new investigation, with scale assessment to propose chunks for simple tasks."
    chunk_directory: "0029-investigation_commands"
---

## Advances Trunk Goal

This narrative advances the Problem Statement's core thesis: that understanding
the goal and correctness constraints is the engineering problem. Investigations
provide a structured way to explore unknowns—whether issues in the system or
potential new concepts—before committing to implementation. They capture the
learning process itself, ensuring that even "no action" decisions are documented
and defensible.

## Driving Ambition

Add investigations as a first-class artifact type in the vibe engineering
workflow. An investigation is an exploratory document created when an operator
wants to understand something before committing to action—either exploring an
issue with the system or exploring a potential new concept.

Unlike narratives (which start with a known ambition and decompose into chunks)
or subsystems (which document emergent patterns), investigations start with
uncertainty. They may or may not produce chunks. The value is in the structured
exploration and the captured learning.

Key design decisions from collaborative refinement:

**States:**
- ONGOING - investigation in progress
- SOLVED - investigation led to action; chunks were proposed/created
- NOTED - we found something but chose not to act (closed, won't pursue)
- DEFERRED - we chose not to act now, but may revisit later

**Structure:**
- No structural distinction between "issue" and "concept" investigations
- The trigger naturally captures whether it's a problem or an opportunity
- Template guidance suggests different exploration approaches without mandating

**Testability emphasis:**
- The template should nudge toward identifying testable hypotheses
- Encourage objective verification where possible (measurements, prototypes, spikes)
- Distinguish between verified findings and opinions/hypotheses in conclusions

**Relationship to chunks:**
- Investigations list chunk prompts (like narratives) rather than directly creating chunks
- The operator decides which proposed chunks to actually create via /chunk-create

**Scale guidance (for /investigation-create command):**

The slash command should help users assess whether a full investigation is warranted.
Investigations add value when the learning process itself is worth preserving. They're
overhead when the answer is quick and obvious.

*Signs a full investigation IS warranted:*
- Root cause is unclear; multiple hypotheses need testing
- The issue spans multiple systems or has unclear boundaries
- The decision has architectural implications worth documenting
- "No action" is a legitimate outcome that should be defensible later
- The exploration will take multiple sessions or involve others
- Similar questions might arise again; the learning should be reusable

*Signs a lighter-weight approach is better:*
- Single hypothesis that can be verified in minutes
- Root cause becomes obvious upon first inspection
- Fix is small and localized (e.g., one function, one file)
- No architectural decision—just a bug fix
- The context is fully captured in a commit message or chunk goal

*Lighter-weight alternatives:*
- **Just fix it**: For obvious bugs, create a chunk directly via /chunk-create
- **Commit message**: For trivial fixes, the commit message captures the "why"
- **Inline in chunk GOAL.md**: Add a "Background" or "Investigation Notes" section
  to the chunk goal if context is needed but doesn't warrant a separate artifact
- **Decision record**: If the finding is a decision (not exploration), use /decision-create

The /investigation-create command should present these options when the user's
description suggests a small-scale issue, letting them consciously choose the
full investigation structure or opt for something lighter.

## Chunks

1. Create the investigation OVERVIEW.md template in src/templates/investigation/,
   following the patterns established by narrative and subsystem templates. Include
   sections for: trigger, success criteria, testable hypotheses, exploration log,
   findings, proposed chunks, and resolution rationale.

2. Add CLI commands for investigations: `ve investigation create <name>` to scaffold
   a new investigation directory, and `ve investigation list` to show investigations
   by status. Follow the patterns in src/narratives.py and src/subsystems.py.

3. Create the /investigation-create slash command to guide collaborative refinement
   of a new investigation, similar to /narrative-create and /subsystem-discover.

4. Update CLAUDE.md and docs/trunk/SPEC.md to document investigations as a workflow
   artifact, including when to use investigations vs narratives vs subsystems.

## Completion Criteria

When complete, an operator can create an investigation when facing uncertainty—
whether debugging an issue or exploring a new concept. The investigation template
guides them through structured exploration, encourages testable hypotheses, and
captures the learning regardless of outcome. Investigations that lead to action
produce chunk prompts; those that don't still document the decision rationale
for future reference.