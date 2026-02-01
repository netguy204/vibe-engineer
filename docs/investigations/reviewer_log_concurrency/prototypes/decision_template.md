---
# Decision Record
# Path: docs/reviewers/{reviewer}/decisions/{chunk}_{iteration}.md
# Instantiated by: ve reviewer decision create <chunk> [--iteration N]

decision: null  # APPROVE | FEEDBACK | ESCALATE
summary: null   # One-sentence rationale

# --- Operator review (filled in later) ---
# Union type: string ("good" | "bad") or map ({ feedback: "<message>" })
operator_review: null
---

## Criteria Assessment

<!-- For each success criterion in GOAL.md -->

### Criterion 1: [criterion text from GOAL.md]

- **Status**: satisfied | gap | unclear
- **Evidence**: [What implementation evidence supports this assessment]

### Criterion 2: [criterion text from GOAL.md]

- **Status**: satisfied | gap | unclear
- **Evidence**: [What implementation evidence supports this assessment]

<!-- Continue for all criteria -->

## Feedback Items

<!-- For FEEDBACK decisions only. Delete section if APPROVE. -->

### Issue 1

- **Problem**: [What's wrong or missing]
- **Suggestion**: [Recommended fix]
- **Severity**: blocking | suggestion

## Escalation Reason

<!-- For ESCALATE decisions only. Delete section if APPROVE/FEEDBACK. -->

- **Ambiguity**: [What's unclear in the documented intent]
- **Options considered**:
  1. [Option A]
  2. [Option B]
