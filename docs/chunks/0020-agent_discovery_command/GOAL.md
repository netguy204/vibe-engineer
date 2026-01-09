---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/commands/subsystem-discover.md
code_references:
  - ref: src/templates/commands/subsystem-discover.md
    implements: "Agent command template guiding collaborative subsystem discovery through 7 phases: name derivation, pattern identification, boundary exploration, invariant discovery, implementation mapping, chunk relationship mapping, and consolidation planning"
narrative: 0002-subsystem_documentation
subsystems: []
---

# Chunk Goal

## Minor Goal

Create the `/subsystem-discover` agent command that guides collaborative discovery of emergent subsystems. This command orchestrates the workflow where an agent and operator together explore the codebase to identify, document, and formalize cross-cutting patterns that have emerged organically.

**Why this matters**: The subsystem OVERVIEW.md template (chunk 0017) provides structure for capturing subsystem knowledge, but doesn't guide the discovery process. Operators know a pattern exists ("we have a validation system") but need help systematically exploring its boundaries, finding all implementations, and surfacing inconsistencies. The `/subsystem-discover` command makes this exploration collaborative and thorough.

**How this advances the trunk goal**: From docs/trunk/GOAL.md's Required Properties, "Following the workflow must maintain the health of documents over time and should not grow more difficult over time." By providing a structured discovery workflow, agents can help capture emergent patterns before knowledge is lost or inconsistencies multiply. The command ensures subsystem documentation starts comprehensive rather than requiring constant catch-up.

**Dependencies**: This chunk builds on:
- Chunk 0016 (Directory & CLI): The `ve subsystem discover <shortname>` command creates the subsystem directory
- Chunk 0017 (Template): The OVERVIEW.md template with discovery prompts in each section

## Success Criteria

### Command Structure

1. **Command file created**: `.claude/commands/subsystem-discover.md` exists and follows the established command pattern (e.g., similar structure to `/chunk-create`)

2. **Accepts high-level description**: The command accepts `$ARGUMENTS` as either:
   - A high-level description of the subsystem pattern
   - An existing subsystem path/ID (continues discovery on an existing DISCOVERING subsystem)

   **Example descriptions**:
   - "Front-matter handling - parsing from documents, asserting against Pydantic models, and mutating in place"
   - "Test scaffolding and mocks - complex mocks like multi-project worktrees and simulated VE setups that should be used consistently across tests"
   - "Error handling - accumulating errors and presenting them together so users don't hunt and peck through failures"
   - "Template management - consistent parameters across templates, template includes, shared assumptions about available tools"

3. **Derives and verifies name**: When given a description, the agent:
   - Proposes a short name derived from the description (e.g., `frontmatter_handling`, `test_scaffolding`, `error_accumulation`)
   - Presents the proposed name to the operator for confirmation or adjustment
   - Uses the confirmed name with `ve subsystem discover <shortname>` to create the directory

### Discovery Workflow Phases

4. **Description-guided exploration**: The high-level description bootstraps the entire discovery process. The agent should apply these principles to extract actionable investigation paths:

   **Decomposition principles**:
   - **Extract action verbs as function patterns**: Verbs like "parsing", "asserting", "mutating", "accumulating" suggest function names and behaviors to grep for (e.g., `parse_frontmatter`, `validate_`, `mutate_`)
   - **Extract domain nouns as type/module patterns**: Nouns like "frontmatter", "Pydantic model", "worktree", "template" suggest class names, module names, or file patterns to search
   - **Identify enumerated concerns as scope anchors**: Phrases like "including X, Y, and Z" or "X, Y, and Z constitute" explicitly list what's in scope—search for each

   **Signal detection principles**:
   - **"Should" and "consistently" signal inconsistencies**: Language like "should be used consistently" or "should consistently use" implies known inconsistency—the agent should search for both the canonical pattern AND deviations
   - **"End state" descriptions reveal invariants**: Phrases describing desired outcomes ("templates can make consistent assumptions", "users don't hunt and peck") are candidate invariants to validate against implementations
   - **Grouping language defines boundaries**: When the operator groups concepts together ("parsing, validating, and mutating all constitute"), they're defining subsystem scope—related but ungrouped concepts are candidates for "out of scope"

   **Initial investigation strategy**:
   - Generate 3-5 search patterns from extracted verbs and nouns
   - Run searches and categorize results as: likely canonical, likely deviation, unclear
   - Present categorized findings to operator before proceeding
   - Use operator feedback to refine understanding before populating template sections

5. **Phase 1 - Pattern identification**: Using the principles above, the agent:
   - Derives search patterns from the description (verbs → function patterns, nouns → type/file patterns)
   - Executes searches and categorizes findings
   - Presents findings to the operator: "Based on your description, I found these implementations. I've categorized them as canonical vs. potential deviations—does this match your understanding?"
   - Refines search based on operator feedback

6. **Phase 2 - Boundary exploration**: The command guides exploration of scope:
   - Prompt the agent to ask clarifying questions from the template's Scope section
   - Search for related but potentially distinct patterns ("Is X part of this or separate?")
   - Document both in-scope and out-of-scope determinations

7. **Phase 3 - Invariant discovery**: The command guides invariant identification:
   - Prompt the agent to analyze discovered implementations for common patterns
   - Ask the operator about hard requirements vs soft conventions
   - Document invariants with rationale

8. **Phase 4 - Implementation mapping**: The command guides code reference collection:
   - For each discovered implementation, prompt the agent to classify compliance level (COMPLIANT, PARTIAL, NON_COMPLIANT)
   - Populate the code_references frontmatter with symbolic references
   - Document deviations in the Known Deviations section with context

9. **Phase 5 - Chunk relationship mapping**: The command guides chunk discovery:
   - Search existing chunks for references to the pattern's implementations
   - Prompt the agent to classify each as "implements" or "uses"
   - Update the chunks frontmatter and Chunk Relationships section

10. **Phase 6 - Consolidation planning**: If NON_COMPLIANT references were found:
    - Prompt the agent to draft consolidation chunk prompts
    - Add drafts to the Consolidation Chunks section
    - Ask the operator if any should be created immediately

### Workflow Properties

11. **Interruptible**: The command can be run multiple times on the same subsystem. Each run should detect which sections are already populated and focus on incomplete areas.

12. **Conversational**: Each phase involves back-and-forth with the operator. The command should not attempt to auto-populate everything—operator judgment is essential for scope decisions and invariant priorities.

13. **Progressive**: The command progresses through phases in order but can skip phases if the operator indicates they're already handled.

### Output Quality

14. **Populated template**: After running the command through all phases, the subsystem's OVERVIEW.md should have:
    - Intent section populated (not just template comments)
    - Scope section with In Scope and Out of Scope subsections
    - Invariants section with at least one hard or soft invariant
    - At least one code_reference in frontmatter
    - Template guidance comments removed from populated sections

15. **Status guidance**: The command should guide the operator on when to transition from DISCOVERING to DOCUMENTED (typically when Intent, Scope, and Invariants are sufficiently captured)

