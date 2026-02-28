---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/orchestrator-investigate.md.jinja2
code_references:
  - ref: src/templates/commands/orchestrator-investigate.md.jinja2#Scenario F
    implements: "Partial merge recovery - docs on main, implementation on branch"
  - ref: src/templates/commands/orchestrator-investigate.md.jinja2#Scenario G
    implements: "Systematic code bug recovery - batch retry affected chunks"
  - ref: src/templates/commands/orchestrator-investigate.md.jinja2#Resolution F
    implements: "Step-by-step recovery for partial merge scenario"
  - ref: src/templates/commands/orchestrator-investigate.md.jinja2#Resolution G
    implements: "Code bug fix and batch retry workflow"
  - ref: src/templates/commands/orchestrator-investigate.md.jinja2#status DONE vs delete warning
    implements: "Critical warning distinguishing status DONE from delete"
narrative: null
investigation: orch_stuck_recovery
subsystems:
- subsystem_id: orchestrator
  relationship: implements
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_merge_rebase_retry
- orch_rename_propagation
---

# Chunk Goal

## Minor Goal

Add two new scenarios to the `/orchestrator-investigate` skill template (`src/templates/commands/orchestrator-investigate.md.jinja2`) that cover recovery paths not addressed by the current Scenarios A-E:

**Scenario F: Implementation on branch, docs on main (partial merge)**
When a FUTURE chunk's docs (GOAL.md, PLAN.md) are committed to main and the orchestrator runs PLAN/IMPLEMENT in a worktree, but a later phase (REVIEW/COMPLETE) fails — main has commits mentioning the chunk name (creating a "merge illusion") but implementation code lives only on the `orch/` branch. The current scenarios don't warn about this or provide recovery steps. Diagnostic: `git log --oneline orch/<chunk> ^main` shows unmerged implementation commits.

**Scenario G: Systematic code bug affecting all chunks in the same phase**
When a bug in VE/orchestrator code (e.g., missing import, schema error) causes every chunk reaching a particular phase to fail identically. The current Scenario C covers individual agent failure but not framework-level bugs requiring: code fix → commit → restart orchestrator → batch retry. Should also warn that `work-unit delete` destroys branches.

Also add a general warning distinguishing `work-unit status DONE` (preserves branch) from `work-unit delete` (force-deletes branch with `-D`).

## Success Criteria

- Scenario F added to Phase 2 of the orchestrator-investigate template with: symptoms, diagnosis, diagnostic steps (verify branch has unmerged commits, check what's on main), critical warning about delete, and full resolution workflow (merge → resolve conflicts → set IMPLEMENTING → chunk-complete → commit)
- Scenario G added with: symptoms (multiple NEEDS_ATTENTION with same error), diagnosis, diagnostic steps (compare attention_reasons, check orchestrator.log), and resolution (fix code → commit → restart → batch retry with state reset)
- A warning box or note added to the Resolution section distinguishing `work-unit status DONE` from `work-unit delete` and when to use each
- Template re-rendered via `ve init` and the rendered command file is updated
- Existing scenarios A-E are unchanged