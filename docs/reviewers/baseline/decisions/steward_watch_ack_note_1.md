---
decision: APPROVE
summary: "All success criteria satisfied — clear ack-every-message note added to Step 5 of steward-watch template with failure mode callout, template renders correctly"
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: The steward-watch skill template contains a clear note in the ack step (Step 5) or as a prominent callout that **all** messages must be acked, not just those that produce chunks

- **Status**: satisfied
- **Evidence**: `src/templates/commands/steward-watch.md.jinja2` lines 109-113 — bold "**Every message must be acked.**" paragraph added directly after the existing "Critical" paragraph in Step 5, explicitly listing bootstrap/initialization messages, questions answered inline, no-ops, and duplicates as examples that still require acking.

### Criterion 2: The note explicitly calls out the failure mode: without acking, the cursor doesn't advance and the steward loops on the same message

- **Status**: satisfied
- **Evidence**: Same paragraph (lines 111-113) states: "Without it, the cursor stays in place and the next watch cycle re-delivers the same message, causing the steward to loop on it indefinitely."

### Criterion 3: The skill template renders correctly via `ve init`

- **Status**: satisfied
- **Evidence**: Rendered output at `.claude/commands/steward-watch.md` contains the identical note. `uv run pytest tests/test_steward_skills.py` passes (2/2 tests). The diff between template and rendered output is consistent.
