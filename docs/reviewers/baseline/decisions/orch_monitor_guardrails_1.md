---
decision: APPROVE
summary: "All five success criteria satisfied — guardrails section with four anti-pattern rules added, DONE handler rewritten, start/stop warning present, CWD verification and clean working tree checks included"
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `/orchestrator-monitor` template includes a "DO NOT" section with all four guardrails

- **Status**: satisfied
- **Evidence**: Lines 46–67 of `src/templates/commands/orchestrator-monitor.md.jinja2` contain a `### Guardrails — DO NOT` section with four numbered rules covering: (1) no intervention on DONE chunks, (2) no `ve orch start/stop`, (3) no git commands from worktree directories, (4) no uncommitted changes on main.

### Criterion 2: DONE status handler says "no action needed — orchestrator handles merge automatically"

- **Status**: satisfied
- **Evidence**: Lines 174–177 of the template: "No action needed — the orchestrator handles merge and branch cleanup automatically. Do NOT manually merge or delete the branch." All `git merge` and `git branch -d` commands removed from DONE handler. The `/loop` prompt (line 102) also updated: "DONE: no action needed — orchestrator handles merge automatically."

### Criterion 3: Template warns against `ve orch start/stop` from monitoring context

- **Status**: satisfied
- **Evidence**: Guardrail #2 (lines 54–56) explicitly warns against `ve orch start` and `ve orch stop`. The `/loop` prompt preamble (lines 92–93) includes "Never run `ve orch start/stop`."

### Criterion 4: Template includes CWD verification reminder after any worktree inspection

- **Status**: satisfied
- **Evidence**: Lines 139–146 in the NEEDS_ATTENTION handler add a step 3 ("Before any git operations below") with `pwd` and `git status` checks, placed after the branch inspection step and before the decision tree. The `/loop` prompt (line 93) also includes "Verify `pwd` is project root before git ops."

### Criterion 5: Template includes clean working tree check before any git operations

- **Status**: satisfied
- **Evidence**: Same step 3 (lines 139–146) combines CWD verification with clean working tree check (`git status # Must show clean working tree`). Guardrail #4 (lines 63–66) also establishes this as a top-level rule. Both the NEEDS_ATTENTION handler and the `/loop` prompt enforce this.
