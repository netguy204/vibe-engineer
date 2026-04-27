---
discovered_by: claude
discovered_at: 2026-04-26T02:21:54+00:00
severity: medium
status: open
resolved_by: null
artifacts:
  - docs/chunks/orch_attention_queue/GOAL.md
  - src/orchestrator/state.py
  - src/orchestrator/api/attention.py
---

# orch_attention_queue over-claims priority scoring scope

## Claim

`docs/chunks/orch_attention_queue/GOAL.md` is ACTIVE and asserts two
priority-scoring success criteria that the implementation does not deliver:

**Success criterion 1** ("Attention queue shows NEEDS_ATTENTION work units
with priority"):

> Priority calculated by: blocked_chunk_count + (depth_in_graph * weight)

**Success criterion 5** ("Priority scoring reflects downstream impact"):

> Compute `blocked_by` graph from work unit dependencies
> Count how many work units are **transitively** blocked by each attention item
> Higher blocked count = higher priority (surface items that unblock the most work)

The body prose also describes the chunk as adding "Priority scoring based on
how many other work units are blocked" with the implication that the scoring
captures graph-depth and transitive impact.

## Reality

`StateStore.get_attention_queue()` in `src/orchestrator/state.py:795` orders
attention items by direct one-hop blocks count, not by any depth-weighted or
transitive metric:

```sql
SELECT w.*, (
    SELECT COUNT(*) FROM work_units b
    WHERE EXISTS (
        SELECT 1 FROM json_each(b.blocked_by)
        WHERE value = w.chunk
    )
) as blocks_count
FROM work_units w
WHERE w.status = ?
ORDER BY blocks_count DESC, w.updated_at ASC
```

The subquery counts work units that have the attention item *directly* in
their `blocked_by` list — a single hop. There is no recursive CTE, no
transitive closure computation, and no `depth_in_graph` factor. The
`api/attention.py` endpoint passes `blocks_count` straight through (line 92)
without further weighting.

So the implementation delivers:
- Order by direct (one-hop) `blocks_count` DESC
- Tie-break by `updated_at` ASC

The success criteria assert:
- Order by `blocked_chunk_count + (depth_in_graph * weight)` (no depth factor exists)
- Counts of *transitively* blocked work units (only direct counts exist)

Neither `code_references` row admits `status: partial`, so the audit veto
rule based on declared over-claim does not fire — this is an *undeclared*
over-claim caught only by symmetric verification of the named SQL/Python
against the success-criteria text.

## Workaround

None. The audit only logs. The CLI command, API endpoint, and database
migration described in the other success criteria do exist and behave as
described — only the priority-scoring formula and transitive-blocking claims
are unsupported. Agents reading the GOAL and assuming attention items are
ranked by transitive downstream impact will get the wrong mental model.

## Fix paths

1. **Implement transitive blocked counting and depth weighting** (preferred
   if the original ambition stands): replace the one-hop subquery with a
   recursive CTE that walks the `blocked_by` graph, and add a depth factor
   to the priority expression. Update the API contract and CLI output to
   reflect the richer score.
2. **Narrow the success criteria** to match what the SQL actually does:
   "Priority = direct blocks_count, tie-broken by oldest updated_at." Drop
   the `depth_in_graph * weight` formula and the "transitively" qualifier.
   This is the honest description of the shipped behavior.
