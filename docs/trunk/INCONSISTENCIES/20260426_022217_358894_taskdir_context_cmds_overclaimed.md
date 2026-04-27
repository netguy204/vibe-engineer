---
discovered_by: claude
discovered_at: 2026-04-26T02:22:17+00:00
severity: low
status: open
resolved_by: null
artifacts:
  - docs/chunks/taskdir_context_cmds/GOAL.md
  - docs/subsystems/workflow_artifacts/OVERVIEW.md
---

# taskdir_context_cmds claims an invariant extension that did not happen

## Claim

`docs/chunks/taskdir_context_cmds/GOAL.md` lists this success
criterion (line 91-92):

> "Hard Invariant #11 in `workflow_artifacts` subsystem is extended
> or a new invariant is added to document task-context requirements
> for operational commands"

The chunk's prose also frames the work as closing "a semantic gap in
the task-context implementation" with "operational commands"
(`overlap`, `validate`, `activate`).

## Reality

`docs/subsystems/workflow_artifacts/OVERVIEW.md` Hard Invariants list
(lines 365-422) contains exactly 11 invariants, the same as before
this chunk. Hard Invariant #11 covers `--projects` flag for artifact
**creation** commands (`ve chunk create`, `ve narrative create`,
etc.) — not operational commands like `overlap`, `validate`,
`activate`.

There is no extension of #11 mentioning operational commands, and no
new invariant #12 covering them. The behavioral implementation in
`src/cli/chunk.py` (functions `activate`, `validate`, `overlap`) does
correctly support task context, and `src/task_utils.py` provides the
underlying helpers — the *code* matches the chunk's behavioral
intent. But the documented invariant required by success criterion
#7 is missing.

## Workaround

None — the audit only logs. The behavioral implementation is real
and reliable; only the subsystem-level invariant documentation is
absent.

## Fix paths

1. **Add an invariant**: extend Hard Invariant #11 with a sentence
   covering operational commands, OR add a new Hard Invariant #12 in
   `workflow_artifacts/OVERVIEW.md` codifying that task-aware
   operational commands (`overlap`, `validate`, `activate`) must
   resolve project-qualified references and traverse task context.
   Then mark this chunk's success criterion satisfied.
2. **Drop the success criterion**: if the operator decides invariant
   documentation is not warranted for operational commands (the
   pattern is already implicit from creation-command precedent),
   remove success criterion #7 from this chunk's GOAL.md.

## Note on metadata fix

While auditing, several `code_references` in this chunk pointed at
`src/ve.py#activate` and `src/ve.py#overlap`, but `src/ve.py` is now
just a thin entry point (`from cli import cli`). The actual handlers
moved to `src/cli/chunk.py#activate` and `src/cli/chunk.py#overlap`
(per `cli_modularize` chunk). This audit fixes those refs in place
since the correct target is unambiguous.
