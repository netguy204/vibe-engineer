---
decision: FEEDBACK
summary: "CLI grouping and skill both land, but the overlap index discards the cross-repo project qualifier, and the skill omits two behaviors its GOAL requires (per-tree partition invocation, resumability)"
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve chunk partition --json` emits, for every chunk in scope, its cluster assignment under both relations

- **Status**: satisfied
- **Evidence**: `src/cli/chunk.py#partition` calls `partition_chunks` once and renders `PartitionResult.to_dict()`; verified on the real 454-chunk corpus (294 overlap clusters, 68 similarity clusters).

### Criterion 2: Nothing in scope is silently dropped

- **Status**: satisfied
- **Evidence**: `unclustered` and `high_fan_in_paths` both in the payload and in the human output. `tests/test_chunk_partition.py::TestCodeOverlapRelation::test_reference_less_chunk_is_reported_not_dropped` and `TestHubFileExclusion::test_the_skipped_hub_is_reported_not_silently_dropped`.

### Criterion 3: The command reuses `cluster_chunks` and `qualify_ref` / `parse_reference` rather than forking them

- **Status**: satisfied
- **Evidence**: `partition_chunks` delegates the similarity half to `cluster_chunks`; `_chunk_reference_paths` uses `symbols.qualify_ref` / `symbols.parse_reference`. The overlap relation is new code, justified in GOAL (`find_overlapping_chunks` is directional, status-locked, and `code_references`-only).

### Criterion 4: `--min-similarity` accepted, default consistent with `ve chunk cluster`

- **Status**: satisfied
- **Evidence**: default 0.3 in both; `TestContentSimilarityRelation::test_min_similarity_defaults_to_the_cluster_command_default`.

### Criterion 5: Status filtering matches `ve chunk list`

- **Status**: satisfied
- **Evidence**: same `models.parse_status_filters` helper and the same `--future`/`--active`/`--implementing` shortcuts; `TestStatusFiltering` (3 tests).

### Criterion 6: Tests assert deterministic output for a fixture corpus

- **Status**: satisfied
- **Evidence**: `TestDeterminism` — byte-identical repeated runs, sorted members/evidence, and a corpus rebuilt in reverse creation order producing identical output.

### Criterion 7: Skill template exists, renders, passes plugin invariants

- **Status**: satisfied
- **Evidence**: `src/templates/plugin/skills/audit-corpus.md.jinja2` → `skills/audit-corpus/SKILL.md`; `hooks.KNOWN_EVENTS` updated; 247 generic plugin-skill invariants pass.

### Criteria 8-12: The four axes defined (validity / freshness / accuracy / redundancy)

- **Status**: satisfied
- **Evidence**: table in the skill's Purpose section names each axis with its question and source of truth; validity delegates to `ve validate` (Step 2), accuracy to `intent-auditor` (Step 4). `TestAuditCorpusSkill::test_defines_all_four_audit_axes`.

### Criterion 13: Two passes with different partitioning, and the skill says why

- **Status**: satisfied
- **Evidence**: "Why two passes, partitioned differently" states the local/relational distinction and the quadratic cost the grouping bounds.

### Criterion 14: Multi-tree repositories are in scope

- **Status**: gap
- **Evidence**: the skill names `ve chunk list --workspace` for enumerating trees and rules cross-tree redundancy out of scope, but never says how to obtain a per-tree grouping. `ve chunk partition` has no `--workspace` flag, so an agent following the skill has no stated route to a member tree's clusters.

### Criterion 15: The run is scopeable and resumable

- **Status**: gap
- **Evidence**: Step 1 covers scope (whole corpus / one cluster / since a git ref). Resumability is absent — there is no mechanism for an interrupted run to skip completed clusters, and nothing in the skill mentions one.

### Criterion 16: Findings report with proposed actions, plus INCONSISTENCIES entries, no rewrites

- **Status**: satisfied
- **Evidence**: Step 6; the read-only constraint is imposed in the Step 4 task message and re-checked via `git status --short` after each wave. `TestAuditCorpusSkill::test_forbids_rewriting_chunks`.

### Criterion 17: Redundancy findings name the resolution command

- **Status**: satisfied
- **Evidence**: Step 6 requires the proposed action be the command the operator would run, with three examples.

### Criterion 18: Validated end-to-end against this repository's corpus

- **Status**: gap (disclosed)
- **Evidence**: validated inline over four clusters, not at fan-out scale; recorded in PLAN.md Deviations with what it does and does not establish. Findings were actionable on the first cluster, which is the substance of the criterion; the full ~100-agent run is the operator's call and was not authorized.

### Criterion 19: `uv run ve validate` exits zero

- **Status**: satisfied
- **Evidence**: passes with warnings only. The `code↔chunk` warnings naming this chunk resolve when `code_references` are populated at completion.

### Criterion 20: `uv run pytest tests/` passes

- **Status**: satisfied
- **Evidence**: 5117 passed.

### Criterion 21: `ve plugin render` re-run, rendered SKILL.md committed alongside its template

- **Status**: satisfied
- **Evidence**: rendered; `git status` shows only `skills/audit-corpus/` added, no collateral changes to the other 39 skills. Commit is the chunk-commit step.

## Feedback Items

### issue-qualifier-dropped

- **Location**: `src/cluster_analysis.py#_chunk_reference_paths`
- **Concern**: The inverted index keys on `file_path` alone, discarding the project qualifier that `parse_reference` returns. A chunk referencing `org/repo::src/foo.py` and a local chunk referencing `src/foo.py` land in the same cluster, reported as sharing a file they do not share. In task and workspace contexts — precisely the multi-project setting the skill claims to support — this manufactures redundancy findings between chunks in different repositories.
- **Suggestion**: Key on the qualified path (`project::file_path` when project is not the local `.`), matching how `compute_symbolic_overlap` compares fully-qualified refs. Add a test with one local and one cross-repo reference to the same relative path asserting they do not cluster.
- **Severity**: functional
- **Confidence**: high

### issue-workspace-route

- **Location**: `src/templates/plugin/skills/audit-corpus.md.jinja2`, Step 1 "Multi-tree repositories"
- **Concern**: Criterion 14 requires per-tree audits, but the skill gives no way to get a per-tree grouping.
- **Suggestion**: State that each member tree is grouped by running `ve chunk partition --json --project-dir <member path>`, and that `ve workspace list` (or the `--workspace` listing) supplies the member paths.
- **Severity**: functional
- **Confidence**: high

### issue-no-resume

- **Location**: `src/templates/plugin/skills/audit-corpus.md.jinja2`
- **Concern**: Criterion 15 requires resumability. Nothing in the skill addresses an interrupted run, and on a corpus large enough to need this skill an interruption is likely rather than exceptional.
- **Suggestion**: Add a resume mechanism that leans on the determinism already built: cluster ids are stable across runs on an unchanged corpus, so a run can record completed cluster ids to a scratch file and skip them on resume. Say explicitly that a corpus changed mid-run invalidates the ids and the run should restart.
- **Severity**: functional
- **Confidence**: high

## Escalation Reason

<!-- For ESCALATE decisions only. Delete section if APPROVE/FEEDBACK. -->
