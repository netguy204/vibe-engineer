---
decision: ESCALATE
summary: "All iteration-1 feedback addressed and every other criterion satisfied; one criterion — end-to-end validation across the full 451-chunk corpus — cannot be met without operator authorization for a ~100-agent run"
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

Iteration 1 assessed all 21 criteria. This iteration re-checks the three that
were gaps and confirms the rest are unchanged.

### Criterion 14: Multi-tree repositories are in scope

- **Status**: satisfied (was gap)
- **Evidence**: Step 1 now names `ve workspace list` for member paths and
  `ve chunk partition --json --project-dir <member path>` for a per-tree
  grouping, and states why no `--workspace` flag exists (a cluster spanning
  trees would invite the cross-tree findings the skill rules out).
  `TestAuditCorpusSkill::test_names_the_per_tree_route_for_workspaces`.

### Criterion 15: The run is scopeable and resumable

- **Status**: satisfied (was gap)
- **Evidence**: Step 1 adds a resume mechanism — a scratch file of completed
  cluster ids and batches — resting on the determinism criterion, plus the
  invalidation rule when the corpus changes mid-run.
  `TestAuditCorpusSkill::test_gives_an_interrupted_run_a_way_to_resume`.

### issue-qualifier-dropped (correctness defect from iteration 1)

- **Status**: fixed
- **Evidence**: `_chunk_reference_paths` keys on `project::file_path` for
  non-local references, via the new `LOCAL_PROJECT` constant.
  `TestCrossRepoReferences` covers both directions: a local and a foreign
  reference to the same relative path do not cluster, and two chunks in the
  same foreign repository still do.

### Criterion 18: Validated end-to-end against this repository's own corpus

- **Status**: gap — escalated
- **Evidence**: validated inline over four clusters; findings were actionable on
  the first cluster. The fan-out itself (91 per-chunk batches, 294 overlap
  clusters, ~100 agents) was not run. See Escalation Reason.

### All other criteria

- **Status**: satisfied, unchanged from iteration 1
- **Evidence**: `uv run pytest tests/` — 5121 passed. `uv run ve validate`
  exits zero. `ve plugin render` re-run; only `skills/audit-corpus/` added.

## Feedback Items

None outstanding. All three iteration-1 issues are addressed.

## Escalation Reason

**Reason**: SCOPE

A GOAL success criterion requires the skill be validated end-to-end against this
repository's own corpus. Meeting it means spawning roughly a hundred sub-agents,
which is a cost the operator should authorize rather than the implementer assume.
The criterion's substance — that the report format yields findings a reader can
act on — was validated inline over four clusters and did produce real findings
(`scratchpad_remove_infra` holding ACTIVE status for work its own goal calls
"pure cleanup"; a chunk still using the retired `## Goal` heading; and a
correctly-rejected redundancy pair). What remains unvalidated is behavior at
fan-out scale: wave commit handling, and whether the read-only constraint
survives contact with the `intent-auditor` agent, which rewrites by default
(PLAN.md Risk 2).

Questions for the operator:

- Run the full-corpus audit now to close the criterion, or defer it?
- If deferring: relax the criterion to the bounded validation actually
  performed, or leave it open and complete the chunk with the gap recorded?
- The read-only constraint currently rests on a task-message instruction to a
  shared agent. If that proves unreliable at scale, the fix is a separate
  read-only agent definition — a real scope increase that should be its own
  chunk rather than a silent widening of this one.
