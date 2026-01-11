<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk extends the orchestrator foundation (orch_foundation) with scheduling capabilities. The implementation builds on the existing daemon, state store, HTTP API, and CLI patterns.

**Key technical choices:**

1. **Claude Agent SDK for agent execution**: Use `claude-agent-sdk` Python package with session-per-phase semantics. Each phase (GOAL/PLAN/IMPLEMENT/COMPLETE) is a fresh `query()` call. Sessions suspend when `AskUserQuestion` is called, resume when operator answers.

2. **Git worktrees for isolation**: Each work unit gets its own worktree at `.ve/chunks/<chunk>/worktree/` on a dedicated branch `orch/<chunk>`. Worktrees are created when a work unit starts running and removed when complete.

3. **Async dispatch loop in daemon**: The daemon runs an async background task that periodically checks for READY work units and spawns agents up to `max_agents` slots. Agent execution is async, allowing multiple agents to run concurrently.

4. **Transcript capture via message streaming**: The Agent SDK yields messages as an async generator. We capture all messages to `.ve/chunks/<chunk>/log/<phase>.txt` for debugging and audit.

**Patterns from orch_foundation to follow:**
- Pydantic models for data structures (extend `WorkUnit`, add `Config`)
- SQLite state persistence (add config table, extend work_units with priority)
- Starlette HTTP API (add new endpoints)
- Click CLI commands (add `inject`, `queue`, `prioritize`, `config`)
- Unix socket for daemon communication

**Testing approach:**
- Unit tests for worktree manager (mock git operations)
- Unit tests for agent spawner (mock claude-agent-sdk)
- Integration tests for dispatch loop (in-memory state, mock agents)
- CLI tests for new commands (real daemon, mock agent execution)

## Subsystem Considerations

No existing subsystems are relevant to this chunk. The orchestrator is a new major component that may become a subsystem itself once stable.

## Sequence

### Step 1: Add claude-agent-sdk dependency

Add `claude-agent-sdk` to pyproject.toml dependencies. This is the Claude Agent SDK Python package that provides the `query()` function for running agents.

Location: pyproject.toml

### Step 2: Extend models with scheduling fields

Add new fields and models to support scheduling:

1. Add `priority` field to `WorkUnit` (integer, default 0, higher = more urgent)
2. Add `session_id` field to `WorkUnit` (optional string, for suspended sessions)
3. Add `OrchestratorConfig` model with:
   - `max_agents: int` (default: 2)
   - `dispatch_interval_seconds: float` (default: 1.0)

Location: src/orchestrator/models.py

### Step 3: Add config table and migration

Create SQLite migration (version 2) that:
1. Adds `priority` column to `work_units` table (INTEGER DEFAULT 0)
2. Adds `session_id` column to `work_units` table (TEXT NULL)
3. Creates `config` table with key-value pairs for daemon settings

Update StateStore with:
- `get_config(key)` / `set_config(key, value)` methods
- `get_ready_queue()` method returning work units ordered by priority DESC, created_at ASC
- `_migrate_v2()` migration function

Location: src/orchestrator/state.py

### Step 4: Create worktree manager module

Create `src/orchestrator/worktree.py` with:

```python
class WorktreeManager:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    def create_worktree(self, chunk: str) -> Path:
        """Create git worktree for chunk at .ve/chunks/<chunk>/worktree/"""
        # 1. Create branch orch/<chunk> from HEAD
        # 2. git worktree add .ve/chunks/<chunk>/worktree orch/<chunk>
        # 3. Return worktree path

    def remove_worktree(self, chunk: str) -> None:
        """Remove git worktree and optionally the branch"""
        # 1. git worktree remove .ve/chunks/<chunk>/worktree
        # 2. Optionally: git branch -d orch/<chunk>

    def get_worktree_path(self, chunk: str) -> Path:
        """Return the worktree path for a chunk"""

    def worktree_exists(self, chunk: str) -> bool:
        """Check if worktree already exists"""
```

Use `subprocess.run()` to execute git commands. Handle errors gracefully (branch already exists, worktree already exists, etc.).

Location: src/orchestrator/worktree.py

### Step 5: Create agent runner module

Create `src/orchestrator/agent.py` with:

```python
class AgentRunner:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    async def run_phase(
        self,
        chunk: str,
        phase: WorkUnitPhase,
        worktree_path: Path,
        resume_session_id: Optional[str] = None,
    ) -> AgentResult:
        """Run a single phase for a chunk using Claude Agent SDK.

        Returns AgentResult with:
        - completed: bool (phase finished successfully)
        - suspended: bool (agent called AskUserQuestion)
        - session_id: str (for resuming if suspended)
        - question: Optional[dict] (if suspended, the question to queue)
        - error: Optional[str] (if failed)
        """

    def _get_phase_skill(self, phase: WorkUnitPhase) -> str:
        """Return the slash command to invoke for a given phase"""
        # GOAL -> /chunk-create, PLAN -> /chunk-plan, etc.

    async def _capture_transcript(
        self,
        chunk: str,
        phase: WorkUnitPhase,
        messages: AsyncIterator,
    ) -> None:
        """Stream messages to .ve/chunks/<chunk>/log/<phase>.txt"""
```

The `run_phase` method:
1. Creates fresh `query()` call with phase skill as prompt (e.g., "/chunk-plan")
2. Sets working directory to worktree_path
3. Configures `PreToolUse` hook to intercept `AskUserQuestion`
4. Iterates async generator, capturing messages
5. Detects suspension (AskUserQuestion intercepted) vs completion

Location: src/orchestrator/agent.py

### Step 6: Create scheduler module with dispatch loop

Create `src/orchestrator/scheduler.py` with:

```python
class Scheduler:
    def __init__(
        self,
        store: StateStore,
        worktree_manager: WorktreeManager,
        agent_runner: AgentRunner,
        config: OrchestratorConfig,
    ):
        self.store = store
        self.worktree_manager = worktree_manager
        self.agent_runner = agent_runner
        self.config = config
        self._running_agents: dict[str, asyncio.Task] = {}
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """Start the dispatch loop"""
        while not self._stop_event.is_set():
            await self._dispatch_tick()
            await asyncio.sleep(self.config.dispatch_interval_seconds)

    async def stop(self) -> None:
        """Stop the dispatch loop gracefully"""
        self._stop_event.set()
        # Wait for running agents to complete or cancel them

    async def _dispatch_tick(self) -> None:
        """One iteration of the dispatch loop"""
        # 1. Count running agents
        # 2. If slots available, get next READY work unit
        # 3. Spawn agent task for work unit
        # 4. Update work unit status to RUNNING

    async def _run_work_unit(self, work_unit: WorkUnit) -> None:
        """Execute a single work unit (called as async task)"""
        # 1. Create worktree if needed
        # 2. Run phase via agent_runner
        # 3. On completion: advance phase or mark DONE
        # 4. On suspension: mark NEEDS_ATTENTION, save session_id
        # 5. On error: mark NEEDS_ATTENTION
        # 6. Remove from _running_agents when done

    def get_running_count(self) -> int:
        """Return number of currently running agents"""
```

Location: src/orchestrator/scheduler.py

### Step 7: Integrate scheduler into daemon

Modify `src/orchestrator/daemon.py` to:

1. Import and instantiate Scheduler in daemon startup
2. Start scheduler as background asyncio task alongside uvicorn
3. Stop scheduler gracefully on daemon shutdown
4. Pass scheduler reference to API for status queries

Modify `create_app()` in `src/orchestrator/api.py` to accept scheduler reference for status endpoint updates.

Location: src/orchestrator/daemon.py, src/orchestrator/api.py

### Step 8: Add inject command and API endpoint

Add `POST /work-units/inject` endpoint to `src/orchestrator/api.py`:
- Accepts `chunk` name (required)
- Validates chunk directory exists with GOAL.md
- Determines initial phase (GOAL if no PLAN.md, PLAN if PLAN.md exists but no implementation, IMPLEMENT if has PLAN.md)
- Creates work unit with determined phase and READY status
- Returns created work unit

Add `ve orch inject <chunk>` CLI command to `src/ve.py`:
- Calls the inject endpoint
- `--all-proposed` flag to inject all proposed chunks from investigations/narratives

Location: src/orchestrator/api.py, src/ve.py

### Step 9: Add queue and prioritize commands

Add `GET /work-units/queue` endpoint to `src/orchestrator/api.py`:
- Returns READY work units ordered by priority DESC, created_at ASC
- Includes count of blocked work units waiting on each

Add `PATCH /work-units/{chunk}/priority` endpoint:
- Accepts `priority` integer
- Updates work unit priority

Add CLI commands to `src/ve.py`:
- `ve orch queue` - Lists ready queue (like `ve orch ps --status READY` but with priority order)
- `ve orch prioritize <chunk> [priority]` - Sets priority (default: bump by 10)

Location: src/orchestrator/api.py, src/ve.py

### Step 10: Add config command

Add `GET /config` and `PATCH /config` endpoints to `src/orchestrator/api.py`:
- GET returns current config as JSON
- PATCH updates config values (max_agents, dispatch_interval_seconds)

Add CLI command to `src/ve.py`:
- `ve orch config` - Shows current config
- `ve orch config --max-agents=N` - Sets max agents
- `ve orch config --dispatch-interval=N` - Sets dispatch interval

Location: src/orchestrator/api.py, src/ve.py

### Step 11: Update exports and package init

Update `src/orchestrator/__init__.py` to export new modules:
- WorktreeManager
- AgentRunner
- Scheduler
- OrchestratorConfig

Location: src/orchestrator/__init__.py

### Step 12: Write tests for worktree manager

Create `tests/test_orchestrator_worktree.py` with tests:
- `test_create_worktree_creates_branch_and_directory`
- `test_create_worktree_handles_existing_branch`
- `test_remove_worktree_removes_directory`
- `test_worktree_exists_returns_correct_status`
- `test_get_worktree_path_returns_correct_path`

Use `make_ve_initialized_git_repo` from conftest.py for test setup.

Location: tests/test_orchestrator_worktree.py

### Step 13: Write tests for agent runner

Create `tests/test_orchestrator_agent.py` with tests:
- `test_run_phase_completes_successfully` (mock claude-agent-sdk)
- `test_run_phase_captures_transcript`
- `test_run_phase_detects_ask_user_question`
- `test_run_phase_handles_errors`
- `test_get_phase_skill_returns_correct_command`

Mock `claude_agent_sdk.query()` to return controlled message sequences.

Location: tests/test_orchestrator_agent.py

### Step 14: Write tests for scheduler

Create `tests/test_orchestrator_scheduler.py` with tests:
- `test_dispatch_tick_spawns_agent_when_slots_available`
- `test_dispatch_tick_respects_max_agents`
- `test_dispatch_tick_picks_highest_priority_first`
- `test_work_unit_advances_phase_on_completion`
- `test_work_unit_marks_needs_attention_on_suspension`
- `test_stop_waits_for_running_agents`

Use in-memory state store and mock agent runner.

Location: tests/test_orchestrator_scheduler.py

### Step 15: Write tests for new CLI commands

Add tests to `tests/test_orchestrator_cli.py`:
- `test_inject_creates_work_unit`
- `test_inject_validates_chunk_exists`
- `test_inject_detects_initial_phase`
- `test_queue_shows_ready_work_units_by_priority`
- `test_prioritize_updates_priority`
- `test_config_shows_current_config`
- `test_config_updates_max_agents`

Location: tests/test_orchestrator_cli.py

### Step 16: Integration testing with real daemon

Add integration tests to `tests/test_orchestrator_integration.py`:
- `test_inject_and_dispatch_starts_agent` (with mocked claude-agent-sdk)
- `test_worktree_created_for_running_work_unit`
- `test_worktree_removed_after_completion`
- `test_multiple_work_units_run_in_parallel`

These tests start a real daemon, inject work units, and verify the dispatch loop behavior with mocked agent execution.

Location: tests/test_orchestrator_integration.py

## Dependencies

**Chunks:**
- `orch_foundation` - Must be complete (provides daemon, state store, models, API)

**External libraries to add:**
- `claude-agent-sdk` - Claude Agent SDK for Python

**Infrastructure:**
- Git must be installed (for worktree operations)
- Claude Code must be installed (Agent SDK depends on it as runtime)

## Risks and Open Questions

1. **Claude Agent SDK async behavior**: The SDK's `query()` returns an async generator. Need to verify:
   - Can we cleanly stop iteration when AskUserQuestion is intercepted?
   - Does stopping iteration leave the session in a resumable state?
   - What happens if the agent process crashes mid-execution?

2. **Worktree cleanup on crash**: If the daemon crashes while an agent is running:
   - Worktrees may be left behind
   - Work units may be stuck in RUNNING status
   - Need startup recovery logic to detect and clean up orphaned state

3. **Concurrent git operations**: Multiple worktree creates/removes happening simultaneously:
   - Git may have locking issues
   - May need to serialize git operations or add retry logic

4. **Agent SDK hook behavior**: The PreToolUse hook for intercepting AskUserQuestion:
   - Need to verify we can suspend iteration from within the hook
   - Need to understand what return value causes suspension vs continuation

5. **Phase detection for inject**: Determining initial phase from chunk state:
   - What if PLAN.md exists but is incomplete?
   - What if implementation files exist but chunk isn't marked complete?
   - May need heuristics or operator override

## Deviations

<!-- Populated during implementation -->