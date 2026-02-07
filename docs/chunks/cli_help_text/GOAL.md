---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/cli/__init__.py
  - src/cli/chunk.py
  - src/cli/narrative.py
  - src/cli/subsystem.py
  - src/cli/investigation.py
  - src/cli/friction.py
  - src/cli/task.py
  - src/cli/orch.py
  - src/cli/reviewer.py
  - src/cli/utils.py
code_references:
  - ref: src/cli/chunk.py#chunk
    implements: "Enriched command group help text for chunk commands"
  - ref: src/cli/chunk.py#create
    implements: "Documented chunk start alias in docstring"
  - ref: src/cli/narrative.py#narrative
    implements: "Enriched command group help text for narrative commands"
  - ref: src/cli/subsystem.py#subsystem
    implements: "Enriched command group help text for subsystem commands"
  - ref: src/cli/investigation.py#investigation
    implements: "Enriched command group help text for investigation commands"
  - ref: src/cli/friction.py#friction
    implements: "Enriched command group help text for friction commands"
  - ref: src/cli/task.py#task
    implements: "Enriched command group help text for task commands"
  - ref: src/cli/orch.py#orch
    implements: "Enriched command group help text for orchestrator commands"
  - ref: src/cli/reviewer.py#reviewer
    implements: "Enriched command group help text for reviewer commands"
  - ref: src/cli/utils.py#format_not_found_error
    implements: "Helper function for actionable not-found error messages"
narrative: arch_consolidation
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_api_retry
---

# Chunk Goal

## Minor Goal

Improve CLI usability for new users by enriching group-level help text, adding actionable error messages, and documenting command aliases.

Currently, command group help strings are terse ("Chunk commands", "Narrative commands", "Subsystem commands") and don't explain what these concepts mean to newcomers. Error messages like "Chunk 'foo' not found" provide no guidance on next steps. The `chunk start` alias for `chunk create` exists but is undocumented in help output.

This chunk enhances discoverability by:
1. Adding one-sentence concept descriptions to each command group's help text
2. Enriching "not found" errors with actionable suggestions (e.g., "run `ve chunk list` to see available chunks")
3. Documenting the `chunk start` alias in help output

This addresses a gap in the CLI's onboarding experience without requiring changes to core functionality or workflows.

## Success Criteria

1. Each command group (`@click.group()` decorator) has enriched help text that includes a one-sentence concept description:
   - `chunk`: "Manage chunks - discrete units of implementation work"
   - `narrative`: "Manage narratives - multi-chunk initiatives with upfront decomposition"
   - `subsystem`: "Manage subsystems - documented architectural patterns"
   - `investigation`: "Manage investigations - exploratory documents for understanding before acting"
   - `friction`: "Manage friction log - accumulative ledger for pain points"
   - `task`: "Manage task directories - cross-repository work coordination"
   - `orch`: "Manage orchestrator - parallel chunk execution across worktrees"
   - `reviewer`: "Manage reviewer agent - automated decision tracking and review"

2. "Not found" error messages include actionable suggestions:
   - Chunk not found → suggest `ve chunk list` or `ve chunk list --recent`
   - Narrative not found → suggest `ve narrative list`
   - Subsystem not found → suggest `ve subsystem list`
   - Investigation not found → suggest `ve investigation list`

3. The `chunk start` alias is documented in help output (e.g., via command docstring or help text showing "Aliases: start")

4. Changes are localized to CLI help strings and error message formatting - no changes to command behavior or validation logic


