---
status: DOCUMENTED
# MIGRATION NOTE: This subsystem was synthesized from chunks.
# Review all [NEEDS_HUMAN] and [CONFLICT] sections before finalizing.
# Confidence: 75% synthesized, 15% inferred, 10% needs human input
chunks:
  - name: orch_foundation
    relationship: implements
  - name: orch_scheduling
    relationship: implements
  - name: orch_conflict_oracle
    relationship: implements
  - name: orch_dashboard
    relationship: implements
  - name: orch_attention_queue
    relationship: implements
  - name: orch_attention_reason
    relationship: implements
  - name: orch_blocked_lifecycle
    relationship: implements
  - name: orch_activate_on_inject
    relationship: implements
  - name: orch_sandbox_enforcement
    relationship: implements
  - name: orch_verify_active
    relationship: implements
  - name: orch_inject_validate
    relationship: implements
  - name: orch_inject_path_compat
    relationship: implements
  - name: orch_mechanical_commit
    relationship: implements
  - name: orch_agent_question_tool
    relationship: implements
  - name: orch_agent_skills
    relationship: implements
  - name: orch_question_forward
    relationship: implements
  - name: orch_submit_future_cmd
    relationship: implements
  - name: orch_tcp_port
    relationship: implements
  - name: orch_broadcast_invariant
    relationship: implements
  - name: orch_conflict_template_fix
    relationship: implements
code_references:
  - ref: src/orchestrator/state.py#OrchestratorState
    implements: Persistent state management for work units and conflicts
    compliance: COMPLIANT
  - ref: src/orchestrator/scheduler.py#Scheduler
    implements: Work unit scheduling and ready queue management
    compliance: COMPLIANT
  - ref: src/orchestrator/daemon.py#OrchestratorDaemon
    implements: Long-running daemon process for orchestration
    compliance: COMPLIANT
  - ref: src/orchestrator/api.py
    implements: HTTP API for daemon communication
    compliance: COMPLIANT
  - ref: src/orchestrator/agent.py#AgentInterface
    implements: Claude Code agent spawning and management
    compliance: COMPLIANT
  - ref: src/orchestrator/models.py#WorkUnitStatus
    implements: Work unit state machine enum
    compliance: COMPLIANT
  - ref: src/orchestrator/models.py#ConflictType
    implements: Conflict classification enum
    compliance: COMPLIANT
  - ref: src/orchestrator/websocket.py
    implements: Real-time WebSocket updates for dashboard
    compliance: COMPLIANT
proposed_chunks: []
created_after:
  - workflow_artifacts
---

# orchestrator

## Intent

<!-- SYNTHESIS CONFIDENCE: HIGH -->

[SYNTHESIZED] Enable operators to run multiple AI agents in parallel on different chunks of work, with automatic conflict detection, scheduling, and attention routing when agents need human input.

From orch_foundation chunk: "Create the foundational infrastructure for running multiple Claude Code agents in parallel, each working on a separate chunk, with a daemon process managing scheduling and coordination."

From orch_conflict_oracle chunk: "Detect potential conflicts between parallel work units before they cause merge conflicts, using file overlap, symbol overlap, and subsystem relationship analysis."

[NEEDS_HUMAN] Business context and strategic importance:
<!-- Why does this subsystem matter to the organization? -->
<!-- What would break if this subsystem didn't exist? -->
<!-- Consider: Without orchestration, operators must manually manage agent parallelism -->

## Scope

### In Scope

<!-- SYNTHESIS CONFIDENCE: HIGH -->

[SYNTHESIZED] Based on chunk code_references and success criteria:
- **Daemon process**: Long-running background process managing work unit lifecycle
- **Work unit management**: PENDING -> READY -> ASSIGNED -> RUNNING -> (terminal states)
- **Scheduling algorithm**: Priority-based scheduling with conflict awareness
- **Conflict detection**: File overlap, symbol overlap, subsystem relationship analysis
- **Conflict resolution**: Operator verdicts (INDEPENDENT, SERIALIZE, etc.)
- **Attention routing**: Questions from agents forwarded to operators
- **Agent spawning**: Claude Code subprocess management with sandbox enforcement
- **Real-time dashboard**: WebSocket-based status updates
- **Mechanical commits**: Auto-commit support for completed chunks

[INFERRED] From code structure:
- **HTTP API**: RESTful endpoints for daemon control
- **State persistence**: SQLite-based state for crash recovery
- **TCP port configuration**: Configurable daemon binding

### Out of Scope

<!-- SYNTHESIS CONFIDENCE: LOW -->

[NEEDS_HUMAN] What explicitly does NOT belong here:
<!-- This is rarely documented in chunks -->
- [INFERRED] Chunk content creation (belongs to workflow_artifacts)
- [INFERRED] External repository syncing (belongs to cross_repo_operations)
- [INFERRED] Template rendering (belongs to template_system)

## Invariants

<!-- SYNTHESIS CONFIDENCE: HIGH -->

[SYNTHESIZED] From chunk success criteria:

1. **Work units progress through defined state machine**
   - PENDING -> READY -> ASSIGNED -> RUNNING -> (NEEDS_ATTENTION | COMPLETED | FAILED | BLOCKED)
   - Source: orch_foundation, orch_blocked_lifecycle

2. **Only one active work unit per agent at a time**
   - Agents cannot be assigned multiple concurrent work units
   - Source: orch_scheduling

3. **Conflicts must be resolved before parallel execution**
   - Conflicting chunks cannot run simultaneously without INDEPENDENT verdict
   - Source: orch_conflict_oracle

4. **NEEDS_ATTENTION state requires attention_reason**
   - Work units entering NEEDS_ATTENTION must specify why operator input is needed
   - Source: orch_attention_reason

5. **Chunks must be committed before injection**
   - Only committed chunks can be injected into the work pool
   - Source: orch_inject_validate

6. **Chunks must have PLAN.md content for injection**
   - Injection validation checks for plan existence
   - Source: orch_inject_validate

7. **Agents operate within sandbox boundaries**
   - Agent processes have restricted filesystem access
   - Source: orch_sandbox_enforcement

8. **Inject activates FUTURE chunk if one exists**
   - Injecting a chunk that's FUTURE will activate it to IMPLEMENTING
   - Displaced chunk (if any) tracked in work unit metadata
   - Source: orch_activate_on_inject

[NEEDS_HUMAN] Implicit invariants not in chunks:
<!-- What rules exist in code but weren't documented? -->
- Default TCP port 8765 (from code inspection)
- State persisted to SQLite for crash recovery

## Code References

<!-- SYNTHESIS CONFIDENCE: HIGH -->

[SYNTHESIZED] Consolidated from chunk code_references:

### Core Infrastructure
- `src/orchestrator/state.py#OrchestratorState` - Persistent state management
- `src/orchestrator/state.py#WorkUnit` - Work unit data model
- `src/orchestrator/state.py#Conflict` - Conflict data model
- `src/orchestrator/daemon.py#OrchestratorDaemon` - Daemon process class

### Scheduling
- `src/orchestrator/scheduler.py#Scheduler` - Scheduling algorithm
- `src/orchestrator/scheduler.py#_get_ready_with_conflicts` - Conflict-aware ready queue
- `src/orchestrator/models.py#WorkUnitStatus` - State machine enum

### Conflict Management
- `src/orchestrator/models.py#ConflictType` - FILE, SYMBOL, SUBSYSTEM
- `src/orchestrator/models.py#ConflictVerdict` - Resolution verdicts
- `src/orchestrator/state.py#create_conflict` - Conflict creation
- `src/orchestrator/state.py#resolve_conflict` - Conflict resolution

### Agent Interface
- `src/orchestrator/agent.py#AgentInterface` - Agent spawning
- `src/orchestrator/agent.py#spawn_agent` - Subprocess creation

### API
- `src/orchestrator/api.py#inject_chunk` - Inject endpoint
- `src/orchestrator/api.py#attention_queue` - Attention query
- `src/orchestrator/api.py#answer_question` - Question response

### Dashboard
- `src/orchestrator/websocket.py` - WebSocket server

[INFERRED] Additional references found in code but not in chunks:
- `src/orchestrator/__init__.py` - Package init

[NEEDS_HUMAN] Validate these references are current:
<!-- Some chunk references may be stale -->

## Deviations

<!-- SYNTHESIS CONFIDENCE: LOW -->

[NEEDS_HUMAN] Known deviations from ideal:
<!-- Chunks rarely document what's wrong -->
- [INFERRED] Error handling may need standardization across API endpoints
- [INFERRED] Websocket reconnection logic may need hardening

## Chunk Provenance

This subsystem was synthesized from the following chunks:

| Chunk | Status | Contribution | Confidence |
|-------|--------|--------------|------------|
| orch_foundation | ACTIVE | Intent, Invariants 1-2, core entities | HIGH |
| orch_scheduling | ACTIVE | Invariants 2, scheduling code refs | HIGH |
| orch_conflict_oracle | ACTIVE | Invariants 3, conflict code refs | HIGH |
| orch_dashboard | ACTIVE | Dashboard code refs | HIGH |
| orch_attention_queue | ACTIVE | Attention routing code refs | HIGH |
| orch_attention_reason | ACTIVE | Invariant 4 | HIGH |
| orch_blocked_lifecycle | ACTIVE | State machine extensions | HIGH |
| orch_activate_on_inject | ACTIVE | Invariant 8 | HIGH |
| orch_sandbox_enforcement | ACTIVE | Invariant 7 | HIGH |
| orch_verify_active | ACTIVE | Validation logic | HIGH |
| orch_inject_validate | ACTIVE | Invariants 5-6 | HIGH |
| orch_inject_path_compat | ACTIVE | Path handling | MEDIUM |
| orch_mechanical_commit | ACTIVE | Commit automation | MEDIUM |
| orch_agent_question_tool | ACTIVE | Agent tooling | MEDIUM |
| orch_agent_skills | ACTIVE | Agent skills | MEDIUM |
| orch_question_forward | ACTIVE | Question forwarding | MEDIUM |
| orch_submit_future_cmd | ACTIVE | CLI commands | MEDIUM |
| orch_tcp_port | ACTIVE | Configuration | LOW |
| orch_broadcast_invariant | ACTIVE | Event broadcasting | MEDIUM |
| orch_conflict_template_fix | ACTIVE | Template fixes | LOW |
| orch_unblock_transition | FUTURE | (not implemented) | N/A |

## Synthesis Metrics

| Section | Synthesized | Inferred | Needs Human | Conflicts |
|---------|-------------|----------|-------------|-----------|
| Intent | 2 | 0 | 1 | 0 |
| Scope | 9 | 3 | 1 | 0 |
| Invariants | 8 | 0 | 1 | 0 |
| Code References | 15 | 1 | 1 | 0 |
| Deviations | 0 | 2 | 1 | 0 |
| **Total** | **34** | **6** | **5** | **0** |

**Overall Confidence**: 76% (34 synthesized / 45 total items)
