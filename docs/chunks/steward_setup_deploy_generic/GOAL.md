---
status: HISTORICAL
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/steward-setup.md.jinja2
code_references:
- ref: src/templates/commands/steward-setup.md.jinja2
  implements: "Interview question 7 (optional deploy command) and generic step 6 in autonomous mode behavior template"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: implementation
depends_on: []
created_after:
- shutdown_tz_normalization
---

# Chunk Goal

## Minor Goal

Remove project-specific deploy instructions from the `/steward-setup` skill
template. The autonomous mode behavior section currently hardcodes a
leader-board-specific deploy step (`cd workers/leader-board && npm run deploy`)
that leaks into every project's generated STEWARD.md.

### The problem

Step 6 in the "Autonomous mode suggested behavior section" of the steward-setup
skill references a hardcoded path (`workers/leader-board`), assumes Cloudflare
Workers + npm toolchain, and assumes a `workers/` directory exists. For every
non-leader-board project, this is noise. An agent that doesn't audit carefully
may paste it verbatim into a Python project's STEWARD.md.

### The fix

Option 3 from the reporter (preferred): make the steward-setup interview ask
an optional "post-push deploy command" question. If provided, inject the
command into the STEWARD.md template's deploy step. If empty, omit the step
entirely. This keeps the deploy-after-push pattern discoverable without
hardcoding project-specific commands.

Fallback (simpler): Option 2 — reframe the deploy step as an illustrative
example rather than a default, with clear "add your own command here" language.

### Where to change

`src/templates/commands/steward-setup.md.jinja2` — the autonomous mode
behavior template section that generates STEWARD.md content during the
interview flow.

### Cross-project context

Reported by the newly-set-up `world-model-steward`. Every steward setup in
the swarm hits this.

## Success Criteria

- steward-setup no longer hardcodes `workers/leader-board` or `npm run deploy`
- Deploy step is either interview-driven (inject provided command) or clearly
  framed as an example the operator should customize
- Projects without deploy steps get a clean STEWARD.md without dead commands
- leader-board's existing STEWARD.md is unaffected (already generated)

