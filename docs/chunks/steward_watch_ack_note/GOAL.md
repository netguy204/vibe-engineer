---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/steward-watch.md.jinja2
code_references:
  - ref: src/templates/commands/steward-watch.md.jinja2
    implements: "Ack-all callout in Step 5 of steward-watch skill template"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- board_scp_command
---

# Chunk Goal

## Minor Goal

The steward-watch skill (`steward-watch.md` template) explicitly notes that **every handled message must be acked** via `ve board ack` before the next watch iteration — including bootstrap/initialization messages and messages that don't represent actionable work (e.g., questions answered inline, no-ops).

Without this callout, an agent following the skill may skip the ack step for non-actionable messages, causing the cursor to never advance and the steward to re-receive the same message indefinitely on the next watch cycle.

## Success Criteria

- The steward-watch skill template contains a clear note in the ack step (Step 5) or as a prominent callout that **all** messages must be acked, not just those that produce chunks
- The note explicitly calls out the failure mode: without acking, the cursor doesn't advance and the steward loops on the same message
- The skill template renders correctly via `ve init`