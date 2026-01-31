# Implementation Plan

## Approach

Create the `/chunk-review` skill as a Jinja2 command template following the established pattern in `src/templates/commands/`. The skill will be a comprehensive prompt that guides an agent through the four-phase review process defined in the prototype at `docs/investigations/orchestrator_quality_assurance/prototypes/chunk-review.md`.

The skill template will:
1. Accept `--reviewer` flag (default: `baseline`) to select which reviewer configuration to use
2. Guide the agent through context gathering, alignment review, decision making, and decision logging
3. Produce structured YAML output suitable for orchestrator consumption in the downstream `orch_review_phase` chunk
4. Append structured entries to the reviewer's `DECISION_LOG.md`

This chunk focuses on MVP scope: only final review mode (not incremental `/request-review`). The skill is a pure prompt template—no Python code changes are needed beyond ensuring `ve init` renders the new template.

Following the template_system subsystem (STABLE), the template will use `.jinja2` suffix and include partials via `{% include %}` for the auto-generated header and common tips.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system to create a new command template. The template will follow the established pattern:
  - File at `src/templates/commands/chunk-review.md.jinja2`
  - Frontmatter with `description` field
  - `{% set source_template = "..." %}` for self-identification
  - `{% include "partials/..." %}` for header and tips
  - Rendered by `ve init` to `.claude/commands/chunk-review.md`

## Sequence

### Step 1: Create the skill template file

Create `src/templates/commands/chunk-review.md.jinja2` with:

1. **Frontmatter** with description: "Review chunk implementation for alignment with documented intent"

2. **Standard includes**:
   - `{% set source_template = "chunk-review.md.jinja2" %}`
   - `{% include "partials/auto-generated-header.md.jinja2" %}`
   - `{% include "partials/common-tips.md.jinja2" %}`

3. **Arguments section** documenting:
   - `--reviewer <name>` flag (default: `baseline`)
   - Note that this is final review mode only (MVP scope)

4. **Instructions section** with four phases adapted from prototype

Location: `src/templates/commands/chunk-review.md.jinja2`

### Step 2: Implement Phase 1 - Context Gathering

Write the instructions for Phase 1 that guide the agent to:

1. Load reviewer configuration:
   - Read `docs/reviewers/{reviewer}/METADATA.yaml` for trust level, domain scope, loop detection config
   - Read `docs/reviewers/{reviewer}/PROMPT.md` for reviewer-specific instructions
   - Read `docs/reviewers/{reviewer}/DECISION_LOG.md` for example decisions (few-shot context)

2. Identify the current chunk via `ve chunk list --current`

3. Read chunk's GOAL.md to understand:
   - Success criteria (what needs to be satisfied)
   - Frontmatter for linked artifacts

4. Follow backreferences to gather broader context:
   - If `narrative` set: Read `docs/narratives/{narrative}/OVERVIEW.md`
   - If `investigation` set: Read `docs/investigations/{investigation}/OVERVIEW.md`
   - If `subsystems` set: Read each `docs/subsystems/{id}/OVERVIEW.md` for invariants

5. Read chunk's PLAN.md to understand intended approach

Location: Phase 1 section of the template

### Step 3: Implement Phase 2 - Alignment Review

Write the instructions for Phase 2 that guide the agent to:

1. For each success criterion in GOAL.md:
   - Find the code that addresses it (using code_paths and code_references as hints)
   - Assess whether it's implemented
   - Check if implementation matches the spirit of the intent (not just the letter)

2. For linked subsystems:
   - Verify implementation follows documented patterns and invariants
   - Flag deviations even if the code "works"

3. Check for unhandled difficulties:
   - Edge cases the goal didn't anticipate
   - Implicit assumptions that should be explicit

4. Consult example decisions from the reviewer's DECISION_LOG.md:
   - Look for similar situations
   - Use good examples to guide judgment
   - Avoid patterns from bad examples

Location: Phase 2 section of the template

### Step 4: Implement Phase 3 - Decision Making

Write the instructions for Phase 3 that guide the agent to choose ONE decision:

**APPROVE** - Use when:
- All success criteria satisfied
- Implementation aligns with intent
- Subsystem invariants respected
- No architectural concerns

Output format:
```yaml
decision: APPROVE
mode: final
iteration: {n}
summary: "..."
criteria_assessment:
  - criterion: "..."
    status: "satisfied"
    evidence: "..."
```

**FEEDBACK** - Use when:
- Misalignments are fixable
- Agent is confident about what needs to change

Output format:
```yaml
decision: FEEDBACK
mode: final
iteration: {n}
summary: "..."
issues:
  - id: "issue-{uuid}"
    location: "<file:line>"
    concern: "..."
    suggestion: "..."
    severity: "architectural|functional|style"
    confidence: "high|medium"
```

**ESCALATE** - Use when:
- Documented intent is ambiguous
- Fix requires changes outside chunk scope
- Architectural concerns needing operator judgment
- Confidence is low and severity is high

Output format:
```yaml
decision: ESCALATE
mode: final
iteration: {n}
reason: "AMBIGUITY|SCOPE|ARCHITECTURE|LOW_CONFIDENCE"
summary: "..."
context:
  questions: [...]
```

Location: Phase 3 section of the template

### Step 5: Implement Phase 4 - Decision Logging

Write the instructions for Phase 4 that guide the agent to:

1. Append a structured entry to `docs/reviewers/{reviewer}/DECISION_LOG.md`

2. Entry format:
   ```markdown
   ## {chunk_directory} - {timestamp}

   **Mode:** final
   **Iteration:** {n}
   **Decision:** {APPROVE|FEEDBACK|ESCALATE}

   ### Context Summary
   - Goal: {one-line summary}
   - Linked artifacts: {list}

   ### Assessment
   {key observations}

   ### Decision Rationale
   {why this decision}

   ### Example Quality
   - [ ] Good example (incorporate into future reviews)
   - [ ] Bad example (avoid this pattern)
   - [ ] Feedback: _______________
   ```

3. Ensure the YAML decision block is clearly separated (for orchestrator parsing)

Location: Phase 4 section of the template

### Step 6: Add skill to CLAUDE.md template

Update `src/templates/claude/CLAUDE.md.jinja2` to include `/chunk-review` in the Available Commands section, so operators can discover it.

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 7: Render and verify

1. Run `uv run ve init` to render the new template
2. Verify `.claude/commands/chunk-review.md` exists with expected content
3. Check that the skill appears in CLAUDE.md Available Commands

### Step 8: Test the skill manually

Perform a manual test by:
1. Invoking `/chunk-review --reviewer baseline` on a completed chunk (e.g., `reviewer_infrastructure`)
2. Verify that:
   - Context gathering reads the expected files
   - The decision is one of APPROVE/FEEDBACK/ESCALATE
   - A properly formatted entry is appended to DECISION_LOG.md
   - The YAML output block is parseable

This is a manual integration test since the skill is a prompt template, not Python code.

## Dependencies

- **reviewer_infrastructure chunk**: Must be ACTIVE. Provides:
  - `docs/reviewers/baseline/` directory structure
  - `src/models.py#ReviewerMetadata` pydantic model for validating METADATA.yaml
  - Baseline reviewer configuration (trust_level: observation, loop_detection defaults)

## Risks and Open Questions

1. **Decision log append atomicity**: Multiple concurrent reviews could race when appending to DECISION_LOG.md. For MVP this is acceptable since:
   - The orchestrator will invoke reviews sequentially per reviewer
   - Operators running manual reviews will see conflicts at commit time
   - If this becomes a problem, a future chunk can add locking

2. **YAML output parsing reliability**: The downstream `orch_review_phase` chunk will need to parse the YAML decision block. The template should make the output format unambiguous with clear delimiters (e.g., `---` before and after).

3. **Iteration tracking without state**: The skill doesn't have access to iteration count (that's orchestrator state). For MVP, the skill outputs `iteration: 1` and the orchestrator will inject the correct count when invoking.

4. **Loop detection without history**: Same-issue detection requires knowing what was flagged before. For MVP, this is deferred to the `orch_review_phase` chunk which will track iteration history and invoke loop detection.

5. **Reviewer PROMPT.md interpretation**: The baseline PROMPT.md provides general guidance. The skill should instruct agents to read and follow it, but interpretation quality depends on the agent.

## Deviations

<!-- Populate during implementation -->