---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/steward-watch.md.jinja2
- src/templates/commands/steward-setup.md.jinja2
code_references:
- ref: src/templates/commands/steward-watch.md.jinja2
  implements: "Conditional DO deploy step in orchestrator monitor loop for DONE chunks"
- ref: src/templates/commands/steward-setup.md.jinja2
  implements: "Deploy step in autonomous mode suggested behavior section"
narrative: null
investigation: null
subsystems:
- subsystem_id: template_system
  relationship: uses
friction_entries: []
bug_type: null
depends_on: []
created_after:
- invite_path_routing_fix
- steward_crossproject_guidance
---

# Chunk Goal

## Minor Goal

Add a "deploy the Durable Object worker" step to the steward's standard operating procedure. When any chunk that impacts Durable Object code (`workers/leader-board/`) completes in the orchestrator, the steward should run `cd workers/leader-board && npm run deploy` and verify it succeeds before posting the changelog entry.

This should be added to:
1. The steward-watch skill template (`src/templates/commands/steward-watch.md.jinja2`) — in the autonomous mode section between "push completed work" and "publish to changelog"
2. The steward-setup skill template (`src/templates/commands/steward-setup.md.jinja2`) — in the suggested autonomous behavior section

The deploy step should be conditional: only trigger when the completed chunk's `code_paths` include files under `workers/`. The steward should read the chunk's GOAL.md frontmatter to check this.

## Success Criteria

- Steward-watch template includes a conditional deploy step for DO-impacting chunks
- Steward-setup template's suggested autonomous behavior includes the deploy step
- `ve init` renders both templates correctly
- The deploy step is clearly documented as conditional (only for worker changes)