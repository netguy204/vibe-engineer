---
discovered_by: claude
discovered_at: 2026-04-26T02:22:17+00:00
severity: medium
status: open
resolved_by: null
artifacts:
  - docs/chunks/orch_agent_question_tool/GOAL.md
  - src/orchestrator/agent.py
---

# orch_agent_question_tool over-claims that an `AskOperator` tool exists

## Claim

`docs/chunks/orch_agent_question_tool/GOAL.md` asserts in its prose
(lines 37, 43):

- "**Solution**: Provide agents with an explicit `AskOperator` tool (or
  similar) that they must use when they need operator input."
- Success criterion: "Agent has access to an `AskOperator` tool (or
  equivalent) for requesting operator input"
- Success criterion: "Orchestrator only sets NEEDS_ATTENTION with a
  'question' reason when the tool is invoked"

The prose frames the chunk as introducing a new, named, explicit
operator-question tool — replacing text-parsing heuristics for question
detection.

## Reality

There is no `AskOperator` tool in the codebase. `grep -rn "AskOperator"
src/ docs/` returns only the chunk's own GOAL.md.

The actual machinery (in `src/orchestrator/agent.py`) intercepts
Claude Code's built-in `AskUserQuestion` tool via a `PreToolUse` hook
(`create_question_intercept_hook`, line 289), captures the question
data, blocks the tool call, and sets the work unit to NEEDS_ATTENTION.
This was implemented by `orch_question_forward` and
`orch_question_capture`, not by this chunk — those chunk names appear
in `# Chunk:` backreferences at the relevant code sites
(`src/orchestrator/agent.py:288, 522, 755`).

The chunk's own `code_references` only claim removal of the
`_is_error_result()` heuristic from `AgentRunner::run_phase` and
`AgentRunner::resume_for_active_status`, which is verifiable in the
code (lines 706-711, 902-904 use `getattr(message, "is_error", False)`
exclusively, no heuristic call). That part of the chunk is real.

So the chunk legitimately delivers heuristic-removal, but its prose
and success criteria over-claim by also asserting introduction of an
`AskOperator` tool — a tool that does not exist by that name and was
not introduced by this chunk. The actual question-capture mechanism
exists but is owned by sibling chunks.

## Workaround

None — the audit only logs. A reader of this GOAL.md will look for
`AskOperator` in the codebase and not find it. They should instead
read `orch_question_forward` and `orch_question_capture` for the
actual mechanism (PreToolUse hook on the built-in AskUserQuestion).

## Fix paths

1. **Narrow the goal**: rewrite the prose and success criteria to
   reflect what this chunk actually delivered (removal of
   `_is_error_result()` heuristic and reliance on the SDK `is_error`
   flag), and cross-reference `orch_question_forward` /
   `orch_question_capture` for the question-capture mechanism that
   sister chunks own. Drop `AskOperator` references.
2. **Rename the chunk's contract**: if the operator's intent is for
   this chunk to OWN the question-tool contract (not the heuristic
   removal), then make `code_references` cover the hook code in
   `src/orchestrator/agent.py:289` and update prose to say
   `AskUserQuestion + PreToolUse hook` rather than a fictional
   `AskOperator`.
