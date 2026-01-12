---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/orchestrator/oracle.py
  - src/orchestrator/models.py
  - src/orchestrator/state.py
  - src/orchestrator/api.py
  - src/orchestrator/scheduler.py
  - src/orchestrator/client.py
  - src/ve.py
  - tests/test_orchestrator_oracle.py
  - tests/test_orchestrator_state.py
  - tests/test_orchestrator_scheduler.py
  - tests/test_orchestrator_cli.py
  - tests/test_orchestrator_integration.py
code_references:
  - ref: src/orchestrator/oracle.py#ConflictOracle
    implements: "Core conflict analysis class with progressive analysis by lifecycle stage"
  - ref: src/orchestrator/oracle.py#ConflictOracle::analyze_conflict
    implements: "Main conflict analysis entry point using stage-appropriate analysis"
  - ref: src/orchestrator/oracle.py#ConflictOracle::should_serialize
    implements: "Three-way verdict system (INDEPENDENT/SERIALIZE/ASK_OPERATOR)"
  - ref: src/orchestrator/oracle.py#ConflictOracle::_analyze_completed_stage
    implements: "Symbol-level conflict detection using code_references frontmatter"
  - ref: src/orchestrator/oracle.py#ConflictOracle::_analyze_plan_stage
    implements: "File overlap detection via PLAN.md Location: lines"
  - ref: src/orchestrator/oracle.py#ConflictOracle::_extract_locations_from_plan
    implements: "Parsing Location: lines from PLAN.md files"
  - ref: src/orchestrator/oracle.py#AnalysisStage
    implements: "Lifecycle stage constants for progressive analysis"
  - ref: src/orchestrator/models.py#ConflictVerdict
    implements: "Three-way verdict enum (INDEPENDENT/SERIALIZE/ASK_OPERATOR)"
  - ref: src/orchestrator/models.py#ConflictAnalysis
    implements: "Conflict analysis result model with overlapping files/symbols"
  - ref: src/orchestrator/models.py#WorkUnit
    implements: "Extended WorkUnit with conflict_verdicts and conflict_override fields"
  - ref: src/orchestrator/state.py#StateStore::_migrate_v7
    implements: "Database migration for conflict storage tables and columns"
  - ref: src/orchestrator/state.py#StateStore::save_conflict_analysis
    implements: "Conflict analysis persistence to SQLite"
  - ref: src/orchestrator/state.py#StateStore::get_conflict_analysis
    implements: "Retrieve conflict analysis for chunk pair"
  - ref: src/orchestrator/state.py#StateStore::list_conflicts_for_chunk
    implements: "List all conflicts involving a chunk"
  - ref: src/orchestrator/state.py#StateStore::clear_conflicts_for_chunk
    implements: "Clear stale conflicts on lifecycle advancement"
  - ref: src/orchestrator/api.py#get_conflicts_endpoint
    implements: "GET /conflicts/{chunk} API endpoint"
  - ref: src/orchestrator/api.py#list_all_conflicts_endpoint
    implements: "GET /conflicts API endpoint with verdict filter"
  - ref: src/orchestrator/api.py#analyze_conflicts_endpoint
    implements: "POST /conflicts/analyze API endpoint"
  - ref: src/orchestrator/api.py#resolve_conflict_endpoint
    implements: "POST /work-units/{chunk}/resolve API endpoint for operator resolution"
  - ref: src/orchestrator/scheduler.py#Scheduler::_check_conflicts
    implements: "Conflict checking before dispatch; populates blocked_by"
  - ref: src/orchestrator/scheduler.py#Scheduler::_reanalyze_conflicts
    implements: "Re-analyze conflicts on phase advancement for more precision"
  - ref: src/orchestrator/client.py#OrchestratorClient::get_conflicts
    implements: "Client method for getting conflicts for a chunk"
  - ref: src/orchestrator/client.py#OrchestratorClient::analyze_conflicts
    implements: "Client method for triggering conflict analysis"
  - ref: src/orchestrator/client.py#OrchestratorClient::resolve_conflict
    implements: "Client method for submitting operator resolution"
  - ref: src/ve.py#orch_conflicts
    implements: "ve orch conflicts CLI command"
  - ref: src/ve.py#orch_resolve
    implements: "ve orch resolve CLI command for operator resolution"
  - ref: src/ve.py#orch_analyze
    implements: "ve orch analyze CLI command for manual conflict analysis"
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
created_after:
- orch_inject_path_compat
- orch_submit_future_cmd
---

# Chunk Goal

## Minor Goal

Implement the **Conflict Oracle** - a progressive analysis system that determines whether chunks can be safely parallelized or must be serialized. The oracle provides goal-level semantic comparison, plan-level file/symbol analysis, and surfaces uncertain conflicts to the operator for judgment via `ve orch resolve`.

This chunk enables the orchestrator to make intelligent scheduling decisions about parallel work. Without conflict detection, the orchestrator would either serialize all work (sacrificing throughput) or parallelize blindly (causing merge conflicts). The conflict oracle provides the judgment layer that balances throughput against merge safety.

## Success Criteria

1. **Progressive analysis at each stage**:
   - PROPOSED: LLM semantic comparison of chunk prompts
   - GOAL exists: LLM comparison of intent + scope from GOAL.md
   - PLAN exists: File overlap detection via `Location:` lines + LLM symbol prediction
   - COMPLETED: Exact symbol overlap from `code_references` frontmatter

2. **Three-way verdict system**: `should_serialize(chunk_a, chunk_b)` returns:
   - `INDEPENDENT` (confidence > 0.8 no overlap) - parallelize freely
   - `SERIALIZE` (confidence > 0.8 overlap) - must sequence
   - `ASK_OPERATOR` (uncertain) - queue attention item for operator judgment

3. **Symbol-level granularity**: Analysis considers symbol overlap (e.g., `src/ve.py#suggest_prefix_cmd` vs `src/ve.py#cluster_rename_cmd`), not just file overlap

4. **`ve orch resolve` command**: Allows operator to resolve uncertain conflicts with `parallelize` or `serialize` verdicts

5. **Integration with scheduler**: Blocked work units have `blocked_by` populated based on oracle verdicts; verdicts re-evaluated as chunks advance through lifecycle

6. **Tests pass**: Unit tests for conflict analysis at each stage; integration tests for scheduler interaction

