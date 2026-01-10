<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk creates a single new template file following the established patterns
in `src/templates/`. The approach is straightforward:

1. Study the existing `narrative/OVERVIEW.md.jinja2` and `subsystem/OVERVIEW.md.jinja2`
   templates to understand the structural conventions
2. Design the investigation template with its unique sections per the GOAL.md
3. Write tests that verify the template renders correctly
4. Create the template file

Per DEC-004, all file references in the template will be relative to the project root.

The template will use the same Jinja2 patterns as existing templates:
- YAML frontmatter with schema documentation in HTML comments
- Section headers with discovery/guidance prompts in HTML comments
- Guidance that helps agents understand when sections are complete

## Sequence

### Step 1: Write failing tests for investigation template rendering

Following docs/trunk/TESTING_PHILOSOPHY.md's TDD requirements, first write tests
that verify:
- The template file exists at `src/templates/investigation/OVERVIEW.md.jinja2`
- The template renders without error
- The rendered output contains required frontmatter fields (status, trigger, proposed_chunks)
- The rendered output contains required sections (Trigger, Success Criteria,
  Testable Hypotheses, Exploration Log, Findings, Proposed Chunks, Resolution Rationale)

Location: `tests/test_investigation_template.py`

These tests should fail initially because the template doesn't exist yet.

### Step 2: Create the investigation template directory

Create the directory structure:
```
src/templates/investigation/
```

Location: `src/templates/investigation/`

### Step 3: Create the investigation OVERVIEW.md.jinja2 template

Create the template with:

**Frontmatter schema:**
- `status`: ONGOING | SOLVED | NOTED | DEFERRED (with schema documentation)
- `trigger`: Brief description of what prompted the investigation
- `proposed_chunks`: Array for chunk prompts (mirrors narrative pattern)

**Sections with guidance comments:**

1. **Trigger** - What prompted this investigation
   - Guidance: Describe the problem or opportunity clearly
   - Note: Natural language captures issue vs concept distinction

2. **Success Criteria** - How we'll know the investigation is complete
   - Guidance: What questions must be answered? What evidence is needed?

3. **Testable Hypotheses** - Encourages objective verification
   - Guidance: Frame beliefs as hypotheses that can be verified
   - Prompt agents to identify how each hypothesis could be tested

4. **Exploration Log** - Timestamped record
   - Guidance: Document exploration steps and findings chronologically
   - Format suggestion for entries: `### YYYY-MM-DD: [Summary]`

5. **Findings** - Distinction between verified and unverified
   - Guidance: Separate "Verified Findings" from "Hypotheses/Opinions"
   - Emphasize: What do we now KNOW vs what do we BELIEVE?

6. **Proposed Chunks** - Like narrative chunks array
   - Guidance: If action is warranted, list chunk prompts here
   - Mirror the frontmatter `proposed_chunks` array structure

7. **Resolution Rationale** - Why the chosen outcome
   - Guidance: Explain the decision to mark SOLVED/NOTED/DEFERRED
   - What evidence supports this resolution?

Location: `src/templates/investigation/OVERVIEW.md.jinja2`

### Step 4: Verify tests pass

Run the test suite to confirm the template renders correctly and contains
all required elements.

```bash
pytest tests/test_investigation_template.py -v
```

## Risks and Open Questions

- **Template variable requirements**: Need to verify what variables (if any) the
  template expects from the template rendering system. The narrative template uses
  no variables, but subsystem uses `{{ short_name }}`. The investigation template
  likely needs no variables since investigations don't have a computed name in
  the same way.

- **Proposed chunks vs chunks naming**: The narrative uses `chunks` in frontmatter;
  investigations use `proposed_chunks` to emphasize the speculative nature. Need
  to ensure the naming is consistent with the GOAL.md specification.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->