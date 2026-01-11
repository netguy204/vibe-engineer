# Parallel Agent Orchestration Design

**Date:** 2026-01-11
**Status:** Draft
**Investigation:** docs/investigations/parallel_agent_orchestration

## Overview

An orchestration system for managing parallel agent work on VE chunks. The core insight is that this is an **operating system problem**: worktrees are processes, agents are CPUs, and the orchestrator is a scheduler that maximizes throughput while managing resource conflicts.

## Mental Model

**The Orchestrator as Attention Router**

The orchestrator's job is not to "run agents" - agents run themselves. Its job is to:

1. **Route operator attention** to where it creates the most throughput
2. **Maintain continuity** across operator interruptions
3. **Enforce correct sequencing** via fuzzy conflict detection

The primary interface is an **attention queue** - a prioritized list of things needing operator input. Priority is determined by **downstream impact**: unblocking something that unblocks 4 other chunks ranks higher than unblocking a leaf node.

## Architecture

```
┌──────────────────────────────────────────────┐
│           Orchestrator Daemon                │
│  ┌───────────────┐  ┌─────────────────────┐  │
│  │ Scheduler     │  │ State Store         │  │
│  │               │  │ (SQLite)            │  │
│  └───────────────┘  └─────────────────────┘  │
│  ┌───────────────┐  ┌─────────────────────┐  │
│  │ Conflict      │  │ Worktree            │  │
│  │ Oracle        │  │ Manager             │  │
│  └───────────────┘  └─────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │ HTTP/WebSocket API                     │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
        ▲              ▲              ▲
        │              │              │
   ┌────┴────┐   ┌─────┴─────┐   ┌────┴────┐
   │   CLI   │   │ Dashboard │   │ Future  │
   │ ve orch │   │  (Web)    │   │ Slack,  │
   │         │   │           │   │ Phone   │
   └─────────┘   └───────────┘   └─────────┘
```

### Components

**Orchestrator Daemon (`ve-orchestrator`)**
- Long-running process, survives reboots
- SQLite database for durable state
- Spawns and shepherds agents through chunk phases
- Exposes HTTP + WebSocket API
- Auto-launches ready work when dependencies clear

**CLI Client (`ve orch`)**
- Stateless, talks to daemon via HTTP
- Commands for status, queue management, intervention
- JSON output mode for scripting

**Web Dashboard**
- Connects via WebSocket for live updates
- Primary view: attention queue + process grid
- Click-to-expand: agent context, chunk goal, pending question

### Per-Project Isolation

**Requirement:** Multiple orchestrator daemons can run simultaneously on one machine, each managing a different project.

**Implementation:** Each daemon is scoped to a project directory and stores all state under `.ve/`:

```
project-a/
├── .ve/
│   ├── orchestrator.pid     # Daemon process ID
│   ├── orchestrator.sock    # Unix socket for IPC
│   ├── orchestrator.db      # SQLite state database
│   └── orchestrator.log     # Daemon logs
└── docs/chunks/...

project-b/
├── .ve/
│   ├── orchestrator.pid
│   ├── orchestrator.sock
│   ├── orchestrator.db
│   └── orchestrator.log
└── docs/chunks/...
```

**CLI discovery:** The `--project-dir` option (defaulting to current directory) determines which daemon to communicate with. The CLI reads `.ve/orchestrator.sock` from the project directory to find the right socket.

**Benefits:**
- No port conflicts between daemons
- No global registry or coordination required
- State is naturally co-located with the project it manages
- Easy cleanup: delete `.ve/` to remove all orchestrator state

## The OS Analogy

| OS Concept | Orchestrator Concept |
|------------|---------------------|
| **Process** | Worktree + Chunk (own address space, lifecycle, state) |
| **CPU** | Agent (stateless executor, runs current phase) |
| **Scheduler** | Orchestrator daemon (assigns ready processes to CPUs) |
| **Instruction** | Phase (goal → plan → implement → complete) |
| **Process state** | READY, RUNNING, BLOCKED, WAITING_IO |
| **Resource conflict** | Symbol overlap (fuzzy, judgment-based) |
| **Interrupt** | Attention item (process needs operator intervention) |
| **Context switch** | Agent completes phase, worktree returns to ready queue |

### Key Insight: Stateless Agents

Agents don't persist across phases. Each phase is:
1. Fresh agent context (cleared)
2. Agent receives: chunk directory + phase-specific prompt
3. Agent completes phase
4. Orchestrator evaluates: conflict? proceed? wait?

Agent "slots" control throughput/cost, not context. The orchestrator is stateful; agents are ephemeral workers.

## Work Unit Model

The orchestrator manages **work units**, not agent sessions:

```
WorkUnit {
  chunk: string           // chunk directory (the "PID")
  phase: GOAL | PLAN | IMPLEMENT | COMPLETE
  status: READY | RUNNING | BLOCKED | NEEDS_ATTENTION | DONE
  blocked_by: string[]    // chunks that must complete first
  worktree: string        // git worktree path
}
```

### Chunk Lifecycle

```
PROPOSED ─→ GOAL_DRAFTING ─→ GOAL_REVIEW ─→ PLANNING ─→ [PLAN_REVIEW?] ─→ IMPLEMENTING ─→ IMPL_REVIEW ─→ COMPLETING ─→ DONE
```

At each transition:
- Conflict analysis runs with newly available information
- If clear → advance to next phase, status = READY
- If conflict detected → status = BLOCKED
- If attention needed → status = NEEDS_ATTENTION, queue item

### Dispatch Loop

```
every tick:
  for unit in work_units where status == READY:
    if agent_slots_available():
      spawn_fresh_agent(unit.chunk, unit.phase)
      unit.status = RUNNING

  for unit in work_units where status == BLOCKED:
    re_evaluate_conflicts(unit)
    if no_conflicts():
      unit.status = READY
```

## Conflict Oracle

### Progressive Analysis

| Stage | Information Available | Analysis Method |
|-------|----------------------|-----------------|
| PROPOSED | Prompt text only | LLM semantic comparison of prompts |
| GOAL exists | GOAL.md content | LLM comparison of intent + scope |
| PLAN exists | PLAN.md with locations | File overlap + LLM symbol prediction |
| COMPLETED | code_references | Exact symbol overlap (ground truth) |

### Fuzzy Judgment

Conflict detection is **not hard locking** - it's a judgment call:

```python
def should_serialize(chunk_a, chunk_b) -> Verdict:
    confidence = analyze_overlap(chunk_a, chunk_b)

    if confidence.no_overlap > 0.8:
        return INDEPENDENT      # Parallelize freely
    elif confidence.overlap > 0.8:
        return SERIALIZE        # Must sequence
    else:
        return ASK_OPERATOR     # Queue attention item
```

When uncertain, escalate to operator rather than guess wrong.

### Symbol-Level Granularity

File overlap is too coarse (many chunks touch `src/ve.py`). What matters is **symbol overlap**:

- `src/ve.py#suggest_prefix_cmd` vs `src/ve.py#cluster_rename_cmd` → Independent
- Both modifying `src/ve.py#validate_chunk` → Conflict

For planned chunks, predict symbols from PLAN.md. For completed chunks, use `code_references` as ground truth.

## Attention Queue

### What Goes in the Queue

- **Question**: Agent asked a clarifying question
- **Decision**: Agent presenting options, needs a choice
- **Review**: Agent completed a phase, needs approval
- **Stuck**: Agent not progressing (timeout, loop, error)
- **Conflict**: Uncertain semantic overlap, operator decides

### Priority Scoring

Items ranked by downstream impact:

```
priority = blocked_chunk_count + (depth_in_graph * weight)
```

Tie-breaker: time in queue (older items surface first).

### Item Display

```
[1] QUESTION  auth_refactor  blocks:4  12m ago
    "JWT or session tokens for auth layer?"

    Context: Refactoring authentication to support SSO
    Phase: PLANNING
    [a]nswer  [g]oal  [t]ranscript  [s]kip
```

Each item shows:
- Type and chunk identifier
- Downstream impact (blocks:N)
- Time waiting
- The question/decision with context summary
- Available actions

## Review Gates

### Goal Review (Always Required)

The goal is the contract. Surface:
- Chunk name and initial status
- Key assumptions extracted from goal
- Scope boundaries: in-scope vs out-of-scope

### Plan Review (Conditional)

Require review when:
- Symbol overlap detected with other active work
- Template/meta file changes (CLAUDE.md, command templates)
- New CLI commands (prompt: "permanent or one-time?")

Auto-advance when:
- Isolated file changes, no template touches
- Similar to previously-approved patterns

### Implementation Review

Surface for review:
- Files touched vs files with semantic changes
- Template or guidance file modifications
- Consistency check with similar commands
- Precondition: tests must pass

## Dashboard View

```
┌─────────────────────────────────────────────────────────────────────┐
│  VE Orchestrator                                    3 agents active │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ATTENTION (2)                                                      │
│  ──────────────────────────────────────────────────────────────────│
│  [1] QUESTION  auth_refactor  blocks:4  12m ago                    │
│      "JWT or session tokens for auth layer?"                        │
│      ► Refactoring authentication to support SSO                    │
│                                                                     │
│  [2] CONFLICT  user_endpoints ↔ auth_middleware  confidence:0.6    │
│      "These may overlap - parallelize anyway?"                      │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  RUNNING (3)                              READY (2)   BLOCKED (1)  │
│  ──────────────────────────────────────────────────────────────────│
│  ● api_validation    IMPLEMENTING  4m     ○ error_handling         │
│  ● cache_layer       PLANNING      2m     ○ logging_cleanup        │
│  ● cli_export        GOAL          <1m                              │
│                                           ◌ user_endpoints          │
│                                             └─ waiting: auth_refactor
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  [a]nswer  [v]iew goal  [t]ranscript  [i]nterrupt  [r]efresh       │
└─────────────────────────────────────────────────────────────────────┘
```

**Information Hierarchy:**
1. Attention count (how many things need me?)
2. Top attention item expanded with context
3. Process overview (running/ready/blocked)
4. Blocked reasons visible

## CLI Commands

### Daemon Lifecycle
```bash
ve orch start                    # Start orchestrator daemon
ve orch stop                     # Stop daemon gracefully
ve orch status                   # Quick summary
```

### Attention Queue
```bash
ve orch queue                    # List attention items
ve orch answer <chunk> "response"   # Respond to question
ve orch resolve <chunk> parallelize # Resolve conflict check
ve orch skip <chunk>             # Defer attention item
```

### Work Management
```bash
ve orch inject <chunk>           # Add chunk to work pool
ve orch inject --proposed        # Import all proposed chunks
ve orch prioritize <chunk>       # Bump priority
ve orch block <chunk>            # Manual hold
ve orch unblock <chunk>          # Release hold
```

### Process Inspection
```bash
ve orch ps                       # List all processes
ve orch inspect <chunk>          # Show details
ve orch transcript <chunk>       # Dump agent transcript
ve orch logs <chunk>             # Orchestrator events
```

### Intervention
```bash
ve orch interrupt <chunk> "msg"  # Inject guidance
ve orch kill <chunk>             # Terminate, return to READY
ve orch retry <chunk>            # Re-run current phase
```

### Configuration
```bash
ve orch config --max-agents=4       # Throughput limit
ve orch config --plan-review=risky  # When to require review
```

All commands support `--json` for scripting.

## Open Questions

1. **Agent SDK vs Claude Code**: Should agents be Claude Code sessions or Agent SDK processes? Agent SDK offers more programmatic control.

2. **Worktree lifecycle**: When to create/destroy worktrees? Per-chunk? Pooled and reused?

3. **Merge strategy**: When a chunk completes, merge immediately or batch merges?

4. **Dashboard technology**: TUI (terminal) vs web? Web offers richer interaction but adds deployment complexity.

5. **Learning from outcomes**: Can the oracle improve over time by tracking which parallel work merged cleanly vs painfully?

## Implementation Phases

### Phase 1: Foundation
- Daemon skeleton with SQLite state
- Basic work unit model
- `ve orch start/stop/status/ps`

### Phase 2: Scheduling
- Worktree manager
- Agent spawning (single phase execution)
- `ve orch inject`, ready queue

### Phase 3: Attention Queue
- Question/decision capture from agents
- Priority scoring
- `ve orch queue/answer`

### Phase 4: Conflict Oracle
- Goal-level semantic comparison
- Plan-level file/symbol analysis
- `ve orch resolve`

### Phase 5: Dashboard
- Web UI with WebSocket updates
- Attention queue view
- Process grid

### Phase 6: Polish
- Stuckness detection
- Intervention commands
- Configuration options
