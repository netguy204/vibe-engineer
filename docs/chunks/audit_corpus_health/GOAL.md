---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cluster_analysis.py
- src/cli/chunk.py
- src/hooks.py
- src/templates/plugin/skills/audit-corpus.md.jinja2
- skills/audit-corpus/SKILL.md
- tests/test_chunk_partition.py
- tests/test_plugin_skills.py
- tests/test_plugin_render.py
- docs/subsystems/cluster_analysis/OVERVIEW.md
code_references:
- ref: src/cluster_analysis.py#partition_chunks
  implements: "Whole-corpus grouping under both relations in one call; the deterministic substrate the audit fans out over"
- ref: src/cluster_analysis.py#_code_overlap_clusters
  implements: "Per-file overlapping cover with a fan-in ceiling, replacing connected components, which collapsed 423 of 454 chunks into one cluster"
- ref: src/cluster_analysis.py#_chunk_reference_paths
  implements: "File keys drawn from both code_paths and code_references, keeping the project qualifier so a cross-repo path is not the local path of the same name"
- ref: src/cluster_analysis.py#PartitionResult
  implements: "Both relations plus the two blind spots — unclustered chunks and skipped hub files — so a partial run cannot read as a complete one"
- ref: src/cluster_analysis.py#OverlapCluster
  implements: "A code-overlap cluster and the shared paths and symbols that formed it"
- ref: src/cluster_analysis.py#SimilarityCluster
  implements: "A content-similarity cluster carrying its cohesion score and theme"
- ref: src/cluster_analysis.py#LOCAL_PROJECT
  implements: "The qualifier standing for this repository, distinguishing local from cross-repo reference paths"
- ref: src/cluster_analysis.py#cluster_chunks
  implements: "Mean pairwise cohesion score per cluster, and a total tie-break sort so cluster order does not inherit filesystem enumeration order"
- ref: src/cluster_analysis.py#ClusterResult
  implements: "cluster_scores field, additive so existing constructions stay valid"
- ref: src/cli/chunk.py#partition
  implements: "ve chunk partition: JSON and human output, status filtering matching ve chunk list, and --fan-in-ceiling"
- ref: src/hooks.py#KNOWN_EVENTS
  implements: "audit-corpus registered as a hook event, keeping the literal in sync with the skill surface"
- ref: src/templates/plugin/skills/audit-corpus.md.jinja2
  implements: "The audit-corpus skill: four defined axes, two passes partitioned by locality, read-only sub-agent contract, and blind-spot reporting"
- ref: skills/audit-corpus/SKILL.md
  implements: "Rendered skill shipped in the plugin"
- ref: tests/test_chunk_partition.py#TestCodeOverlapRelation
  implements: "Chunks sharing a file cluster with that path as evidence; chunks sharing nothing do not; a reference-less chunk is reported rather than dropped"
- ref: tests/test_chunk_partition.py#TestCoverNotComponents
  implements: "Transitive sharing does not merge clusters, and a chunk spanning files appears in each — the cover semantics that replaced components"
- ref: tests/test_chunk_partition.py#TestHubFileExclusion
  implements: "Hub files above the ceiling generate no cluster, are reported as skipped, and their exclusion does not cost narrower genuine overlaps"
- ref: tests/test_chunk_partition.py#TestCrossRepoReferences
  implements: "A qualified and a local path of the same name do not cluster, while two chunks inside one foreign repository still do"
- ref: tests/test_chunk_partition.py#TestDeterminism
  implements: "Byte-identical repeated runs, sorted output, and identical assignment for a corpus rebuilt in reverse creation order"
- ref: tests/test_chunk_partition.py#TestStatusFiltering
  implements: "Scope selection matching ve chunk list, including rejection of an invalid status"
- ref: tests/test_chunk_partition.py#TestSymbolEvidence
  implements: "A symbol named by two chunks appears in evidence as the stronger redundancy signal"
- ref: tests/test_plugin_skills.py#TestAuditCorpusSkill
  implements: "The skill's load-bearing properties: four axes, partition as grouping source, delegation to ve validate and intent-auditor, the read-only rule, blind-spot reporting, workspace route, and resume"
- ref: tests/test_plugin_render.py#TestCollectionLayout
  implements: "Skill surface count raised to 40 as the collection gained audit-corpus"
narrative: null
investigation: null
subsystems:
- subsystem_id: cluster_analysis
  relationship: implements
- subsystem_id: workflow_artifacts
  relationship: uses
- subsystem_id: template_system
  relationship: uses
friction_entries: []
depends_on: []
created_after:
- external_never_resolved
- hooks_lifecycle_fragments
- claudemd_marker_safety
- claudemd_symlink_notice
- template_workspace_awareness
---

# Chunk Goal

## Minor Goal

VE ships an `audit-corpus` plugin skill that reports the health of a project's
entire chunk corpus — validity, freshness, accuracy, and redundancy — and a
`ve chunk partition` CLI command that supplies the skill with a deterministic,
machine-readable partition of that corpus.

The partition is computed by the CLI from data VE already records, never by a
classifier agent. `ve chunk partition --json` groups chunks under two
independent relations: **code overlap** (chunks claiming the same file, drawn
from `code_paths` and `code_references`, with shared symbols reported as
stronger evidence) and **content similarity** (TF-IDF over GOAL.md text). The
skill consumes that assignment and fans out sub-agents over it. Because the
grouping is deterministic, two runs over an unchanged corpus produce the same
clusters and therefore the same findings.

The code-overlap relation is an overlapping **cover**, not a strict partition: a
chunk claiming five files belongs to five clusters. Grouping by connected
component instead — unioning chunks transitively through the files they share —
collapses a real corpus into a single cluster, because A shares one file with B
while B shares a different file with C. On this repository that put 423 of 454
chunks in one component, at every fan-in ceiling tried. A cover loses nothing
the audit needs: two chunks can only be redundant if they claim a file in
common, and that file's cluster contains both.

The skill separates the audit by locality, and that separation is the
load-bearing design decision:

- **Per-chunk checks are local.** A chunk over-claims, or points at a moved
  file, or holds a status that no longer describes its ownership, independently
  of every other chunk. These shard arbitrarily, N chunks per agent, and cost
  scales linearly.
- **Redundancy is relational.** Two chunks are only comparable when they land in
  the same agent's context, and naive pairwise comparison is O(n²) —
  intractable on the thousand-chunk corpora this skill exists for. The CLI
  partition is what makes the relational pass affordable: one agent per cluster,
  and chunks in different clusters are never compared.

The skill reports; it does not rewrite. Every finding lands as a proposed action
against a named chunk, and resolving redundancy — superseding, merging into a
narrative, marking COMPOSITE, historicalizing — stays an operator decision. The
skill is therefore safe to run against a corpus its operator did not author.

`audit-corpus` complements the existing `audit-intent` skill
(`skills/audit-intent/SKILL.md`) rather than replacing it. `audit-intent` is a
one-time migration that *rewrites* chunks to the present-tense standard in
`docs/trunk/CHUNKS.md`. `audit-corpus` is a recurring health report whose
distinct axis is redundancy and cross-chunk contradiction. Where the two overlap
on per-chunk accuracy, `audit-corpus` delegates to the existing `intent-auditor`
agent (`agents/intent-auditor.md`) in a read-only mode rather than restating its
detection criteria.

## Success Criteria

### The CLI partition

- `ve chunk partition --json` emits, for every chunk in scope, its cluster
  assignment under both relations, in one invocation. Shape (illustrative):
  ```json
  {
    "relations": {
      "code_overlap": [{"id": "c0", "members": ["a", "b"], "evidence": ["src/x.py"]}],
      "content_similarity": [{"id": "s0", "members": ["a", "q"], "score": 0.41, "theme": "…"}]
    },
    "unclustered": ["z"],
    "high_fan_in_paths": [{"path": "src/ve.py", "chunk_count": 50}]
  }
  ```
- Nothing in scope is silently dropped. Chunks that neither relation grouped
  appear in `unclustered`; hub files excluded from the overlap relation appear
  in `high_fan_in_paths` with the count that excluded them. A run that bounded
  its own coverage has to say so, or a partial audit reads as a complete one.
- The command reuses `src/cluster_analysis.py#cluster_chunks` for TF-IDF
  similarity rather than reimplementing it, and reuses `src/symbols.py`'s
  `qualify_ref` / `parse_reference` so the overlap relation and
  `src/chunks.py#Chunks.find_overlapping_chunks` agree on what a reference
  points at. The overlap relation itself is new code:
  `find_overlapping_chunks` answers a different question (for one chunk, which
  ACTIVE *ancestors* share a reference — directional, status-locked, and
  `code_references`-only), and calling it per chunk would be the quadratic cost
  the clustering exists to avoid.
- `--min-similarity` is accepted and defaults consistently with
  `ve chunk cluster` (currently 0.3).
- Status filtering matches `ve chunk list` (`--status`, plus the `--active`
  style shortcuts), so an operator can audit only ACTIVE chunks or include
  HISTORICAL.
- Tests assert deterministic output for a fixture corpus: the same input
  produces byte-identical cluster assignment across runs.

### The skill

- `src/templates/plugin/skills/audit-corpus.md.jinja2` exists, renders via
  `ve plugin render` to `skills/audit-corpus/SKILL.md`, and passes the
  invariants in `tests/test_plugin_skills.py` (frontmatter, no un-rendered
  Jinja2, AUTO-GENERATED header). It uses the shared `idioms.frontmatter` and
  `canonical_preamble` partials like every other plugin skill.
- The skill defines the four audit axes explicitly, so two runs mean the same
  thing by them:
  - **Validity** — the chunk's references resolve. The skill *calls*
    `ve validate` for this and reports its findings; it does not re-derive
    reference integrity the validator already owns.
  - **Freshness** — the code the chunk governs still matches what the chunk
    claims about it, and the chunk's status still answers "how much of the
    intent does this chunk own?" correctly.
  - **Accuracy** — the GOAL's assertions are true of the code (over-claim
    detection), delegated to the `intent-auditor` agent in report-only mode.
  - **Redundancy** — two or more chunks claim overlapping intent over the same
    code, making them candidates for COMPOSITE co-ownership, supersession, or
    consolidation into a narrative.
- Execution has two passes with different partitioning, and the skill states
  why: an arbitrary-shard per-chunk pass, and a one-agent-per-cluster relational
  pass driven by `ve chunk partition --json`.
- Multi-tree repositories are in scope: the skill enumerates member trees via
  `ve chunk list --workspace` and audits each tree's corpus with its own
  partition. Cross-tree redundancy is explicitly out of scope and the skill says
  so — references crossing a tree boundary belong to `ve workspace validate`.
- The run is scopeable and resumable. The operator can audit the whole corpus, a
  named cluster, or only chunks touched since a git ref; an interrupted run
  resumes without repeating completed clusters. A run that bounds its own
  coverage says what it skipped — silent truncation reads as "audited
  everything".
- Output is a findings report carrying a proposed action per finding, plus
  `docs/trunk/INCONSISTENCIES/` entries for doc-vs-code contradictions in the
  format `audit-intent` already established. No chunk file is rewritten and no
  status is changed by the skill itself.
- Redundancy findings name the resolution the operator would run
  (`ve chunk status`, `ve narrative create`, `ve chunk cluster-rename`) rather
  than describing the problem abstractly.
- The skill is validated against this repository's own corpus under parallel
  fan-out: a wave of 10 concurrent sub-agents over 50 ACTIVE chunks produces
  findings a reader can act on without re-reading the chunks themselves, and
  leaves the working tree unmodified. The second half is the load-bearing one.
  `intent-auditor` rewrites by default, so the read-only constraint is an
  instruction fighting the agent's own protocol; a wave in which agents decide
  on rewrites and `code_paths` fixes and still write nothing is what makes the
  skill safe to point at a corpus its operator did not author.

  Known limitation, recorded because it bounds what that run proves: the
  validation delivered the audit protocol to the sub-agents as a file they
  read, not as their system prompt. A registered `intent-auditor` subagent
  type carries "rewrite the prose in place" with more force than a file does.
  The constraint has not been tested under that delivery.

### Whole-repo hygiene

- `uv run ve validate` exits zero.
- `uv run pytest tests/` passes.
- `ve plugin render` is re-run and the rendered `skills/audit-corpus/SKILL.md`
  is committed alongside its template.

## Implementation notes

Prior art to read before planning:

- `skills/audit-intent/SKILL.md` — the wave-based fan-out pattern, the
  INCONSISTENCIES entry format, and the veto rule.
- `agents/intent-auditor.md` — the per-chunk audit protocol this skill
  delegates to.
- `src/cluster_analysis.py` — `cluster_chunks` (TF-IDF), `get_chunk_clusters`
  (prefix clusters), `check_cluster_size`.
- `src/chunks.py` — `find_overlapping_chunks`, `compute_symbolic_overlap`.
- `src/cli/chunk.py` — `cluster`, `overlap`, `cluster_list_cmd`; where
  `partition` will live.
- `src/plugin_render.py` — how a `skills/*.md.jinja2` template becomes
  `skills/<name>/SKILL.md`.

Naming: the skill is `audit-corpus`, pairing with the existing `audit-intent`.
The CLI subcommand is `ve chunk partition` — `cluster` and `cluster-list` are
taken and mean narrower things.

## Rejected Ideas

### An LLM classifier agent as the dispatch front door

The obvious shape is: one agent reads the corpus, classifies chunks by area of
interest, and dispatches each group to a sub-agent. Rejected on three grounds.

It does not fit. A thousand-chunk corpus does not fit in one agent's context, so
the classifier becomes its own recursive fan-out problem — partitioning in order
to partition.

It does not converge. LLM classification is not reproducible, so successive runs
reshuffle clusters and findings churn between runs instead of the corpus getting
measurably cleaner.

It re-derives what VE already records. `code_paths`, `code_references`,
`subsystems`, `narrative`, and `depends_on` are exactly the "area of interest"
signal, already written down, and VE already carries both the code-overlap and
TF-IDF clustering implementations. Judgment is spent inside a cluster — "is this
genuine redundancy or complementary work?" — where a heuristic genuinely cannot
answer and an LLM can.

### Subsuming audit-intent into the new skill

Rejected: `audit-intent` is a migration with a terminal state (a corpus
rewritten to the present-tense standard), while `audit-corpus` is a recurring
report with no terminal state. Merging them would give a destructive one-time
operation the same entry point as a safe repeatable one.

### Auto-fixing redundancy findings

Rejected: superseding or merging chunks destroys intent records, and whether two
overlapping chunks are redundant or deliberately co-owning (COMPOSITE) is a
judgment the operator has to make. Even the narrower "auto-fix only the
mechanically unambiguous" option was declined, to keep the skill safe to run
against a corpus the operator did not author.

### Computing the partition in the skill's bash instead of the CLI

Rejected: the partition logic would live in prose, could not be unit-tested, and
would drift from `ve chunk cluster`'s existing similarity math. A CLI command is
testable, reproducible, and reusable — the orchestrator's conflict oracle
(`src/orchestrator/oracle.py`) needs the same overlap relation.