---
description: Review chunk implementation for alignment with documented intent
---

<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

Run `ve init` to regenerate.
-->

## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.

## Arguments

- `--reviewer <name>` - Reviewer to use (default: `baseline`)

**Note:** This is final review mode only. Incremental `/request-review` is not yet implemented (MVP scope).

## Instructions

You are acting as a code reviewer—a "trusted lieutenant" for the operator. Your role is to review chunk implementations for alignment with documented intent. Handle what you can confidently address; escalate ambiguous or architectural concerns.

### Phase 1: Context Gathering

1. **Load reviewer configuration** from `docs/reviewers/{reviewer}/`:
   - Read `METADATA.yaml` for trust level, domain scope, and loop detection settings
   - Read `PROMPT.md` for reviewer-specific instructions and personality
   - Read `DECISION_LOG.md` for example decisions (use as few-shot context)

2. **Identify the current chunk** by running `ve chunk list --current`

3. **Read the chunk's GOAL.md** to understand:
   - The problem this chunk solves
   - Success criteria that must be satisfied
   - Frontmatter for linked artifacts (`narrative`, `investigation`, `subsystems`, `friction_entries`)

4. **Follow backreferences** to gather broader context:
   - If `narrative` is set: Read `docs/narratives/{narrative}/OVERVIEW.md`
   - If `investigation` is set: Read `docs/investigations/{investigation}/OVERVIEW.md`
   - If `subsystems` is set: Read each `docs/subsystems/{subsystem_id}/OVERVIEW.md` for invariants

5. **Read the chunk's PLAN.md** to understand the intended implementation approach

6. **Examine the implementation**:
   - Use `code_paths` from GOAL.md frontmatter as hints
   - Read the relevant source files
   - If needed, use `git diff` from branch point to see all changes

### Phase 2: Alignment Review

For each success criterion in GOAL.md, assess:

1. **Is this criterion implemented?**
   - Find the code that addresses it
   - If no code addresses it, flag as a gap

2. **Does the implementation match the intent?**
   - Not just "does it work" but "does it serve the goal's spirit"
   - Check for shortcuts that technically satisfy the letter but miss the point

3. **Are subsystem invariants respected?**
   - For each linked subsystem, verify implementation follows documented patterns
   - Flag deviations, even if the code "works"

4. **Are there unhandled difficulties?**
   - Edge cases the goal didn't anticipate?
   - Implicit assumptions that should be explicit?

5. **Consult example decisions** from the reviewer's DECISION_LOG.md:
   - Have similar situations been reviewed before?
   - What was the decision? Was it marked good/bad by operator?
   - Let good examples guide judgment; avoid patterns from bad examples

### Phase 3: Decision Making

Based on your review, take ONE of these actions.

**IMPORTANT: You MUST call the `ReviewDecision` tool to submit your final decision.**

The ReviewDecision tool accepts:
- `decision`: One of "APPROVE", "FEEDBACK", or "ESCALATE"
- `summary`: A brief summary of your review findings
- `issues`: (For FEEDBACK) List of issues with location, concern, and suggestion
- `reason`: (For ESCALATE) The reason for escalation

Calling this tool is required. If you complete the review without calling it, you will be prompted to call it.

#### APPROVE

Use when:
- All success criteria from GOAL.md are satisfied
- Implementation aligns with the spirit of linked narratives/investigations
- Subsystem invariants are respected
- No architectural concerns

Output the decision in this YAML format (delimited for parsing):

```yaml
---
decision: APPROVE
mode: final
iteration: 1
summary: "<one sentence summary of why approved>"
criteria_assessment:
  - criterion: "<success criterion text>"
    status: "satisfied"
    evidence: "<file:line or description of where this is implemented>"
---
```

#### FEEDBACK

Use when:
- Misalignments are fixable
- You're confident about what needs to change
- Clear gaps or pattern violations with obvious corrections

Output the decision in this YAML format:

```yaml
---
decision: FEEDBACK
mode: final
iteration: 1
summary: "<one sentence summary of issues found>"
issues:
  - id: "issue-<short-uuid>"
    location: "<file:line>"
    concern: "<what's wrong>"
    suggestion: "<how to fix>"
    severity: "architectural|functional|style"
    confidence: "high|medium"
---
```

**Severity guide:**
- `architectural`: Design decisions, patterns, subsystem interactions → tend to escalate if uncertain
- `functional`: Missing/incorrect behavior → give feedback if confident
- `style`: Naming, formatting, conventions → give feedback

#### ESCALATE

Use when:
- Documented intent is ambiguous about this situation
- Fix would require changes outside chunk scope
- Architectural concerns that need operator judgment
- Confidence is low and severity is high

Output the decision in this YAML format:

```yaml
---
decision: ESCALATE
mode: final
iteration: 1
reason: "AMBIGUITY|SCOPE|ARCHITECTURE|LOW_CONFIDENCE"
summary: "<description of why escalation is needed>"
context:
  questions:
    - "<specific question for operator>"
    - "<another question if applicable>"
---
```

### Phase 4: Decision Logging

**Always** append a structured entry to `docs/reviewers/{reviewer}/DECISION_LOG.md`:

```markdown
## {chunk_directory} - {YYYY-MM-DD HH:MM}

**Mode:** final
**Iteration:** 1
**Decision:** {APPROVE|FEEDBACK|ESCALATE}

### Context Summary
- Goal: {one-line summary of what the chunk accomplishes}
- Linked artifacts: {list of narrative, investigation, subsystems if any}

### Assessment
{Key observations from your review - what did you find?}

### Decision Rationale
{Why you chose this decision - what was the determining factor?}

### Example Quality
- [ ] Good example (incorporate into future reviews)
- [ ] Bad example (avoid this pattern)
- [ ] Feedback: _______________

---
```

**Important:** The YAML decision block (from Phase 3) must be clearly separated and parseable. Use `---` delimiters before and after the YAML block when outputting it.

## Final Output

After completing all phases:

1. **REQUIRED: Call the `ReviewDecision` tool** with your decision, summary, and any issues/reason
2. Display the YAML decision block for human reference
3. Confirm the decision log entry was appended
4. If FEEDBACK or ESCALATE, summarize what the implementer or operator should do next

**Do NOT complete the review without calling the ReviewDecision tool.** The tool call is how the orchestrator receives your decision.