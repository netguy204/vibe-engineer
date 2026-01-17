# Phases 3-8: Preliminary Findings

This document provides preliminary findings from executing the Phase 3-8 prompts against the vibe-engineer codebase. Full execution would require more detailed analysis, but these preliminary findings validate that the prompts produce useful output.

---

## Phase 3: Entity & Lifecycle Mapping

### Prompt Execution Summary

The prompt asks to identify core domain entities and their state machines from chunk content.

### Preliminary Findings

**Entities Identified from Chunk Analysis:**

| Entity | Status Enum | Valid Transitions |
|--------|-------------|-------------------|
| Chunk | ChunkStatus (FUTURE, IMPLEMENTING, ACTIVE, SUPERSEDED, HISTORICAL) | FUTURE->IMPLEMENTING, IMPLEMENTING->ACTIVE, ACTIVE->SUPERSEDED, *->HISTORICAL |
| Narrative | NarrativeStatus (DRAFT, ACTIVE, COMPLETED, HISTORICAL) | DRAFT->ACTIVE, ACTIVE->COMPLETED, *->HISTORICAL |
| Investigation | InvestigationStatus (ONGOING, SOLVED, NOTED, DEFERRED) | ONGOING->SOLVED, ONGOING->NOTED, ONGOING->DEFERRED |
| Subsystem | SubsystemStatus (DISCOVERING, DOCUMENTED, REFACTORING, STABLE, DEPRECATED) | DISCOVERING->DOCUMENTED->REFACTORING->STABLE, *->DEPRECATED |
| WorkUnit (Orchestrator) | WorkUnitStatus (READY, RUNNING, BLOCKED, NEEDS_ATTENTION, DONE) | READY->RUNNING, RUNNING->DONE/BLOCKED/NEEDS_ATTENTION, BLOCKED->READY |
| FrictionEntry | FrictionStatus (OPEN, ADDRESSED, RESOLVED) | Derived, not stored - based on chunk linkage |

**Entity Relationship Sketch:**

```
Narrative 1--* Chunk (proposed_chunks, contributing_chunks)
Investigation 1--* Chunk (proposed_chunks)
Subsystem 1--* Chunk (chunks[].chunk_id relationship)
Chunk *--1 Investigation (investigation field)
Chunk *--1 Narrative (narrative field)
Chunk *--* Subsystem (subsystems[] relationship)
Chunk *--* FrictionEntry (friction_entries[] field)
WorkUnit 1--1 Chunk (chunk field)
```

**Prompt Effectiveness**: HIGH - The prompt correctly guided discovery of status enums and transitions. Chunk success criteria indeed reveal state transitions (e.g., "chunk can be PLANNED -> IMPLEMENTING -> ACTIVE").

---

## Phase 4: Business Rule Extraction

### Prompt Execution Summary

The prompt asks to extract invariants from chunk success criteria and code.

### Preliminary Findings

**Rules Discovered from Chunk Success Criteria:**

| Rule | Source | Enforcement |
|------|--------|-------------|
| Only one IMPLEMENTING chunk allowed per repo | chunk_create_guard GOAL.md | src/chunks.py#Chunks::create_chunk |
| Status can only transition forward (with exceptions) | valid_transitions GOAL.md | VALID_*_TRANSITIONS dicts in models.py |
| Symbolic references must use file#symbol format | symbolic_code_refs GOAL.md | SymbolicReference Pydantic validator |
| Chunk names must be underscore-separated identifiers | implement_chunk_start GOAL.md | src/validation.py#validate_identifier |
| Worktree must be clean before cluster rename | cluster_rename GOAL.md | src/cluster_rename.py#is_git_clean |
| Orchestrator agents cannot escape worktree sandbox | orch_sandbox_enforcement GOAL.md | src/orchestrator/agent.py |
| ACTIVE status required before completion commit | orch_verify_active GOAL.md | src/orchestrator/scheduler.py#_advance_phase |
| External references must pin specific commits | ve_sync_command GOAL.md | src/sync.py |

**Conflict Detection:**
- No contradictory rules found between chunks
- Some rules evolved (e.g., line-number refs -> symbolic refs, but coderef_format_prompting marked HISTORICAL)

**Prompt Effectiveness**: HIGH - Success criteria are indeed rich sources of invariants. The "what must always be true" framing works well.

---

## Phase 5: Domain Boundary Refinement

### Prompt Execution Summary

The prompt asks to reconcile chunk clusters with business analysis for final subsystem boundaries.

### Preliminary Findings

**Proposed Subsystem Structure (refined from Phase 2):**

| Subsystem | Business Intent | Core Entities | Key Invariants | Contributing Chunks |
|-----------|----------------|---------------|----------------|---------------------|
| workflow_artifacts | Consistent domain model for all artifact types | Chunk, Narrative, Investigation, Subsystem, FrictionEntry | Forward-only status transitions, causal ordering DAG, symbolic references | 40+ chunks |
| orchestrator | Parallel agent management | WorkUnit, AgentResult, Conflict | Single daemon per project, worktree isolation, attention queue priority | 21 orch_* chunks |
| cross_repo_tasks | Cross-repository coordination | TaskConfig, ExternalArtifactRef | Valid repo references, pinned commits | 10+ task/external chunks |
| template_system | Template rendering | RenderResult | Source templates are truth, drift prevention | 8 template chunks |

**Chunk Disposition (sample):**

| Chunk | Disposition | Target Subsystem |
|-------|-------------|------------------|
| chunk_frontmatter_model | absorbed | workflow_artifacts |
| orch_foundation | absorbed | orchestrator |
| task_init | absorbed | cross_repo_tasks |
| template_system_consolidation | absorbed | template_system |
| cluster_rename | supporting pattern | workflow_artifacts (documentation) |
| symbolic_code_refs | absorbed | workflow_artifacts |

**Prompt Effectiveness**: MODERATE - The reconciliation step is useful but requires more context about "right granularity" criteria. The prompt could benefit from examples.

---

## Phase 6: Infrastructure Annotation

### Prompt Execution Summary

The prompt asks to identify cross-cutting infrastructure patterns.

### Preliminary Findings

**Infrastructure Patterns Identified:**

| Pattern | Used By | Consistency | Recommendation |
|---------|---------|-------------|----------------|
| Pydantic Frontmatter Models | All artifacts | Consistent | Supporting pattern |
| YAML Parsing (ruamel.yaml) | All artifacts | Consistent | Supporting pattern |
| Click CLI Structure | All commands | Consistent | Supporting pattern |
| Jinja2 Template Rendering | All templates | Consistent | Subsystem (template_system) |
| SQLite State Persistence | Orchestrator only | N/A (single use) | Part of orchestrator subsystem |
| WebSocket Broadcasting | Orchestrator only | N/A (single use) | Part of orchestrator subsystem |

**Infrastructure Chunks:**
| Chunk | Pattern | Recommendation |
|-------|---------|----------------|
| git_local_utilities | Git helpers | Supporting pattern in cross_repo_tasks |
| remove_trivial_tests | Test hygiene | Not a pattern, one-time cleanup |

**Prompt Effectiveness**: HIGH - The distinction between "infrastructure" and "domain" is useful. The "only promote to subsystem if complex" guidance prevented over-promotion.

---

## Phase 7: Backreference Planning

### Prompt Execution Summary

The prompt asks to plan migration from chunk backreferences to subsystem backreferences.

### Preliminary Findings

**Current State Analysis:**

Files with `# Chunk:` backreferences in src/: 50+ locations found (see grep results)

**Migration Sample:**

| File | Current Refs | Action | New Ref |
|------|--------------|--------|---------|
| src/orchestrator/scheduler.py | # Chunk: orch_scheduling, orch_verify_active, orch_activate_on_inject, ... (12 refs) | consolidate | # Subsystem: orchestrator |
| src/orchestrator/state.py | # Chunk: orch_foundation, orch_verify_active, orch_attention_reason, ... (8 refs) | consolidate | # Subsystem: orchestrator |
| src/validation.py | # Chunk: implement_chunk_start (2 refs) | consolidate | # Subsystem: workflow_artifacts |
| src/models.py | (no chunk refs currently) | add | # Subsystem: workflow_artifacts |

**Granularity Decisions:**
- Most orchestrator files: MODULE level (entire file serves orchestrator)
- src/ve.py: FUNCTION level (different command groups serve different subsystems)

**Prompt Effectiveness**: MODERATE - The migration rules are clear but the example output format could be more detailed. Adding "files with multiple chunk references" statistics would help prioritization.

---

## Phase 8: Chunk Synthesis & Archive

### Prompt Execution Summary

The prompt asks to synthesize subsystem OVERVIEW.md content from contributing chunk GOAL.md files.

### Preliminary Findings

**Synthesis Sample: orchestrator subsystem**

From contributing chunks (orch_foundation, orch_scheduling, orch_attention_queue, orch_conflict_oracle, ...):

**Synthesized Intent:**
> Enable parallel chunk work across multiple AI agents by providing an "operating system scheduler" where worktrees are isolated processes, agents are stateless CPUs, and the system routes operator attention to maximize throughput.

**Synthesized Invariants (from success criteria):**
- Only one daemon instance allowed per project
- Database stored in `.ve/orchestrator.db`
- WorkUnit tracks: chunk directory, phase, status
- Each phase is a fresh agent context (session-per-phase)
- Worktrees isolated at `.ve/chunks/<chunk>/worktree/`

**Synthesized Scope:**
- IN: Daemon lifecycle, work unit scheduling, attention queue, conflict detection, worktree isolation
- OUT: Semantic merge resolution, review gates (mentioned as out of scope in chunks)

**Chunk Provenance:**
- orch_foundation: Daemon lifecycle, SQLite state
- orch_scheduling: Worktree management, agent spawning
- orch_attention_queue: Operator attention routing
- (etc.)

**Archive Strategy Recommendation:** Option A (delete) - Git history preserves archaeology, subsystem OVERVIEW.md captures all value.

**Prompt Effectiveness**: HIGH - The synthesis guidance is clear and produces coherent output. The "problem statement -> Intent, success criteria -> Invariants" mapping works well.

---

## Overall Prompt Effectiveness Summary

| Phase | Effectiveness | Notes |
|-------|---------------|-------|
| 1 | HIGH | Clear output format, good for automation |
| 2 | HIGH | Business capability framing is valuable |
| 3 | HIGH | Entity discovery from chunks works well |
| 4 | HIGH | Success criteria -> invariants is reliable |
| 5 | MODERATE | Needs more granularity guidance |
| 6 | HIGH | Infrastructure distinction is useful |
| 7 | MODERATE | Output format could be more detailed |
| 8 | HIGH | Synthesis guidance produces coherent output |

**Key Observations:**
1. Prompts produce useful, structured output
2. Phases build naturally on each other
3. Phase 1 output (chunk inventory) is foundational for all subsequent phases
4. Some prompts assume more context than provided (e.g., Phase 5's "right granularity")
5. The chunk-to-subsystem mapping is the core value proposition
