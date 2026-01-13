# Chunk Review Skill (Prototype v2)

## Overview

This skill reviews chunk implementations for alignment with documented intent.
It operates as a "trusted lieutenant"—handling what it can confidently address
and escalating ambiguous or architectural concerns to the operator.

Reviewers are **persistent entities with emergent personality**. Each reviewer
has its own decision log, trust level, and domain scope. Personality emerges
from accumulated examples of good/bad decisions.

## Review Modes

### Incremental Review (On-Demand)

The implementer can request a review at any point during implementation using
the `request-review` tool. This enables:

- Early feedback before going too far down a wrong path
- Validation of approach before investing in details
- Clarification of ambiguous requirements mid-implementation

Incremental reviews are **advisory**—they provide feedback but don't block.

### Final Review (Mandatory)

Every chunk receives a final review after `chunk-implement` completes and before
`chunk-complete` can proceed. This is the **gate**—the chunk cannot complete
without reviewer approval.

## Inputs

- `chunk_directory`: Path to the chunk being reviewed
- `reviewer`: Name of the reviewer to use (e.g., `baseline`, `api_v1`)
- `mode`: `incremental` or `final` (default: `final`)
- `iteration`: Current iteration count (tracked automatically)

## Loop Detection and Escape Hatch

**Problem**: Review-implementation cycles can loop indefinitely if:
- Reviewer keeps finding new issues
- Implementer's fixes introduce new problems
- Requirements are fundamentally ambiguous

**Safety mechanism**:

```yaml
loop_detection:
  max_iterations: 3           # Hard limit on review cycles
  escalation_threshold: 2     # When to start warning
  same_issue_threshold: 2     # Recurrence limit for same issue
```

### Configuration Intent

| Setting | Intent | Behavior |
|---------|--------|----------|
| `max_iterations` | Prevent infinite loops | After this many review→feedback→fix cycles without approval, **automatically escalate** to operator. The loop isn't converging and needs human intervention. |
| `escalation_threshold` | Early warning system | After this many iterations, **log a warning** to the decision log (but don't escalate yet). Signals that convergence may be at risk. Operator can proactively intervene if monitoring. |
| `same_issue_threshold` | Detect misunderstandings | If the **same issue** (matched by issue ID) is flagged this many times, **escalate immediately** regardless of iteration count. Indicates either: (1) implementer misunderstands the feedback, (2) the issue is structurally unfixable, or (3) reviewer and implementer have incompatible interpretations. |

### Why Per-Reviewer Configuration?

These thresholds are part of reviewer personality:
- **Strict reviewers** (e.g., security-focused): Lower thresholds, escalate sooner
- **Trusted reviewers** on routine work: Higher thresholds, more patience
- **New reviewers** in observation mode: Lower thresholds until trust develops

Operators can tune these as they calibrate each reviewer's behavior.

### Behavior by Iteration Count

| Iteration | Behavior |
|-----------|----------|
| 1 | Normal review |
| 2 | Normal review + warning logged (if `escalation_threshold: 2`) |
| 3 | Final attempt—escalate if not resolved (if `max_iterations: 3`) |
| 4+ | **Automatic escalation** to operator |

**Escalation message:**

```yaml
decision: ESCALATE
reason: LOOP_DETECTED
summary: "Review-implementation cycle has not converged after {n} iterations."
history:
  - iteration: 1
    decision: FEEDBACK
    issues: ["..."]
  - iteration: 2
    decision: FEEDBACK
    issues: ["..."]
  - iteration: 3
    decision: FEEDBACK
    issues: ["..."]
recommendation: |
  This suggests either:
  1. Requirements ambiguity that needs operator clarification
  2. Implementation approach that can't satisfy all constraints
  3. Reviewer/implementer misalignment on interpretation

  Operator intervention needed to break the loop.
```

**Same-issue detection**: If the reviewer flags the same issue twice (after
implementer claimed to fix it), escalate immediately—this indicates either a
misunderstanding or an unfixable constraint.

---

## Instructions

### Phase 1: Context Gathering

1. **Load reviewer configuration** from `docs/reviewers/{reviewer}/`:
   - Read `PROMPT.md` for any domain-specific instructions
   - Read `DECISION_LOG.md` for example decisions to inform judgment
   - Read `METADATA.yaml` for trust level and domain scope

2. **Read the chunk's GOAL.md** to understand the focused intent:
   - What problem does this chunk solve?
   - What are the success criteria?
   - What constraints apply?

3. **Follow backreferences** to gather broader context:
   - If `narrative` is set: Read the narrative's OVERVIEW.md
   - If `investigation` is set: Read the investigation's OVERVIEW.md
   - If `subsystems` is set: Read each subsystem's OVERVIEW.md for invariants
   - If `friction_entries` is set: Understand what pain points motivated this

4. **Read the chunk's PLAN.md** to understand the intended approach

5. **Identify the implementation**:
   - For incremental review: Current working state
   - For final review: Complete implementation (git diff from branch point)

6. **Check iteration history** (for final reviews):
   - How many review cycles have occurred?
   - What issues were flagged in previous iterations?
   - Were any issues flagged multiple times?

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
   - Does the implementation encounter edge cases the goal didn't anticipate?
   - Are there implicit assumptions that should be made explicit?

5. **Consult example decisions** from the reviewer's decision log:
   - Have similar situations been reviewed before?
   - What was the decision? Was it marked good/bad by operator?
   - Let good examples guide judgment; avoid patterns from bad examples

### Phase 3: Decision Making

**Check loop detection first** (final review mode only):

```
if iteration >= max_iterations:
    return ESCALATE with reason=LOOP_DETECTED

if any issue was flagged in previous iteration and still present:
    return ESCALATE with reason=RECURRING_ISSUE
```

Then, based on your review, take ONE of these actions:

#### APPROVE
Use when: Implementation fully aligns with intent, all criteria met, no concerns.

```yaml
decision: APPROVE
mode: final|incremental
iteration: {n}
summary: "Implementation aligns with GOAL.md intent."
criteria_assessment:
  - criterion: "<text>"
    status: "satisfied"
    evidence: "<where in code>"
```

#### FEEDBACK
Use when: Misalignments are fixable and you're confident about what needs to change.

```yaml
decision: FEEDBACK
mode: final|incremental
iteration: {n}
summary: "Implementation needs revision."
issues:
  - id: "issue-{uuid}"      # For tracking across iterations
    location: "<file:line>"
    concern: "<what's wrong>"
    suggestion: "<how to fix>"
    severity: "architectural|functional|style"
    confidence: "high|medium"
    first_flagged: {iteration}  # Track recurrence
```

#### ESCALATE
Use when:
- Loop detected (iteration >= max_iterations)
- Same issue flagged twice (recurring issue)
- Documented intent is ambiguous
- Fixing requires changes outside chunk scope
- Architectural concerns that need operator judgment
- Confidence is low and severity is high

```yaml
decision: ESCALATE
mode: final|incremental
iteration: {n}
reason: "LOOP_DETECTED|RECURRING_ISSUE|AMBIGUITY|SCOPE|ARCHITECTURE|LOW_CONFIDENCE"
summary: "<description>"
context:
  iteration_history: [...]  # If loop-related
  questions: [...]          # If ambiguity-related
```

### Phase 4: Decision Logging

**Always** append to the reviewer's global decision log:

```markdown
## {chunk_directory} - {timestamp}

**Mode:** {incremental|final}
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
<!-- Operator fills this in -->
- [ ] Good example (incorporate into future reviews)
- [ ] Bad example (avoid this pattern)
- [ ] Feedback: _______________
```

Log location: `docs/reviewers/{reviewer}/DECISION_LOG.md`

---

## Implementer Interface: Request Review

The implementer can request an incremental review using:

```
/request-review [reviewer]
```

This invokes the chunk-review skill with `mode: incremental`.

**When to use:**
- "I'm about to implement the caching layer—does this approach align with intent?"
- "I've finished the core logic but haven't done error handling yet—early feedback?"
- "I'm stuck between two approaches—which aligns better with the goal?"

**Implementer provides:**
- Current state of implementation
- Specific questions (optional)
- Areas of uncertainty (optional)

**Reviewer returns:**
- Assessment of alignment so far
- Guidance on questions asked
- Early warnings about potential issues

This does NOT block—implementer can continue regardless of feedback.

---

## Trust Level Behavior

### `observation` (default for new reviewers)
- Log everything in detail
- All decisions surfaced for operator review
- Operator expected to mark examples good/bad

### `calibration`
- Log everything
- Can approve obvious alignments without surfacing
- Escalate anything uncertain
- Operator provides feedback to calibrate judgment

### `delegation`
- Log decisions with less detail
- Auto-decide on delegated categories
- Only surface escalations and edge cases

### `full`
- Minimal logging (escalations only)
- Operator only sees escalations
- Full autonomy on non-escalated decisions

---

## Integration Points

### Workflow Position

```
chunk-create
    │
    ▼
chunk-plan
    │
    ▼
chunk-implement ◄────────────────┐
    │                            │
    │ (/request-review)          │
    ▼                            │
[incremental review] ────────────┤ (feedback loop)
    │                            │
    ▼                            │
chunk-implement continues...     │
    │                            │
    ▼                            │
[final review] ──────────────────┘
    │
    │ (APPROVE only)
    ▼
chunk-complete
```

### Orchestrator Integration

When running under orchestrator:
- Final review is mandatory before COMPLETE phase
- ESCALATE decisions trigger orchestrator attention mechanism
- Loop detection escalations get HIGH priority attention
- Reviewer identity tracked in work unit metadata

---

## Example Few-Shot Context

When reviewing, the reviewer incorporates examples from its decision log:

```markdown
## Examples from your decision history:

### Good Example (API validation)
Chunk: api_input_validation
Decision: FEEDBACK
Issue: "Validation errors returned as 500 instead of 400"
Outcome: Operator marked GOOD - "Correct catch, severity appropriate"

### Bad Example (over-escalation)
Chunk: refactor_utils
Decision: ESCALATE
Reason: "Unclear if helper should be in utils/ or lib/"
Outcome: Operator marked BAD - "This is a style decision, just pick one"

Use these examples to calibrate your judgment on similar situations.
```

---

## Reviewer Lifecycle

```
┌─────────────────────────────────────────────────────────┐
│ 1. CREATE: Start from baseline                          │
│    ve reviewer create api_v1 --from baseline            │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 2. OBSERVE: Review chunks, log decisions                │
│    Operator marks examples good/bad                     │
│    Trust level: observation                             │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 3. CALIBRATE: Examples incorporated into reviews        │
│    Operator provides less frequent feedback             │
│    Trust level: calibration                             │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 4. DELEGATE: Reviewer handles domain autonomously       │
│    Operator only sees escalations                       │
│    Trust level: delegation or full                      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ (domain divergence)
┌─────────────────────────────────────────────────────────┐
│ 5. FORK: Create new reviewer for divergent domain       │
│    ve reviewer fork api_v1 --as ui_v1 --examples "..."  │
│    New reviewer starts at observation trust             │
└─────────────────────────────────────────────────────────┘
```
