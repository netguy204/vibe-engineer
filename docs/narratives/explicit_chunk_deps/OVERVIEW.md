---
status: DRAFTING
advances_trunk_goal: "Required Properties: Following the workflow must maintain the health of documents over time and should not grow more difficult over time."
proposed_chunks:
  - prompt: "Add depends_on field to chunk GOAL.md template with schema documentation explaining it provides explicit dependencies that bypass the oracle's auto-detection"
    chunk_directory: null
    depends_on: []
  - prompt: "Add depends_on field to proposed_chunks schema in narrative and investigation templates, using index-based references to other prompts in the same array"
    chunk_directory: null
    depends_on: []
  - prompt: "Propagate dependencies during chunk-create: when creating a chunk from a narrative, translate index-based depends_on to chunk directory names"
    chunk_directory: null
    depends_on: [1]
  - prompt: "Add explicit_deps flag to WorkUnit model indicating this work unit uses declared dependencies and should skip oracle conflict detection"
    chunk_directory: null
    depends_on: []
  - prompt: "Implement batch injection with topological sort: extend ve orch inject to accept multiple chunks, sort by dependency graph, and inject in order so depends_on names resolve"
    chunk_directory: null
    depends_on: [0, 3]
  - prompt: "Skip oracle for explicit-dep work units: modify scheduler's _check_conflicts to bypass oracle when explicit_deps=True, using only declared blocked_by"
    chunk_directory: null
    depends_on: [3]
created_after: []
---

## Advances Trunk Goal

**Required Properties**: "Following the workflow must maintain the health of documents over time and should not grow more difficult over time."

The orchestrator's conflict oracle currently suffers from false positives when detecting conflicts between chunks. This creates friction: chunks that could safely run in parallel get blocked, or operators must manually resolve spurious conflicts. By allowing explicit dependency declarations, agents can express the *intended* execution order directly, bypassing heuristic detection and making parallel execution predictable.

## Driving Ambition

When creating batches of chunks from narratives or investigations, agents often know the conceptual dependencies between chunks (e.g., "the client chunk needs the API chunk's interfaces"). Currently there's no way to declare these dependencies - the orchestrator relies entirely on auto-detection via the conflict oracle, which:

- Only activates at PLAN/COMPLETED stages (too late for initial scheduling)
- Misses semantic dependencies that don't overlap at file level
- Produces false positives that block unrelated work

We want agents to declare dependencies explicitly when they know them. These declared dependencies should be **authoritative** - they bypass the oracle entirely rather than layering on top of it. A well-structured narrative batch with complete dependency declarations should run without any oracle interference: no false positives, predictable execution order.

The design uses a dual-declaration model:
1. **Narrative/Investigation proposed_chunks** gain a `depends_on` field using index-based references
2. **Chunk GOAL.md frontmatter** gains a `depends_on` field with chunk directory names
3. At batch injection time, dependencies translate to `blocked_by` with oracle bypass

Dependencies are **intra-batch scoped**: they express order within a single injection batch. Chunks from different batches continue using auto-detection.

## Chunks

1. **Add depends_on to chunk GOAL.md template** - Add the frontmatter field with schema documentation explaining it bypasses the oracle

2. **Add depends_on to proposed_chunks schema** - Extend narrative/investigation templates to support index-based dependencies in proposed_chunks arrays

3. **Propagate dependencies during chunk-create** - When creating a chunk from a narrative, translate index-based deps to chunk directory names (depends on #2)

4. **Add explicit_deps flag to WorkUnit** - New boolean field indicating this work unit uses declared dependencies and skips oracle (depends on nothing)

5. **Batch injection with topological sort** - Extend `ve orch inject` to accept multiple chunks, topologically sort by dependencies, inject in order so depends_on names resolve to existing work units (depends on #1, #4)

6. **Skip oracle for explicit-dep work units** - Modify scheduler's `_check_conflicts` to bypass oracle when `explicit_deps=True`, using only the declared `blocked_by` list (depends on #4)

## Completion Criteria

When complete, an operator can:

1. Create a narrative with proposed_chunks that include `depends_on` references
2. Batch-create chunks from the narrative, with dependencies automatically translated to chunk directory names
3. Batch-inject those chunks into the orchestrator with `ve orch inject chunk_a chunk_b chunk_c`
4. Watch them execute in dependency order without oracle false positives blocking progress

The key outcome: **predictable parallel execution** for well-structured work batches.