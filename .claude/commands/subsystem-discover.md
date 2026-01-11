---
description: Guide collaborative discovery of an emergent subsystem.
---

## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.


## Instructions

The operator has provided the following input:

$ARGUMENTS

---

## Determining Input Type

Examine `$ARGUMENTS` to determine whether this is:

1. **Existing subsystem** (continuing discovery): If `$ARGUMENTS` matches pattern
   `docs/subsystems/<short_name>` or just `<short_name>` (e.g., `validation`,
   `docs/subsystems/frontmatter`), this is a request to continue discovery
   on an existing subsystem. Skip to the **Resuming Discovery** section below.

2. **New subsystem** (starting discovery): Otherwise, treat `$ARGUMENTS` as a
   high-level description of a subsystem pattern to discover. Continue with
   **Phase 0: Name Derivation** below.

---

## Resuming Discovery

If continuing an existing subsystem:

1. Read the subsystem's OVERVIEW.md file
2. Analyze which sections have actual content vs only template comments:
   - Intent section populated?
   - Scope section with In Scope/Out of Scope?
   - Invariants section with hard/soft invariants?
   - code_references in frontmatter?
   - chunks array populated?
3. Report progress to the operator:
   > "This subsystem is in DISCOVERING status. Here's what's been captured so far:
   > - Intent: [populated/empty]
   > - Scope: [populated/empty]
   > - Invariants: [populated/empty]
   > - Code references: [count]
   > - Chunk relationships: [count]"
4. Resume from the first incomplete phase below

---

## Phase 0: Name Derivation

When `$ARGUMENTS` is a new description, derive and confirm a short name:

1. **Analyze the description** and propose a short name:
   - Extract key nouns from the description
   - Use underscore separation (e.g., `frontmatter_handling`, `test_scaffolding`)
   - Keep under 32 characters
   - Prefer concrete over abstract names (e.g., `error_accumulation` over `error_handling`)

2. **Present the proposed name** to the operator:
   > "Based on your description, I propose the name `<proposed_name>`.
   > This captures [rationale for the name choice].
   > Does this name work, or would you prefer something different?"

3. **Accept confirmation or adjustment** from the operator

4. **Register the subsystem**:
   ```
   ve subsystem discover <confirmed_name>
   ```

5. Note the created directory path (e.g., `docs/subsystems/frontmatter_handling`).
   We'll refer to this as `<subsystem_directory>` below.

---

## Phase 1: Pattern Identification

Use the operator's description to bootstrap codebase exploration.

### Decomposition Principles

Apply these principles to extract actionable investigation paths:

**Extract action verbs as function patterns**:
- Verbs like "parsing", "asserting", "mutating", "accumulating" suggest function
  names and behaviors to search for
- Example: "parsing from documents" → search for `parse_`, `read_`, `load_`

**Extract domain nouns as type/module patterns**:
- Nouns like "frontmatter", "Pydantic model", "worktree", "template" suggest
  class names, module names, or file patterns to search
- Example: "Pydantic models" → search for `BaseModel`, `*Model`, `validate`

**Identify enumerated concerns as scope anchors**:
- Phrases like "X, Y, and Z constitute" explicitly list what's in scope
- Search for each enumerated concept specifically

### Signal Detection

**"Should" and "consistently" signal inconsistencies**:
- Language like "should be used consistently" implies known inconsistency
- Search for both the canonical pattern AND likely deviations

**"End state" descriptions reveal invariants**:
- Phrases describing desired outcomes are candidate invariants
- Example: "so users don't hunt and peck through failures" → invariant about
  error presentation

**Grouping language defines boundaries**:
- When concepts are grouped together, they're defining subsystem scope
- Related but ungrouped concepts are candidates for "out of scope"

### Investigation Steps

1. **Generate 3-5 search patterns** from the description decomposition:
   - Function patterns from verbs (grep)
   - File/module patterns from nouns (glob)
   - Example searches for "front-matter handling":
     - `parse.*frontmatter`, `frontmatter.*parse`
     - `validate.*frontmatter`, `frontmatter.*valid`
     - Files: `*frontmatter*.py`, `*yaml*.py`

2. **Execute searches** and review results

3. **Categorize findings**:
   - **Likely canonical**: Appears to be the "right way" based on patterns
   - **Likely deviation**: Works differently, may need consolidation
   - **Unclear**: Need operator input to classify

4. **Present findings to operator**:
   > "Based on your description, I found these implementations:
   >
   > **Likely Canonical:**
   > - `src/frontmatter.py#parse_frontmatter` - Uses consistent pattern X
   >
   > **Potential Deviations:**
   > - `src/legacy/parser.py#read_header` - Uses different approach
   >
   > **Unclear:**
   > - `src/utils.py#extract_metadata` - Related but uncertain if in scope
   >
   > Does this match your understanding?"

5. **Refine based on feedback** - adjust searches or recategorize as needed

**Exit Criteria**: Operator confirms the identified implementations match their
mental model of the subsystem.

---

## Phase 2: Boundary Exploration

Clarify what's in scope and what's explicitly out.

### Discovery Questions

Ask the operator these questions (from the template's Scope section):

1. "Is X part of this subsystem or separate?" (for each related concept discovered)
2. "Can you give me an example of something that seems related but is NOT part
   of this subsystem?"
3. "What edge cases are you unsure about?"

### Exploration Steps

1. **For each discovered implementation**, ask: "Is this part of the subsystem?"

2. **Search for related patterns** that might be distinct:
   - If the subsystem is "frontmatter handling", what about YAML parsing in general?
   - If it's "error accumulation", what about logging?

3. **Document scope determinations** in three categories:
   - **In Scope**: Core to the subsystem
   - **Out of Scope**: Related but explicitly separate
   - **Ambiguous**: Needs further discussion

4. **Update the OVERVIEW.md** with the Scope section content:
   - Remove the template comment block
   - Add In Scope, Out of Scope, and optionally Ambiguous subsections

**Exit Criteria**: Operator confirms scope boundaries; In Scope and Out of Scope
sections are populated in `<subsystem_directory>/OVERVIEW.md`.

---

## Phase 3: Invariant Discovery

Identify what must always be true about this subsystem.

### Discovery Questions

Ask the operator (from the template's Invariants section):

1. "What must ALWAYS be true about this subsystem?"
2. "What would break if this invariant was violated?"
3. "If I were to modify code in this subsystem, what rules should I never break?"
4. "Are there any conventions that are strongly preferred but not strictly required?"

### Classification

**Hard Invariants**: Must never be violated
- Should be specific and testable
- Violation would cause bugs, security issues, or data corruption
- Example: "All external input must be validated before use"

**Soft Conventions**: Strongly preferred but flexible in edge cases
- Explain the reasoning so agents can make informed tradeoffs
- Example: "Prefer early returns over nested conditionals (readability)"

### Documentation Steps

1. **Analyze discovered implementations** for common patterns that suggest invariants

2. **Ask the operator** about requirements vs conventions

3. **Document in OVERVIEW.md**:
   - Remove the template comment block from Invariants section
   - Add Hard Invariants and/or Soft Conventions subsections
   - Include rationale for each invariant

**Exit Criteria**: At least one hard invariant or soft convention documented with
rationale in `<subsystem_directory>/OVERVIEW.md`.

---

## Phase 4: Implementation Mapping

Populate the code_references frontmatter with discovered implementations.

### Compliance Levels

For each discovered implementation, classify its compliance:

- **COMPLIANT**: Fully follows the subsystem's patterns (canonical implementation)
- **PARTIAL**: Partially follows but has some deviations
- **NON_COMPLIANT**: Does not follow the patterns (deviation to be addressed)

When in doubt, mark as PARTIAL and ask the operator.

### Documentation Steps

1. **For each implementation from Phase 1**, determine compliance level

2. **Format as symbolic reference**: `{file_path}#{symbol_path}`
   - Symbol path uses `::` as nesting separator for nested symbols
   - Example: `src/validation.py#Validator::validate`

3. **Add to frontmatter** code_references array:
   ```yaml
   code_references:
     - ref: src/frontmatter.py#parse_frontmatter
       implements: "Core parsing logic"
       compliance: COMPLIANT
     - ref: src/legacy/parser.py#read_header
       implements: "Legacy header parsing"
       compliance: NON_COMPLIANT
   ```

4. **Document NON_COMPLIANT and PARTIAL entries** in the Known Deviations section:
   - Why the deviation exists (if known)
   - Impact of the deviation
   - Any blockers to fixing it

5. **Update Implementation Locations section** with prose context for COMPLIANT
   references - explain why they're canonical

**Exit Criteria**: At least one code_reference in frontmatter; any deviations
documented in Known Deviations section.

---

## Phase 5: Chunk Relationship Mapping

Find chunks that relate to this subsystem.

### Discovery Steps

1. **Search chunks for references to discovered implementations**:
   ```
   # Search chunk GOAL.md files for file paths
   grep -r "src/frontmatter.py" docs/chunks/*/GOAL.md

   # Search chunk code_references for overlapping files
   grep -r "frontmatter" docs/chunks/*/GOAL.md
   ```

2. **Search chunk code_references** for overlapping files/symbols

3. **For each relevant chunk, classify relationship**:
   - **implements**: Chunk contributed code to the subsystem
   - **uses**: Chunk depends on the subsystem's patterns

### Documentation Steps

1. **Update subsystem's chunks frontmatter array**:
   ```yaml
   chunks:
     - chunk_id: "validation_enhancements"
       relationship: implements
     - chunk_id: "chunk_completion"
       relationship: uses
   ```

2. **Populate Chunk Relationships section** with prose:
   - Remove template comment block
   - Add Implements and Uses subsections
   - Brief description of each chunk's relationship

**Exit Criteria**: chunks array populated; Chunk Relationships section has at
least one entry (or explicitly notes "no related chunks found").

---

## Phase 6: Consolidation Planning

If NON_COMPLIANT references were found, plan for migration.

### When to Skip

If no NON_COMPLIANT code_references exist, note this and skip to Phase 7.

### Planning Steps

1. **For each NON_COMPLIANT reference**, draft a consolidation chunk prompt:
   - Location: Where the non-compliant code lives
   - Issue: What's wrong or different from canonical approach
   - Draft prompt: A seed for `/chunk-create`
   - Status: Not yet scheduled / Planned / Blocked on X

2. **Update Consolidation Chunks section** in OVERVIEW.md:
   - Remove template comment block
   - Add Pending Consolidation subsection with entries

3. **Ask the operator** if any consolidation chunks should be created immediately:
   > "I've identified [N] non-compliant implementations that could be consolidated.
   > Would you like to create any of these as chunks now, or leave them documented
   > for future work?"

**Exit Criteria**: Consolidation Chunks section populated for any NON_COMPLIANT
code (or section notes "no consolidation needed").

---

## Phase 7: Status Transition

Review completeness and consider transitioning from DISCOVERING to DOCUMENTED.

### Completeness Check

Review the populated sections:
- [ ] Intent section has content (not just template comments)
- [ ] Scope section has In Scope and Out of Scope content
- [ ] Invariants section has at least one invariant
- [ ] At least one code_reference in frontmatter
- [ ] Template guidance comments removed from populated sections

### Status Transition Rules

**DISCOVERING → DOCUMENTED**: When Intent, Scope, and Invariants are populated
and confirmed by the operator.

### Transition Steps

1. **If all core sections are populated**:
   > "The subsystem documentation is now comprehensive:
   > - Intent: [summary]
   > - Scope: [in/out items]
   > - Invariants: [count] documented
   > - Code references: [count]
   >
   > I recommend transitioning status from DISCOVERING to DOCUMENTED.
   > This signals that the core patterns are captured and agents should
   > track any new deviations they discover."

   If the operator agrees:
   ```
   ve subsystem status <subsystem_id> DOCUMENTED
   ```

2. **If sections remain incomplete**:
   > "Some sections still need content:
   > - [list incomplete sections]
   >
   > The subsystem remains in DISCOVERING status. You can continue discovery
   > later by running `/subsystem-discover <subsystem_id>`."

---

## Summary

After completing all phases, provide a summary:

> "Subsystem discovery complete for `<subsystem_name>`:
>
> **Status**: [DISCOVERING/DOCUMENTED]
> **Location**: `<subsystem_directory>/OVERVIEW.md`
>
> **What was captured**:
> - Intent: [brief summary]
> - Scope: [N] in-scope, [M] out-of-scope items
> - Invariants: [N] hard, [M] soft
> - Code references: [N] total ([X] compliant, [Y] partial, [Z] non-compliant)
> - Chunk relationships: [N] chunks
> - Consolidation items: [N] pending
>
> **Next steps**:
> - [If DISCOVERING] Continue discovery with `/subsystem-discover <id>`
> - [If DOCUMENTED] Subsystem will be referenced as agents work on related code
> - [If consolidation items] Create consolidation chunks with `/chunk-create`"