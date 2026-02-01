---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - tests/
code_references:
  - ref: tests/test_symbols.py
    implements: "Chunk backref for symbolic_code_refs - Symbol extraction tests"
  - ref: tests/test_narrative_consolidation.py
    implements: "Chunk backref for narrative_consolidation - Consolidation tests"
  - ref: tests/test_chunk_suggest_prefix.py
    implements: "Chunk backref for cluster_prefix_suggest - TF-IDF prefix tests"
  - ref: tests/test_artifact_ordering.py
    implements: "Chunk backref for ordering_active_only - Status-aware tip filtering tests"
  - ref: tests/test_external_resolve.py
    implements: "Chunk backref for external_resolve_all_types - Multi-artifact-type resolution tests"
  - ref: tests/test_orchestrator_dashboard.py
    implements: "Chunk backref for orch_dashboard - Dashboard integration tests"
  - ref: tests/test_orchestrator_oracle.py
    implements: "Chunk backref for orch_conflict_oracle - Conflict oracle tests"
  - ref: tests/test_orchestrator_attention.py
    implements: "Chunk backref for orch_attention_queue - Attention queue tests"
  - ref: tests/test_orchestrator_api.py
    implements: "Chunk backref for orch_attention_queue - Attention queue API tests"
narrative: null
investigation: null
subsystems:
  - subsystem_id: workflow_artifacts
    relationship: uses
friction_entries: []
bug_type: null
created_after: ["taskdir_project_refs", "backref_task_context"]
---

# Chunk Goal

## Minor Goal

Restore chunk backreferences to source code that were removed during the chunks-to-subsystems migration, where those backreferences have not been superseded by subsystem references.

### Background

During the migration (commit 9ef703f, 2026-01-17), 674 `# Chunk:` backreferences across 95 files were converted to `# Subsystem:` references. This was appropriate at the time because chunks were being archived and subsystems became the primary documentation. However, chunks have since been restored to `docs/chunks/` (134 chunks now exist), and `backref_task_context` (81fc6e1) re-enabled chunk backreferences in documentation.

The problem: Code that was created by specific chunks now only has coarse-grained subsystem references, losing the fine-grained traceability back to the specific work that created or modified it.

### Scope

This work restores chunk backreferences **selectively**, prioritizing value over completeness.

**Restore when**:
- The chunk reference adds meaningful context beyond what the subsystem reference provides
- The chunk represents significant, cohesive work (feature additions, architectural changes)
- The chunk is still ACTIVE and relevant to understanding the code

**Do NOT restore**:
- References where the subsystem already provides sufficient context (e.g., a file entirely governed by one subsystem doesn't need 15 chunk refs saying "part of workflow_artifacts")
- Low-value chunks: minor fixes, trivial additions, cleanup work
- Chunks with status HISTORICAL or SUPERSEDED
- Chunks that no longer exist (this naturally filters out scratchpad chunks which were removed)

**Description updates**: When restoring, update descriptions to reflect current understanding rather than preserving original (sometimes vague) descriptions.

## Success Criteria

1. **Git archaeology identifies candidate references**: Use `git diff 9ef703f^..9ef703f` to identify chunk references that were converted to subsystem references.

2. **Value-based filtering applied**: Each candidate is evaluated for restoration based on:
   - Does the chunk add context beyond the subsystem? (If subsystem ref says "Orchestrator scheduling" and chunk ref would say "Orchestrator scheduling", skip it)
   - Is the chunk significant work? (Skip trivial chunks like single-line fixes)
   - Is the chunk still ACTIVE? (Skip HISTORICAL/SUPERSEDED)

3. **Selective restoration**: High-value chunk references are restored alongside existing subsystem references. Low-value references are intentionally not restored.

4. **Tests pass**: All existing tests continue to pass.

5. **Documentation**: The chunk's PLAN.md documents which references were restored and which were intentionally skipped (with rationale), providing archaeology for future understanding.