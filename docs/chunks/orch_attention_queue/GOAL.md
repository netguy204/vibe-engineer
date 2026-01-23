---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/api.py
- src/orchestrator/state.py
- src/orchestrator/scheduler.py
- src/orchestrator/agent.py
- src/orchestrator/client.py
- src/ve.py
- tests/test_orchestrator_attention.py
- tests/test_orchestrator_cli.py
- tests/test_orchestrator_api.py
code_references:
  - ref: src/orchestrator/api.py#_get_goal_summary
    implements: "Extract goal summary from chunk's GOAL.md Minor Goal section"
  - ref: src/orchestrator/api.py#attention_endpoint
    implements: "GET /attention endpoint returning prioritized queue with enriched items"
  - ref: src/orchestrator/api.py#answer_endpoint
    implements: "POST /work-units/{chunk}/answer endpoint for submitting answers"
  - ref: src/orchestrator/state.py#StateStore::_migrate_v6
    implements: "Database migration adding pending_answer column"
  - ref: src/orchestrator/state.py#StateStore::get_attention_queue
    implements: "Query NEEDS_ATTENTION work units ordered by blocks count and time"
  - ref: src/orchestrator/scheduler.py#Scheduler::_run_work_unit
    implements: "Pass pending_answer to agent runner on resume"
  - ref: src/orchestrator/agent.py#AgentRunner::run_phase
    implements: "Accept and inject answer parameter when resuming sessions"
  - ref: src/orchestrator/models.py#WorkUnit
    implements: "pending_answer field for storing operator answers until resume"
  - ref: src/orchestrator/client.py#OrchestratorClient::get_attention_queue
    implements: "Client method to call GET /attention endpoint"
  - ref: src/orchestrator/client.py#OrchestratorClient::answer_work_unit
    implements: "Client method to call POST /work-units/{chunk}/answer endpoint"
  - ref: src/ve.py#orch_attention
    implements: "ve orch attention CLI command showing attention queue"
  - ref: src/ve.py#orch_answer
    implements: "ve orch answer CLI command to answer questions and resume"
  - ref: tests/test_orchestrator_attention.py
    implements: "Tests for attention queue and pending_answer persistence"
  - ref: tests/test_orchestrator_api.py#TestAttentionEndpoint
    implements: "Tests for GET /attention API endpoint"
  - ref: tests/test_orchestrator_api.py#TestAnswerEndpoint
    implements: "Tests for POST /work-units/{chunk}/answer API endpoint"
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
created_after:
- orch_attention_reason
---

# Chunk Goal

## Minor Goal

Build the attention queue system for the orchestrator - a prioritized list of work units needing operator input, with CLI commands to view and respond to them.

This is Phase 3 from `docs/investigations/parallel_agent_orchestration/design.md`. Building on the scheduling layer (orch_scheduling) and attention reason tracking (orch_attention_reason), this chunk adds the operator-facing UX for managing blocked work. The attention queue is the "interrupt vector" in the OS analogy - when work units need operator decisions, they surface here prioritized by downstream impact.

This chunk enables:
- A prioritized view of all NEEDS_ATTENTION work units
- `ve orch attention` command to show the queue with context
- `ve orch answer` command to respond to agent questions and resume execution
- Priority scoring based on how many other work units are blocked
- Clear visibility into what's blocking parallel progress

## Success Criteria

1. **Attention queue shows NEEDS_ATTENTION work units with priority**
   - `ve orch attention` lists work units in priority order
   - Priority calculated by: blocked_chunk_count + (depth_in_graph * weight)
   - Tie-breaker: time in queue (older items surface first)
   - Each item shows: chunk name, reason, time waiting, blocks count

2. **Attention items display context for decision-making**
   - Question/decision text from `attention_reason` field
   - Phase the work unit is in (GOAL/PLAN/IMPLEMENT/COMPLETE)
   - How many other work units are blocked waiting on this one
   - Summary of chunk goal for context

3. **`ve orch answer` responds to questions and resumes agents**
   - `ve orch answer <chunk> "response text"` answers and resumes
   - Response is injected into the agent session on resume
   - Work unit transitions: NEEDS_ATTENTION → RUNNING
   - Session resumes using saved `session_id` with `options.resume`
   - Error if work unit is not in NEEDS_ATTENTION state

4. **API endpoints support the attention queue**
   - `GET /attention` returns prioritized queue with item details
   - `POST /work-units/{chunk}/answer` submits answer and triggers resume
   - Response includes updated work unit status

5. **Priority scoring reflects downstream impact**
   - Compute `blocked_by` graph from work unit dependencies
   - Count how many work units are transitively blocked by each attention item
   - Higher blocked count = higher priority (surface items that unblock the most work)

## Out of Scope

- Conflict detection between work units (Phase 4: Conflict Oracle)
- Web dashboard (Phase 5: Dashboard)
- Skip/defer functionality for attention items (can be added later)
- Review gates (auto-advance vs require-review decisions)
- Rich question types beyond simple text answers