<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk creates a single artifact: the `/subsystem-discover` agent command at `.claude/commands/subsystem-discover.md`. The command is a markdown file containing structured instructions that guide an agent through a collaborative subsystem discovery workflow.

**Pattern to follow**: The command follows the established pattern from `/chunk-create` and `/narrative-create`:
- Accept `$ARGUMENTS` from the operator
- Provide numbered steps for the agent to execute
- Mix CLI commands (`ve subsystem discover`) with conversational agent actions (asking questions, searching code, presenting findings)
- Reference template guidance comments to drive exploration

**Key design decisions**:
- The command is purely instructional markdown—no Python code changes required
- The agent does the work; the command provides the workflow structure
- Each phase has clear entry/exit criteria so the workflow is interruptible
- The command references the template's discovery prompts rather than duplicating them

**Testing approach**: This is a command file, not code. Validation will be manual:
- Test by running `/subsystem-discover` with one of the example descriptions
- Verify the workflow produces a populated subsystem OVERVIEW.md
- Confirm interruptibility by stopping mid-workflow and resuming

## Subsystem Considerations

No existing subsystems are directly relevant to this chunk. The command file is a standalone artifact.

However, this chunk is part of building the subsystem infrastructure itself—it's "chunk 6" in the subsystem documentation narrative.

## Sequence

### Step 1: Create the command file with header and argument handling

Create `.claude/commands/subsystem-discover.md` (via symlink from `src/templates/commands/subsystem-discover.md`).

Start with:
- Opening description of the command's purpose
- `$ARGUMENTS` placeholder for the operator's input
- Logic for detecting whether `$ARGUMENTS` is a new description or an existing subsystem ID

**Distinguishing new vs. existing subsystem**:
- If `$ARGUMENTS` matches pattern `docs/subsystems/NNNN-*` or `NNNN-*`, treat as existing subsystem
- Otherwise, treat as a high-level description for a new subsystem

Location: `src/templates/commands/subsystem-discover.md`

### Step 2: Add name derivation and verification phase

When `$ARGUMENTS` is a new description:
1. Instruct the agent to analyze the description and propose a short name
2. Present the proposed name to the operator with rationale
3. Accept confirmation or adjustment
4. Run `ve subsystem discover <confirmed_name>`
5. Note the created directory for subsequent steps

Include guidance on name derivation:
- Extract key nouns from the description
- Use underscore separation
- Keep under 32 characters
- Prefer concrete over abstract names

### Step 3: Add description decomposition guidance

Document the decomposition principles from the GOAL.md as actionable instructions:

**Decomposition principles** (for the agent to apply):
- Extract action verbs → function search patterns
- Extract domain nouns → class/module search patterns
- Identify enumerated concerns → scope anchors

**Signal detection principles**:
- "Should" and "consistently" → search for both canonical AND deviations
- "End state" descriptions → candidate invariants
- Grouping language → scope boundaries

Provide example decomposition for one of the sample descriptions so the agent has a concrete model.

### Step 4: Add Phase 1 - Pattern identification

Instructions for initial codebase exploration:
1. Generate 3-5 search patterns from the description decomposition
2. Execute searches (grep for functions, glob for files)
3. Categorize results: likely canonical, likely deviation, unclear
4. Present categorized findings to operator
5. Refine based on operator feedback

Include example search patterns for the frontmatter handling example:
- `parse.*frontmatter`, `frontmatter.*parse`
- `validate.*frontmatter`, `frontmatter.*valid`
- Files: `*frontmatter*.py`, `*yaml*.py`

Exit criteria: Operator confirms the identified implementations match their mental model.

### Step 5: Add Phase 2 - Boundary exploration

Instructions for scope definition:
1. Reference the template's Scope section discovery prompts
2. For each discovered implementation, ask: "Is X part of this subsystem?"
3. Search for related but potentially distinct patterns
4. Document: In Scope, Out of Scope, Ambiguous (needs discussion)

Include the template questions:
- "Is X part of this subsystem or separate?"
- "Can you give an example of something related but NOT part of this?"
- "What edge cases are you unsure about?"

Exit criteria: Operator confirms scope boundaries; In Scope and Out of Scope sections populated.

### Step 6: Add Phase 3 - Invariant discovery

Instructions for identifying invariants:
1. Analyze discovered implementations for common patterns
2. Reference the template's Invariants section discovery prompts
3. Ask operator about hard requirements vs. soft conventions
4. Document with rationale

Key questions from template:
- "What must ALWAYS be true?"
- "What would break if this invariant was violated?"
- "What rules should I never break when modifying this code?"

Exit criteria: At least one hard invariant or soft convention documented with rationale.

### Step 7: Add Phase 4 - Implementation mapping

Instructions for populating code_references:
1. For each discovered implementation from Phase 1, determine compliance level
2. Format as symbolic reference: `{file_path}#{symbol_path}`
3. Classify: COMPLIANT (canonical), PARTIAL (some deviation), NON_COMPLIANT (full deviation)
4. Add to frontmatter code_references array
5. Document NON_COMPLIANT and PARTIAL entries in Known Deviations section

Provide format example:
```yaml
code_references:
  - ref: src/frontmatter.py#parse_frontmatter
    implements: "Core parsing logic"
    compliance: COMPLIANT
```

Exit criteria: At least one code_reference in frontmatter; deviations documented.

### Step 8: Add Phase 5 - Chunk relationship mapping

Instructions for finding related chunks:
1. Search `docs/chunks/*/GOAL.md` for references to discovered implementations
2. Search chunk code_references for overlapping files
3. For each relevant chunk, classify relationship:
   - "implements": Chunk contributed code to the subsystem
   - "uses": Chunk depends on the subsystem's patterns
4. Update subsystem's chunks frontmatter array
5. Populate Chunk Relationships section

Exit criteria: chunks array populated; Chunk Relationships section has at least one entry (or explicitly notes "no related chunks found").

### Step 9: Add Phase 6 - Consolidation planning

Instructions for handling NON_COMPLIANT code:
1. If NON_COMPLIANT references exist, prompt agent to draft consolidation chunk prompts
2. For each deviation, create entry in Consolidation Chunks section:
   - Location
   - Issue description
   - Draft prompt for `/chunk-create`
   - Status (Not yet scheduled / Planned / Blocked)
3. Ask operator if any should be created immediately

Exit criteria: Consolidation Chunks section populated for any NON_COMPLIANT code.

### Step 10: Add status transition guidance

Instructions for completing discovery:
1. Review populated sections: Intent, Scope, Invariants, Implementation Locations
2. If all core sections are populated with content (not just template comments):
   - Suggest transitioning status from DISCOVERING to DOCUMENTED
   - Run `ve subsystem status <id> DOCUMENTED`
3. If sections remain incomplete, note what's missing and leave as DISCOVERING

Include the status transition rules from the template:
- DISCOVERING → DOCUMENTED: When Intent, Scope, and Invariants are populated and confirmed

### Step 11: Add interruptibility support

Add instructions at the start of the command for handling existing DISCOVERING subsystems:
1. If `$ARGUMENTS` is an existing subsystem ID:
   - Read the current OVERVIEW.md
   - Identify which sections have content vs. only template comments
   - Report progress to operator
   - Resume from the first incomplete phase
2. Present a progress summary before continuing

This makes the workflow resumable—operators can stop and restart without losing work.

### Step 12: Create symlink and test

1. Create symlink: `.claude/commands/subsystem-discover.md` → `src/templates/commands/subsystem-discover.md`
2. Manual test with one of the example descriptions:
   - "Front-matter handling - parsing from documents, asserting against Pydantic models, and mutating in place"
3. Verify:
   - Name derivation and confirmation works
   - Searches produce relevant results
   - Workflow progresses through phases
   - Result is a populated OVERVIEW.md

## Dependencies

- **Chunk 0016 (Directory & CLI)**: `ve subsystem discover <shortname>` must exist and work
- **Chunk 0017 (Template)**: The subsystem OVERVIEW.md template must have discovery prompts

Both are marked ACTIVE, so no blockers.

## Risks and Open Questions

- **Workflow length**: The full 6-phase workflow is comprehensive but may feel long. Mitigated by interruptibility—operators can stop and resume.

- **Search pattern quality**: The decomposition principles may not produce good search patterns for all descriptions. The operator feedback loop in Phase 1 should catch this, but some descriptions may need multiple iterations.

- **Compliance classification subjectivity**: COMPLIANT vs. PARTIAL vs. NON_COMPLIANT requires judgment. The command should encourage conservative classification (when in doubt, mark PARTIAL and ask the operator).

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
