

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Edit the Jinja2 source template at `src/templates/commands/orchestrator-monitor.md.jinja2`
to add guardrails that prevent four observed anti-patterns. The changes are:

1. **Add a prominent "DO NOT" guardrails section** near the top of the instructions
   (after the argument parsing section, before the first step) so agents see the
   constraints before they start acting.

2. **Rewrite the DONE status handler** to remove the manual merge/branch-delete
   instructions entirely, replacing them with a clear statement that the
   orchestrator handles merge automatically.

3. **Add CWD verification reminders** after any instruction that inspects a
   worktree path, and before any git operations.

4. **Add a clean working tree check** before any git operations in the
   NEEDS_ATTENTION handler.

After editing the source template, re-render via `uv run ve init` and verify the
output.

Per DEC-005, the template already avoids prescribing git commit operations from
the operator side. This chunk extends that principle by preventing the *monitor
agent* from performing git operations that the orchestrator owns.

**Testing:** Per TESTING_PHILOSOPHY.md, template content (prose) is not
unit-tested. We verify templates render without error. The existing template
render test suite covers this — re-rendering via `ve init` and confirming no
errors is sufficient. No new tests are needed.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk USES the orchestrator
  subsystem. The template governs how monitoring agents interact with orchestrator
  work units. No code changes to the orchestrator itself — only the skill template.
- **docs/subsystems/template_system** (DOCUMENTED): This chunk modifies a Jinja2
  command template following the existing template rendering pattern.

## Sequence

### Step 1: Add "DO NOT" guardrails section to the template

Insert a new `### Guardrails — DO NOT` section in the Jinja2 source template
(`src/templates/commands/orchestrator-monitor.md.jinja2`) immediately after the
`### Argument Parsing` section (after the `---` divider on line 43) and before
`### Step 1: Immediate First Check`.

The section should contain four clearly numbered rules:

1. **DO NOT intervene on DONE chunks.** DONE chunks are finalized by the
   orchestrator automatically (merge + branch cleanup). Only act on
   NEEDS_ATTENTION status. If you see DONE, report it and remove from the
   monitored set — nothing else.

2. **DO NOT run `ve orch start` or `ve orch stop`.** The orchestrator daemon is
   managed by the operator. If `ve orch ps` returns "not running," it may be a
   transient issue or a CWD mismatch. Report the issue to the operator; never
   start or stop the orchestrator yourself.

3. **DO NOT run git commands from worktree directories.** After inspecting a
   worktree at `.ve/chunks/<name>/worktree/`, always verify your CWD is the
   project root before running any git operations. Run `pwd` and confirm it
   matches the project root.

4. **DO NOT leave uncommitted changes on main.** Before any git operation, run
   `git status` and confirm a clean working tree. If there are uncommitted
   changes, stop and escalate to the operator rather than committing or
   discarding them.

Location: `src/templates/commands/orchestrator-monitor.md.jinja2`, inside the
`{% raw %}` block, between lines 43 and 44.

### Step 2: Rewrite the DONE status handler

Replace the current `#### DONE` section (lines 139–162 of the source template)
which instructs agents to manually merge branches and delete them. The new
version should:

1. State clearly: "No action needed — the orchestrator handles merge and branch
   cleanup automatically."
2. Keep the **conditional deploy** step (check `code_paths` for `workers/`
   paths) since this is post-merge operator-side action.
3. Keep the **changelog posting** step.
4. Keep the **remove from monitored set** step.
5. Remove all `git merge`, `git branch -d`, and `git log ... ^main` commands
   from this section.

### Step 3: Add CWD verification to NEEDS_ATTENTION handler

In the NEEDS_ATTENTION section, after the "Inspect the branch" step (which uses
`git log` and `git diff` on `orch/<chunk>` — these are remote-ref operations
safe from any directory), add a reminder before the decision tree:

> **Before any git operations below**, verify CWD is the project root:
> ```
> pwd  # Must be project root, NOT a worktree directory
> git status  # Must show clean working tree
> ```

This addresses guardrails #3 and #4 for the one section where the monitoring
agent may still perform git operations (merge conflict resolution on
NEEDS_ATTENTION).

### Step 4: Update the `/loop` prompt in Step 2

Update the self-contained `/loop` prompt (lines 66–82) to reflect the changed
DONE handler. Replace the DONE line:

**Before:**
```
- DONE: check chunk GOAL.md code_paths for worker paths; if any start with
  workers/, check the project README or deploy config for the deploy command
  and run it. Post changelog if channel provided: ...
  Remove chunk from monitored set.
```

**After:**
```
- DONE: no action needed — orchestrator handles merge automatically. Check
  code_paths for worker deploys if applicable. Post changelog if channel
  provided: ... Remove chunk from monitored set.
```

Also add to the loop prompt preamble:
```
GUARDRAILS: Never run `ve orch start/stop`. Never run git commands from
worktree directories. Verify `pwd` is project root before git ops.
```

### Step 5: Update the chunk backreference comment

Update the chunk backreference on line 6 of the template to also reference this
guardrails chunk:

```
{# Chunk: docs/chunks/orchestrator_monitor_skill - Orchestrator monitor slash command #}
{# Chunk: docs/chunks/orch_monitor_guardrails - Monitoring guardrails against anti-patterns #}
```

### Step 6: Re-render and verify

1. Run `uv run ve init` to re-render the template
2. Verify the rendered output at `.claude/commands/orchestrator-monitor.md`
   contains the guardrails section and updated DONE handler
3. Run `uv run pytest tests/ -x -q` to confirm no regressions

## Dependencies

None. This chunk only modifies a Jinja2 template — no new libraries or
infrastructure required. The `orchestrator_monitor_skill` chunk that created
the original template is already ACTIVE.

## Risks and Open Questions

- The NEEDS_ATTENTION handler still instructs agents to perform `git merge` for
  merge-failure cases. This is intentional — NEEDS_ATTENTION means the
  orchestrator has already given up on automatic resolution and is asking for
  help. The guardrails ensure agents verify CWD and clean working tree before
  doing so, but the merge itself remains a valid manual intervention.
- The `/loop` prompt is a compressed summary. Balancing brevity (to fit in a
  single prompt) with including guardrails requires careful wording.

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