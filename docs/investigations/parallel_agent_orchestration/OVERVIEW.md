---
status: SOLVED
trigger: "Difficulty managing parallel agent workflows across multiple terminals and Conductor"
proposed_chunks:
  - prompt: "Orchestrator foundation: daemon skeleton with SQLite state, basic work unit model, ve orch start/stop/status/ps commands"
    chunk_directory: orch_foundation
  - prompt: "Orchestrator scheduling: worktree manager, agent spawning for single phase execution, ve orch inject and ready queue"
    chunk_directory: null
  - prompt: "Orchestrator attention queue: question/decision capture from agents, priority scoring by downstream impact, ve orch queue/answer commands"
    chunk_directory: null
  - prompt: "Conflict oracle: goal-level semantic comparison, plan-level file/symbol analysis, ve orch resolve command"
    chunk_directory: null
  - prompt: "Orchestrator dashboard: web UI with WebSocket updates, attention queue view, process grid"
    chunk_directory: null
created_after: ["task_agent_experience", "xr_vibe_integration"]
---

## Trigger

Working across multiple terminals with agents (each pursuing different chunks) and using Conductor.build revealed cognitive overhead that shouldn't exist:

1. **Lost attention signals**: Agents waiting for operator attention without the operator being aware they needed it
2. **Forgotten lifecycle steps**: Skipping chunk steps (plan → implement → complete) due to manual orchestration
3. **Insufficient question focus**: Agent questions not getting proper attention amidst parallel work
4. **Semantic-blind merging**: Conductor merges analyze only conflicting code, not the semantic intent documented in chunk GOALs

Conductor provides workspace isolation via git worktrees and parallel agent execution, but lacks awareness of the Vibe Engineering workflow - chunks, proposed chunks, goals, and the semantic meaning behind changes.

## Success Criteria

1. **Design document produced**: A concrete design for an orchestration feature that addresses the trigger pain points
2. **Independence analysis validated**: A method (preferably automated) to determine which proposed chunks can be safely parallelized
3. **Historical evidence examined**: Analysis of chunks with multiple tips in this repository to understand where parallel assumptions failed

## Testable Hypotheses

### H1: Chunk independence can be mechanically determined from frontmatter and code references

- **Rationale**: Chunks declare `created_after` relationships and may reference shared files. If two chunks don't share code references and have no causal relationship, they should be safe to parallelize.
- **Test**: Build a dependency graph from chunk frontmatter and code_references, compare against historical merge conflicts
- **Status**: PARTIALLY VERIFIED

**Finding:** Independence detection requires TWO inputs:
1. `created_after` DAG (from GOAL.md frontmatter)
2. File overlap (from PLAN.md `Location:` lines or GOAL.md `code_paths`)

The recent merge (3cdbf07) demonstrates this: three chunks declared no dependency on each other via `created_after` but all modified `src/ve.py`, causing merge conflicts. File overlap detection would have flagged this.

### H2: Chunks with multiple git tips indicate failed independence assumptions

- **Rationale**: When the operator worked chunks in parallel that later conflicted, the git history shows multiple tips that required manual reconciliation
- **Test**: Examine chunks in this repo with multiple tips, document what made them not actually independent
- **Status**: VERIFIED

**Evidence:** Merge commit `3cdbf07` shows three parallel branches (`similarity_prefix_suggest`, `cluster_rename`, `task_list_proposed`) that were merged. All three touched `src/ve.py` causing file-level conflicts. The assumption that these were independent (based on their semantic separation) was incorrect - they shared a "funnel file" dependency.

### H3: Semantic-aware merge conflict resolution improves merge success rate

- **Rationale**: Conductor's code-only merge analysis misses chunk semantic intent. Providing chunk GOALs to the merge resolution agent should produce better merges.
- **Test**: Would require a prototype or simulation - compare merge outcomes with and without chunk context
- **Status**: UNTESTED

### H4: A centralized attention queue reduces operator cognitive load

- **Rationale**: The pain of "agents waiting without awareness" suggests a unified queue of agent questions would help
- **Test**: Design mockup + user feedback, or prototype with simple attention aggregation
- **Status**: UNTESTED

## Exploration Log

### 2026-01-11: Investigation created, Conductor analysis

Reviewed Conductor.build - a Mac app for parallel agent orchestration:
- Uses git worktrees for workspace isolation
- Supports Claude Code and Codex agents
- Provides visual dashboard for agent progress
- Has merge/review capabilities

**Gap analysis vs VE workflow needs:**
- No awareness of chunk lifecycle (plan → implement → complete)
- No access to proposed_chunks for parallelization suggestions
- Merge conflict resolution is code-only, no semantic context from chunk GOALs
- No attention queue for agent questions

**Key insight from operator:** Chunks with multiple tips in git history represent cases where parallelization assumptions failed. This is mechanically discoverable - we can analyze the repo to find these cases and understand what made them not actually independent.

### 2026-01-11: Historical parallel work analysis - the recent merge

Examined merge commit `3cdbf07` which merged three parallel chunks:
1. `similarity_prefix_suggest` (cluster-rename + TF-IDF prefix suggestion)
2. `cluster_rename` (batch prefix renaming)
3. `task_list_proposed` (task-aware proposed chunk listing)

**Independence assessment via frontmatter:** All three have identical `created_after`:
```yaml
created_after:
- artifact_promote
- project_qualified_refs
- task_init_scaffolding
- task_status_command
- task_config_local_paths
```
No declared dependency on each other - frontmatter says "these can parallelize."

**Independence assessment via code_paths:** CONFLICT DETECTED

| Chunk | Files Modified |
|-------|----------------|
| similarity_prefix_suggest | src/chunks.py, **src/ve.py**, pyproject.toml, tests/..., .claude/commands/chunk-plan.md |
| cluster_rename | src/cluster_rename.py, **src/ve.py**, src/templates/..., tests/... |
| task_list_proposed | src/task_utils.py, **src/ve.py**, tests/... |

**All three modify `src/ve.py`** - the CLI entry point. This is the archetypal "funnel file" problem where many features add CLI commands to the same file.

**Conclusion for H1:** `created_after` alone is insufficient for independence detection. Must also analyze file overlap. Proposed algorithm:
1. Parse `created_after` from all pending chunks to build a dependency DAG
2. Parse file references to detect overlap - SOURCE DEPENDS ON CHUNK STATUS:
   - COMPLETED/ACTIVE chunks: use `code_paths` from GOAL.md frontmatter
   - IMPLEMENTING chunks: parse `Location:` lines from PLAN.md
   - FUTURE chunks: no file info available (can only use created_after)
3. Two chunks are independent iff: (a) neither depends on the other in the DAG, AND (b) their files don't intersect

### 2026-01-11: UX Design Brainstorming Session

Conducted extensive design session exploring:
- Interaction posture (deep focus vs interrupted recovery)
- Terminal setup and workflow patterns
- Dashboard vs CLI tradeoffs

**Key discovery: OS Analogy**
- Worktree = Process (own address space, lifecycle)
- Agent = CPU (stateless executor)
- Orchestrator = Scheduler
- Phase = Instruction
- Symbol conflict = Resource lock (fuzzy, judgment-based)

This reframe clarified the architecture significantly. Agents are ephemeral workers that execute one phase then return the worktree to the ready queue. The orchestrator maintains all state.

**Design document produced:** `docs/investigations/parallel_agent_orchestration/design.md`

### 2026-01-11: PLAN.md contains file locations

Discovered that PLAN.md files explicitly annotate file locations with `Location:` lines for each step. Example from cluster_rename PLAN.md:
```
Location: src/cluster_rename.py
Location: src/ve.py
Location: tests/test_cluster_rename.py
```

This means file overlap detection is possible at **planning time** (before implementation) by parsing PLAN.md files. This enables a workflow:

1. Operator creates multiple chunks via `/chunk-create`
2. Operator runs `/chunk-plan` on each chunk
3. **NEW**: System parses all PLAN.md files and detects file overlap
4. System warns: "Chunks A and B both modify `src/ve.py` - cannot parallelize safely"
5. Operator sequences chunks appropriately, or decides to parallelize and handle merge conflicts

**Key insight:** The planning phase is the natural checkpoint for independence verification. Post-planning, pre-implementation is when we have maximum information with minimum investment.

## Findings

### Verified Findings

1. **Chunk independence requires file overlap analysis, not just causal ordering**
   - Evidence: Merge 3cdbf07 shows three chunks with identical `created_after` (no mutual dependencies) that all modified `src/ve.py`
   - The `created_after` DAG alone is insufficient for parallelization decisions

2. **File overlap is detectable at planning time via PLAN.md Location: annotations**
   - Evidence: PLAN.md files include explicit `Location:` lines per step
   - This enables pre-implementation conflict detection, avoiding wasted parallel work

3. **"Funnel files" are the primary source of false independence assumptions**
   - Evidence: `src/ve.py` (CLI entry point) is modified by nearly every feature chunk
   - Other common funnel files: main config files, central routing, index files

4. **Multiple daemons must coexist on one machine, scoped by project**
   - Requirement: An operator may work on multiple projects simultaneously, each with its own orchestrator daemon
   - Solution: Each daemon uses a Unix socket stored in the project's `.ve/` directory (`.ve/orchestrator.sock`)
   - CLI discovery: The `--project-dir` option (defaulting to `.`) determines which socket to connect to
   - Implemented in: `orch_foundation` chunk - daemon stores PID, socket, log, and database all under `.ve/`

### Hypotheses/Opinions

1. **Planning phase is the optimal checkpoint for independence verification**
   - Post-planning has maximum information (file locations known) with minimum investment (no implementation done yet)
   - Not yet validated in a tool workflow

2. **Semantic context during merge resolution would reduce conflict errors**
   - Providing chunk GOALs to the merge agent should improve merge quality
   - Not yet tested - would require prototype or A/B comparison

## Proposed Chunks

Implementation follows the phased approach from the design document:

1. **Orchestrator Foundation**: Daemon skeleton with SQLite state, basic work unit model, `ve orch start/stop/status/ps` commands
   - Priority: High (everything else depends on this)
   - Dependencies: None
   - Notes: Establishes the core daemon architecture and state persistence

2. **Orchestrator Scheduling**: Worktree manager, agent spawning for single phase execution, `ve orch inject` and ready queue
   - Priority: High
   - Dependencies: Foundation chunk
   - Notes: This is where the OS analogy comes to life - worktrees as processes, agents as CPUs

3. **Orchestrator Attention Queue**: Question/decision capture from agents, priority scoring by downstream impact, `ve orch queue/answer` commands
   - Priority: High
   - Dependencies: Scheduling chunk
   - Notes: The primary UX surface - where operator attention gets routed

4. **Conflict Oracle**: Goal-level semantic comparison, plan-level file/symbol analysis, `ve orch resolve` command
   - Priority: Medium
   - Dependencies: Attention queue chunk
   - Notes: Progressive fuzzy analysis - more precise as chunks advance through lifecycle

5. **Orchestrator Dashboard**: Web UI with WebSocket updates, attention queue view, process grid
   - Priority: Medium
   - Dependencies: Attention queue chunk
   - Notes: The "at a glance" interface for rapid re-orientation after interruptions

## Resolution Rationale

**Status: SOLVED**

The investigation achieved its primary success criterion: a design document for the orchestration feature.

**Key findings:**
1. The OS analogy (worktree=process, agent=CPU, orchestrator=scheduler) provides a clean mental model
2. Conflict detection must be progressive and fuzzy - more precise as chunks move through lifecycle
3. Agents should be stateless; the orchestrator maintains all durable state
4. The attention queue prioritized by downstream impact is the primary UX

**Design document:** `docs/investigations/parallel_agent_orchestration/design.md`

**Next steps:** The proposed chunks in this investigation can be created to begin implementation. The design document includes phased implementation guidance.