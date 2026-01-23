<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk implements the **Conflict Oracle** - a progressive analysis system that determines whether chunks can be safely parallelized or require serialization. The oracle integrates with the orchestrator's scheduler to provide intelligent scheduling decisions.

**Key technical choices:**

1. **Progressive analysis based on chunk lifecycle stage**: The oracle uses increasingly precise information as chunks advance through their lifecycle:
   - PROPOSED (prompt only): LLM semantic comparison
   - GOAL exists: LLM comparison of intent + scope
   - PLAN exists: File overlap detection via `Location:` lines + optional LLM symbol prediction
   - COMPLETED: Exact symbol overlap from `code_references` frontmatter

2. **Three-way verdict system**: Rather than binary conflict detection, the oracle returns:
   - `INDEPENDENT` (high confidence no overlap) - safe to parallelize
   - `SERIALIZE` (high confidence overlap) - must sequence
   - `ASK_OPERATOR` (uncertain) - queue attention item for human judgment

3. **Symbol-level granularity when available**: File overlap is too coarse (many chunks touch `src/ve.py`). When `code_references` are available, the oracle uses symbol-level comparison via the existing `compute_symbolic_overlap()` function in `src/chunks.py`.

4. **Conflict verdicts stored on work units**: Results are persisted so the scheduler can use them for `blocked_by` population without re-computing.

5. **LLM-based analysis via Claude Agent SDK**: For semantic comparisons at PROPOSED/GOAL stages, use a targeted LLM call rather than full agent sessions.

**Patterns from existing orchestrator code:**
- Pydantic models for data structures (extend WorkUnit with conflict fields)
- SQLite state persistence (migration for conflict verdicts table)
- Starlette HTTP API (new endpoints for conflict analysis and resolution)
- Click CLI commands (add `ve orch resolve`)

**Testing approach per docs/trunk/TESTING_PHILOSOPHY.md:**
- Unit tests for conflict analysis at each lifecycle stage
- Unit tests for symbol overlap detection (using existing test patterns)
- Integration tests for scheduler interaction with conflict verdicts
- Mock LLM calls for deterministic testing

## Subsystem Considerations

No existing subsystems are directly relevant to this chunk. The conflict oracle is a new component within the orchestrator system.

## Sequence

### Step 1: Add ConflictVerdict enum and models

Create conflict-related models in `src/orchestrator/models.py`:

```python
class ConflictVerdict(StrEnum):
    INDEPENDENT = "INDEPENDENT"  # Safe to parallelize
    SERIALIZE = "SERIALIZE"       # Must sequence
    ASK_OPERATOR = "ASK_OPERATOR" # Uncertain, needs human judgment

class ConflictAnalysis(BaseModel):
    chunk_a: str
    chunk_b: str
    verdict: ConflictVerdict
    confidence: float  # 0.0 to 1.0
    reason: str
    analysis_stage: str  # PROPOSED, GOAL, PLAN, COMPLETED
    overlapping_files: list[str] = []  # Files detected as overlapping
    overlapping_symbols: list[str] = []  # Symbols detected as overlapping (when available)
    created_at: datetime
```

Add chunk backreference comment.

Location: src/orchestrator/models.py

### Step 2: Add conflict analysis fields to WorkUnit model

Extend the `WorkUnit` model to include conflict-related fields:
- `conflict_verdicts: dict[str, ConflictVerdict]` - Maps other chunk names to verdicts
- `conflict_override: Optional[ConflictVerdict]` - Operator override for ASK_OPERATOR cases

Update `model_dump_json_serializable()` to include the new fields.

Location: src/orchestrator/models.py

### Step 3: Add database migration for conflict storage

Create `_migrate_v7()` in `src/orchestrator/state.py` that:
1. Creates `conflict_analyses` table for storing conflict analysis results
2. Adds `conflict_verdicts TEXT` column (JSON) to `work_units` table
3. Adds `conflict_override TEXT` column to `work_units` table

Increment `CURRENT_VERSION` to 7.

Schema for `conflict_analyses` table:
```sql
CREATE TABLE conflict_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_a TEXT NOT NULL,
    chunk_b TEXT NOT NULL,
    verdict TEXT NOT NULL,
    confidence REAL NOT NULL,
    reason TEXT NOT NULL,
    analysis_stage TEXT NOT NULL,
    overlapping_files TEXT,  -- JSON array
    overlapping_symbols TEXT,  -- JSON array
    created_at TEXT NOT NULL,
    UNIQUE(chunk_a, chunk_b)  -- One analysis per pair
);
```

Location: src/orchestrator/state.py

### Step 4: Create conflict oracle module

Create `src/orchestrator/oracle.py` with the core conflict analysis logic:

```python
class ConflictOracle:
    def __init__(self, project_dir: Path, store: StateStore):
        self.project_dir = project_dir
        self.store = store
        self.chunks = Chunks(project_dir)

    def analyze_conflict(self, chunk_a: str, chunk_b: str) -> ConflictAnalysis:
        """Analyze potential conflict between two chunks.

        Uses progressive analysis based on what information is available.
        """

    def _analyze_proposed_stage(self, prompt_a: str, prompt_b: str) -> ConflictAnalysis:
        """LLM semantic comparison of prompts."""

    def _analyze_goal_stage(self, goal_a: str, goal_b: str) -> ConflictAnalysis:
        """LLM comparison of GOAL.md contents."""

    def _analyze_plan_stage(self, chunk_a: str, chunk_b: str) -> ConflictAnalysis:
        """File overlap detection from PLAN.md Location: lines."""

    def _analyze_completed_stage(self, chunk_a: str, chunk_b: str) -> ConflictAnalysis:
        """Exact symbol overlap from code_references frontmatter."""

    def _detect_stage(self, chunk: str) -> str:
        """Detect what stage of information is available for a chunk."""

    def _extract_locations_from_plan(self, chunk: str) -> list[str]:
        """Parse Location: lines from PLAN.md."""

    def should_serialize(self, chunk_a: str, chunk_b: str) -> ConflictVerdict:
        """Main entry point: determine if two chunks should be serialized."""
```

The oracle uses different analysis strategies based on the minimum stage of the two chunks (use the least precise analysis available for both).

Location: src/orchestrator/oracle.py

### Step 5: Implement file overlap detection from PLAN.md

Add helper function to parse `Location:` lines from PLAN.md files:

```python
def extract_plan_locations(plan_path: Path) -> list[str]:
    """Extract file paths from Location: lines in PLAN.md.

    Looks for patterns like:
    - Location: src/foo.py
    - Location: src/foo.py (new file)
    - Location: tests/test_foo.py
    """
```

This enables conflict detection at the PLAN stage before implementation begins.

Location: src/orchestrator/oracle.py

### Step 6: Implement symbol-level conflict detection

For chunks with `code_references` populated, use the existing `compute_symbolic_overlap()` function from `src/chunks.py` to detect symbol-level conflicts.

Add method to oracle:
```python
def _get_code_references(self, chunk: str) -> list[str]:
    """Extract code_references from chunk frontmatter."""
    frontmatter = self.chunks.parse_chunk_frontmatter(chunk)
    if frontmatter and frontmatter.code_references:
        return [ref.ref for ref in frontmatter.code_references]
    return []
```

Location: src/orchestrator/oracle.py

### Step 7: Implement LLM-based semantic analysis

For PROPOSED and GOAL stages where we only have text descriptions, use LLM analysis. Create a focused prompt that asks Claude to assess overlap likelihood:

```python
async def _llm_semantic_analysis(
    self,
    text_a: str,
    text_b: str,
    context: str,  # "prompt" or "goal"
) -> tuple[ConflictVerdict, float, str]:
    """Use LLM to assess semantic overlap between two chunk descriptions."""
```

The LLM should return:
- Verdict (INDEPENDENT, SERIALIZE, or ASK_OPERATOR)
- Confidence score (0.0-1.0)
- Reasoning explanation

Use the Claude Agent SDK for this targeted analysis call.

Location: src/orchestrator/oracle.py

### Step 8: Add StateStore methods for conflict persistence

Add methods to `StateStore` for conflict management:

```python
def save_conflict_analysis(self, analysis: ConflictAnalysis) -> None:
    """Save or update a conflict analysis."""

def get_conflict_analysis(self, chunk_a: str, chunk_b: str) -> Optional[ConflictAnalysis]:
    """Get existing conflict analysis for a chunk pair."""

def list_conflicts_for_chunk(self, chunk: str) -> list[ConflictAnalysis]:
    """Get all conflict analyses involving a chunk."""

def clear_conflicts_for_chunk(self, chunk: str) -> None:
    """Clear all conflict analyses for a chunk (called when chunk advances)."""
```

Location: src/orchestrator/state.py

### Step 9: Add conflict resolution API endpoints

Add endpoints to `src/orchestrator/api.py`:

**GET /conflicts/{chunk}** - Get all conflict analyses for a chunk
```python
async def get_conflicts_endpoint(request: Request) -> JSONResponse:
    """Get conflict analyses involving a specific chunk."""
```

**POST /conflicts/analyze** - Trigger conflict analysis between two chunks
```python
async def analyze_conflicts_endpoint(request: Request) -> JSONResponse:
    """Analyze potential conflicts between two chunks."""
```

**POST /work-units/{chunk}/resolve** - Resolve an ASK_OPERATOR conflict
```python
async def resolve_conflict_endpoint(request: Request) -> JSONResponse:
    """Operator resolves an uncertain conflict with parallelize or serialize."""
```

Location: src/orchestrator/api.py

### Step 10: Add `ve orch resolve` CLI command

Create CLI command for conflict resolution:

```bash
ve orch resolve <chunk> --with <other_chunk> [parallelize|serialize]
```

The command:
1. Shows the conflict analysis for the two chunks
2. Accepts operator verdict: `parallelize` (INDEPENDENT) or `serialize`
3. Stores the override in the work unit
4. Updates blocked_by if necessary

Location: src/ve.py

### Step 11: Add `ve orch conflicts` CLI command

Create CLI command to view conflicts:

```bash
ve orch conflicts [chunk]
ve orch conflicts --unresolved  # Show only ASK_OPERATOR verdicts
```

Output shows:
- Chunk pairs with conflict verdicts
- Confidence scores
- Overlapping files/symbols when available

Location: src/ve.py

### Step 12: Integrate oracle into scheduler

Modify `src/orchestrator/scheduler.py` to use the conflict oracle:

1. Before dispatching a work unit, check for conflicts with other RUNNING/READY work units
2. If `SERIALIZE` verdict exists and blocker is still active, add to `blocked_by`
3. If `ASK_OPERATOR` verdict exists without override, queue attention item
4. Re-evaluate conflicts when work units complete (some may unblock)

Add method:
```python
async def _check_conflicts(self, work_unit: WorkUnit) -> list[str]:
    """Check for conflicts with active work and return blocking chunks."""
```

Location: src/orchestrator/scheduler.py

### Step 13: Add conflict re-evaluation on lifecycle advancement

When a chunk advances through its lifecycle (GOAL → PLAN → IMPLEMENT → COMPLETE), re-analyze conflicts with more precise information:

```python
async def _reanalyze_conflicts(self, chunk: str) -> None:
    """Re-analyze conflicts for a chunk with updated information.

    Called when chunk advances stages and more precise analysis is possible.
    """
```

This enables the system to upgrade ASK_OPERATOR to INDEPENDENT or SERIALIZE as more information becomes available.

Location: src/orchestrator/scheduler.py

### Step 14: Add client methods for conflict operations

Add methods to `OrchestratorClient` in `src/orchestrator/client.py`:

```python
def get_conflicts(self, chunk: str) -> list[dict]:
    """Get all conflicts for a chunk."""

def analyze_conflicts(self, chunk_a: str, chunk_b: str) -> dict:
    """Request conflict analysis between two chunks."""

def resolve_conflict(self, chunk: str, other_chunk: str, verdict: str) -> dict:
    """Submit operator resolution for a conflict."""
```

Location: src/orchestrator/client.py

### Step 15: Write tests for conflict oracle core logic

Create `tests/test_orchestrator_oracle.py` with tests:

**Stage detection tests:**
- `test_detect_stage_proposed` - Returns PROPOSED when only prompt available
- `test_detect_stage_goal` - Returns GOAL when GOAL.md exists
- `test_detect_stage_plan` - Returns PLAN when PLAN.md has content
- `test_detect_stage_completed` - Returns COMPLETED when code_references populated

**File overlap tests:**
- `test_extract_locations_from_plan` - Parses Location: lines correctly
- `test_file_overlap_detection_positive` - Detects overlapping files
- `test_file_overlap_detection_negative` - Returns INDEPENDENT for disjoint files

**Symbol overlap tests:**
- `test_symbol_overlap_uses_compute_symbolic_overlap` - Integrates with chunks.py
- `test_symbol_overlap_same_file_different_symbols` - Returns INDEPENDENT
- `test_symbol_overlap_same_symbol` - Returns SERIALIZE

Location: tests/test_orchestrator_oracle.py

### Step 16: Write tests for LLM semantic analysis

Create tests that mock the Claude Agent SDK for deterministic behavior:

- `test_llm_analysis_clear_independent` - High confidence independent
- `test_llm_analysis_clear_conflict` - High confidence overlap
- `test_llm_analysis_uncertain` - Low confidence returns ASK_OPERATOR

Location: tests/test_orchestrator_oracle.py

### Step 17: Write tests for conflict persistence

Add tests to `tests/test_orchestrator_state.py`:

- `test_save_conflict_analysis` - Saves to database
- `test_get_conflict_analysis` - Retrieves by pair
- `test_conflict_analysis_unique_pair` - Handles update vs insert
- `test_list_conflicts_for_chunk` - Returns all analyses for chunk
- `test_clear_conflicts_for_chunk` - Removes analyses on advancement

Location: tests/test_orchestrator_state.py

### Step 18: Write tests for scheduler integration

Add tests to `tests/test_orchestrator_scheduler.py`:

- `test_dispatch_respects_serialize_verdict` - Blocked by conflicting chunk
- `test_dispatch_allows_independent_verdict` - Not blocked when independent
- `test_ask_operator_queues_attention` - ASK_OPERATOR creates attention item
- `test_reanalyze_on_advancement` - Conflicts re-analyzed when chunk advances

Location: tests/test_orchestrator_scheduler.py

### Step 19: Write CLI tests for conflict commands

Add tests to `tests/test_orchestrator_cli.py`:

**TestOrchConflicts class:**
- `test_conflicts_empty` - No conflicts returns empty
- `test_conflicts_with_items` - Shows formatted conflicts
- `test_conflicts_unresolved_filter` - Filters to ASK_OPERATOR only
- `test_conflicts_json` - JSON output format

**TestOrchResolve class:**
- `test_resolve_parallelize` - Sets INDEPENDENT override
- `test_resolve_serialize` - Sets SERIALIZE verdict
- `test_resolve_not_found` - Error for unknown chunk
- `test_resolve_no_conflict` - Error when no conflict exists

Location: tests/test_orchestrator_cli.py

### Step 20: Integration test for full conflict flow

Add integration test that exercises the complete flow:

1. Inject two chunks with overlapping PLAN.md locations
2. Verify conflict analysis returns SERIALIZE or ASK_OPERATOR
3. For ASK_OPERATOR: resolve via `ve orch resolve`
4. Verify scheduler respects the verdict
5. Complete one chunk, verify other is unblocked

Location: tests/test_orchestrator_integration.py

---

**BACKREFERENCE COMMENTS**

All new files in src/orchestrator/ should include:
```python
# Chunk: docs/chunks/orch_conflict_oracle - Conflict oracle for scheduling
```

Modifications to existing files should add:
```python
# Chunk: docs/chunks/orch_conflict_oracle - Conflict analysis integration
```

## Dependencies

**Chunks:**
- `orch_foundation` (ACTIVE) - Provides daemon, state store, models, API
- `orch_scheduling` (ACTIVE) - Provides scheduler, agent runner
- `orch_attention_queue` (ACTIVE) - Provides attention queue for ASK_OPERATOR verdicts
- `orch_inject_path_compat` (ACTIVE) - Path normalization for chunk names
- `orch_submit_future_cmd` (ACTIVE) - Batch injection of FUTURE chunks

**External libraries:**
- `claude-agent-sdk` - Already installed; used for LLM semantic analysis

**Internal dependencies:**
- `src/chunks.py` - `compute_symbolic_overlap()` function for symbol-level analysis
- `src/symbols.py` - `is_parent_of()`, `parse_reference()` for symbol comparison

## Risks and Open Questions

1. **LLM cost and latency**: Semantic analysis at PROPOSED/GOAL stages requires LLM calls. Need to:
   - Cache results to avoid repeated analysis
   - Use fast model (e.g., Claude Haiku) for initial screening
   - Consider batching analyses when multiple chunks are injected

2. **Conflict analysis timing**: When should analysis happen?
   - On inject: Analyze against all existing work units
   - On advancement: Re-analyze with more precise data
   - Decision: Do both, with caching to avoid redundant work

3. **Conflict pair ordering**: `(chunk_a, chunk_b)` vs `(chunk_b, chunk_a)` - need consistent ordering
   - Decision: Store with alphabetically-sorted pair for uniqueness

4. **Symbol overlap false positives**: Two chunks might touch the same symbol but in compatible ways
   - Mitigation: ASK_OPERATOR for uncertain cases; operator can parallelize if they know changes are compatible

5. **PLAN.md Location: format variations**: Different operators might format Location: lines differently
   - Decision: Parse flexibly with regex, handle common variations

6. **Re-analysis cascading**: When one chunk advances, should we re-analyze all its conflict pairs?
   - Decision: Yes, but only if the new stage provides more precise information than the stored analysis

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->
