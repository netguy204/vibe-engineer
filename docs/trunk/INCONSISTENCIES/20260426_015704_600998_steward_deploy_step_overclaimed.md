---
discovered_by: claude
discovered_at: 2026-04-26T01:57:04Z
severity: medium
status: open
resolved_by: null
artifacts:
  - docs/chunks/steward_deploy_step/GOAL.md
---

## Claim

`docs/chunks/steward_deploy_step/GOAL.md` (status ACTIVE) asserts:

- Success criterion 1: "Steward-watch template includes a conditional deploy step for DO-impacting chunks"
- `code_references[0]`: `src/templates/commands/steward-watch.md.jinja2` implements "Conditional DO deploy step in orchestrator monitor loop for DONE chunks"
- Body prose: the deploy step "should be added to: 1. The steward-watch skill template (`src/templates/commands/steward-watch.md.jinja2`) — in the autonomous mode section between 'push completed work' and 'publish to changelog'"

## Reality

`src/templates/commands/steward-watch.md.jinja2` carries only a backreference comment header on line 8 (`{# Chunk: docs/chunks/steward_deploy_step - Conditional DO deploy step for DONE chunks #}`). The body of the file contains no deploy step — Step 3's autonomous-mode bullets go from "Inject into the orchestrator" straight to "Summarize the outcome for the changelog" with no deploy logic between push and changelog.

The actual conditional deploy logic lives in `src/templates/commands/orchestrator-monitor.md.jinja2` lines 180-185, under the `#### DONE` section:

```
1. **Conditional deploy:** Read the chunk's `GOAL.md` frontmatter and inspect
   its `code_paths` list. If any path starts with `workers/`, a deploy may be
   needed. Check the project's README or deploy configuration for the correct
   deploy command rather than hardcoding one. Run the deploy and verify it
   exits cleanly. ...
```

That file is not in the chunk's `code_paths` list, and its `code_references` claim points at the wrong file. Steward-setup.md.jinja2's deploy step (lines 156-159 of the autonomous suggested behavior section) is correctly referenced.

## Workaround

None applied this audit pass — veto rule fired (over-claim suppresses tense rewrite).

The fix is structurally clear (move the `code_references` entry from `steward-watch.md.jinja2` to `orchestrator-monitor.md.jinja2`, add the latter to `code_paths`, and reword success criterion 1 to name the orchestrator-monitor template), but it touches `code_references` and `code_paths` — out of scope for this audit's prose-only rewrite remit. Logged for follow-up.

## Fix paths

1. Update `code_paths` to include `src/templates/commands/orchestrator-monitor.md.jinja2`; rewrite the `code_references` entry to point at that file's "Conditional deploy" step; restate success criterion 1 to reference the orchestrator-monitor template; rewrite the body to describe what the system now does (the orchestrator monitor's DONE handler runs a conditional deploy; the steward-setup template embeds the operator's deploy command into the SOP).
2. If the chunk is regarded as a one-time scaffolding step now superseded by the orchestrator-monitor's own ownership of the deploy step, historicalize via Pattern B — but verify first that no other chunk uniquely owns the "deploy lives in the DONE handler" decision.
