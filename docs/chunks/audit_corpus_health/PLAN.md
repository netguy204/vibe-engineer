

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Two deliverables, built in that order because the second consumes the first:

1. **`ve chunk partition`** — a CLI command emitting the corpus's cluster
   assignment under two relations, as JSON. It is the deterministic substrate
   the skill fans out over.
2. **`audit-corpus`** — a plugin skill template that consumes that JSON, shards
   a per-chunk pass arbitrarily, and runs a relational pass one agent per
   cluster.

### The partition command

The command lives in `src/cli/chunk.py` beside `cluster` and `overlap`, with the
computation in `src/cluster_analysis.py` (the `cluster_analysis` subsystem owns
clustering; see Subsystem Considerations).

**Content-similarity relation** reuses `cluster_analysis.cluster_chunks`
unchanged. It already returns `ClusterResult(clusters, unclustered,
cluster_themes)` over TF-IDF cosine similarity with agglomerative clustering.
The only new work is emitting it as JSON and letting the caller widen the status
filter beyond ACTIVE (`cluster_chunks` accepts an explicit `chunk_ids` list, so
the CLI passes the filtered set in).

**Code-overlap relation is new code, and deliberately not
`Chunks.find_overlapping_chunks`.** That method answers a different question:
for one target chunk, which ACTIVE *ancestors* share a reference. It is
directional (ancestors only, via `artifact_index.get_ancestors`), status-locked
to ACTIVE, and reads `code_references` only. A corpus partition needs an
undirected relation over every chunk in scope, and calling the existing method
once per chunk would be O(n²) ancestor lookups on top of O(n²) reference
comparisons — precisely the cost the partition exists to avoid.

Instead, build an inverted index once:

```
file_path -> {chunk names that reference it}
```

drawing from both `code_paths` and `code_references` (the ref's file portion,
via `parse_reference(qualify_ref(ref, "."))`). Each file with 2+ chunks is an
edge set; union-find over those edges yields connected components in
O(total_refs · α). The file path that produced each edge is retained as the
cluster's `evidence`, which is what makes a finding legible to a reader
("these 7 chunks all touch `src/plugin_render.py`").

Symbol-level precision is preserved where it matters: within a component,
`compute_symbolic_overlap` distinguishes chunks that touch the same *symbol*
from chunks that merely touch the same *file*. That distinction is reported as
`evidence` granularity, not used to split components — two chunks touching
different symbols in one file are still worth comparing for redundancy.

**Determinism** is a success criterion, so every collection that reaches output
is sorted: cluster members sorted by name, clusters sorted by their first
member, evidence paths sorted. Cluster ids are positional (`c0`, `c1`, …) after
that sort, so they are stable across runs on an unchanged corpus.

Corpus measurement taken while planning, which sets expectations for the
relation's reach: of this repository's 454 chunks, 23 have neither `code_paths`
nor `code_references` (17 FUTURE, 2 HISTORICAL, 2 ACTIVE, 1 IMPLEMENTING, 1
EXTERNAL). Code overlap covers ~95% here. On a drifted corpus that fraction
falls, and the design degrades gracefully rather than failing: a chunk with no
references is simply absent from the code-overlap relation and reachable only
through content similarity. The JSON reports such chunks explicitly rather than
letting them vanish — silent omission would read as "audited everything".

### The skill

`src/templates/plugin/skills/audit-corpus.md.jinja2`, following the established
template shape: `idioms.frontmatter(...)`, `idioms.generated_marker(...)`,
`idioms.canonical_preamble("audit-corpus")`, then the skill body. It renders to
`skills/audit-corpus/SKILL.md` via `ve plugin render` — `plugin_render` globs
the template directory, so no registration is needed there, but
`hooks.KNOWN_EVENTS` is a hand-maintained literal that
`tests/test_plugin_skills.py::TestHookEventVocabulary` pins to the skill
directory listing, so the new name must be added there or the suite fails.

The skill delegates per-chunk accuracy to the existing `intent-auditor` agent
rather than restating its protocol, invoked in a report-only mode. The agent
currently *rewrites* chunks; the skill must state the read-only constraint in
the task message it sends, since the agent definition itself is shared with
`audit-intent` and must not change behavior for that caller.

### Testing

Per `docs/trunk/TESTING_PHILOSOPHY.md`, the partition command is behavioral code
and gets tests first. The tests trace to GOAL success criteria:

- Two chunks sharing a `code_paths` entry land in one code-overlap cluster, and
  the shared path appears as evidence. (→ "assigns every chunk to clusters under
  two independent relations")
- Two chunks sharing nothing land in different clusters.
- A chunk with neither `code_paths` nor `code_references` is reported, not
  dropped. (→ "reports such chunks explicitly")
- Running the command twice on an unchanged fixture corpus produces
  byte-identical output. (→ "byte-identical cluster assignment across runs")
- Reordering the chunk directory's iteration order does not change output.
- `--status` filtering restricts the partitioned set the same way `ve chunk
  list --status` does.
- `--min-similarity` changes the content-similarity clustering and defaults
  to 0.3, matching `ve chunk cluster`.

The skill is a prose artifact; it is verified by the existing generic
invariants in `tests/test_plugin_skills.py` (which run over every
`skills/*/SKILL.md`) plus a small `TestAuditCorpusSkill` class asserting the
properties the GOAL names: the four axes appear, the two-pass structure appears,
`ve chunk partition` is the partition source, and the skill states it does not
rewrite chunks. These are structural assertions about a document, which is the
one case where structural assertions are the real thing being verified.

## Subsystem Considerations

- **docs/subsystems/cluster_analysis** (DOCUMENTED): this chunk **implements**
  part of it. The subsystem's In Scope list already covers "Cluster analysis"
  and "TF-IDF similarity"; the code-overlap relation and whole-corpus JSON
  assignment extend it. New functions in `src/cluster_analysis.py` must follow
  the subsystem's existing shape — a result dataclass plus a pure function
  taking `project_dir`, matching `ClusterResult` / `cluster_chunks`.

  The subsystem's stated intent is naming-oriented ("help operators name chunks
  for semantic alphabetical clustering"). Auditing is a second consumer of the
  same machinery. On completion, add the new `code_references` to the
  subsystem's OVERVIEW.md and widen its Intent to name both consumers — the
  subsystem is DOCUMENTED, so this is recording what is true, not a refactor.

- **docs/subsystems/workflow_artifacts**: **uses** — chunk enumeration and
  frontmatter parsing go through `Chunks`.

- **docs/subsystems/template_system**: **uses** — the skill is a Jinja2 template
  rendered by `ve plugin render`.

## Sequence

### Step 1: Failing tests for the partition relations

Add `tests/test_chunk_partition.py` with a fixture corpus built in `tmp_path`
(follow the fixture style already used in `tests/` for chunk trees). Cover:
shared-path clustering, disjoint chunks, the reference-less chunk, determinism
across two runs, and status filtering. These fail — nothing implements them yet.

### Step 2: The code-overlap relation

In `src/cluster_analysis.py`, add:

- `OverlapCluster` dataclass — `id: str`, `members: list[str]`,
  `evidence: list[str]`
- `PartitionResult` dataclass — `code_overlap: list[OverlapCluster]`,
  `content_similarity: list[SimilarityCluster]`, `unclustered: list[str]`
- `partition_chunks(project_dir, chunk_ids=None, min_similarity=0.3) -> PartitionResult`

`partition_chunks` builds the inverted index, runs union-find, sorts everything,
and calls `cluster_chunks` for the similarity half. Reference extraction reuses
`qualify_ref` / `parse_reference` from `src/chunks.py` so the partition and
`find_overlapping_chunks` agree on what a reference points at.

Add the `# Chunk: docs/chunks/audit_corpus_health` backreference at the module
symbols this chunk introduces.

### Step 3: The CLI command

In `src/cli/chunk.py`, add `@chunk.command("partition")` with `--json`,
`--min-similarity`, `--status`, the `--active`/`--future`/`--implementing`
shortcuts, and `--project-dir`. Reuse the status-parsing helper `ve chunk list`
uses rather than re-parsing status strings. Human-readable output when `--json`
is absent; JSON exactly as the GOAL's illustrative shape when present.

Step 1's tests pass at the end of this step.

### Step 4: Verify the partition against this repository

Run `uv run ve chunk partition --json` over the real 454-chunk corpus. Confirm:
it completes without pathological runtime, the reference-less chunks appear in
the reported-not-dropped list, and cluster sizes are plausible (a cluster
containing 200 chunks means the relation is too coarse and needs a
high-fan-in-path exclusion, which is a finding to record in Deviations, not to
paper over).

### Step 5: The skill template

Write `src/templates/plugin/skills/audit-corpus.md.jinja2`. Body sections:

- **Purpose** — the four axes, defined; the complement-not-replace relationship
  to `audit-intent`.
- **Step 1: scope** — whole corpus, one cluster, or chunks touched since a git
  ref; workspace enumeration via `ve chunk list --workspace`, per-tree
  partitions, cross-tree redundancy explicitly out of scope.
- **Step 2: validity** — run `ve validate`, report its findings, do not
  re-derive them.
- **Step 3: per-chunk pass** — arbitrary N-per-agent shards, `intent-auditor` in
  report-only mode.
- **Step 4: relational pass** — `ve chunk partition --json`, one agent per
  cluster, with the locality argument stated so a reader knows why the two
  passes are partitioned differently.
- **Step 5: report** — findings with a proposed action naming the command the
  operator would run; `docs/trunk/INCONSISTENCIES/` entries for doc-vs-code
  contradictions, in `audit-intent`'s established format; explicit statement of
  anything the run skipped.
- **Notes for the orchestrating agent** — the no-rewrite rule and why.

### Step 6: Register and render

Add `"audit-corpus"` to `hooks.KNOWN_EVENTS` in `src/hooks.py`. Run
`uv run ve plugin render` and commit `skills/audit-corpus/SKILL.md` alongside
the template. Confirm `git diff` shows only the intended addition.

### Step 7: Skill tests

Add `TestAuditCorpusSkill` to `tests/test_plugin_skills.py` asserting the
GOAL-named properties listed under Testing above.

### Step 8: End-to-end validation on this corpus

Run the skill against this repository's own chunks. The GOAL requires that the
run produce findings a reader can act on without re-reading the chunks. If the
findings are unactionable, that is a defect in the report format, not an
acceptable outcome — fix the template and re-run.

### Step 9: Close out

- Update `docs/subsystems/cluster_analysis/OVERVIEW.md` with the new
  `code_references` and the widened Intent.
- Populate `code_paths` / `code_references` in this chunk's GOAL.md.
- `uv run ve validate` exits zero; `uv run pytest tests/` passes.

---

**BACKREFERENCE COMMENTS**

Add `# Chunk: docs/chunks/audit_corpus_health - <what it implements>` at
`partition_chunks`, the new dataclasses, and the `partition` CLI command. The
skill template carries its backreference as an HTML comment, matching the
existing plugin skill templates.

## Dependencies

None outside the repository. `scikit-learn` is already a dependency (used by
`cluster_chunks`); the code-overlap relation adds no new library.

## Risks and Open Questions

- **A high-fan-in path could collapse the corpus into one cluster.** Files that
  many chunks touch (`src/cli/chunk.py`, `src/chunks.py`) may chain unrelated
  chunks into a single giant component through transitive union-find merges.
  Step 4 exists to detect this. If it happens, the fix is a fan-in ceiling —
  paths referenced by more than N chunks stop generating edges — recorded as a
  Deviation with the chosen N and its justification. This is the most likely
  place the plan changes.

- **`intent-auditor` is shared with `audit-intent`, which expects it to
  rewrite.** The read-only constraint must be imposed by the caller's task
  message. If that proves unreliable in Step 8, the alternative is a separate
  read-only agent definition — a real scope increase, so surface it to the
  operator rather than deciding unilaterally.

- **`EXTERNAL` appeared as a chunk status** in the corpus measurement but is not
  in the documented status taxonomy in the GOAL.md template. Unrelated to this
  chunk; noted here so it is not lost. Worth an INCONSISTENCIES entry during
  Step 8 if it is still unexplained then.

- **The end-to-end run is expensive.** Auditing 454 chunks fans out many agents.
  Step 8 may scope to a subset; if it does, the report must say what it skipped,
  and the chunk cannot claim the end-to-end criterion is met on a partial run.

## Deviations

### Step 2: connected components replaced by a per-file overlapping cover

The plan built the code-overlap relation with union-find over shared files,
yielding connected components. Step 4 measured that on this repository and it
failed as the Risks section anticipated, but worse than anticipated: **423 of
454 chunks landed in a single component.**

The plan's proposed remedy — a fan-in ceiling excluding hub paths — does not
fix it. Measured at ceilings of 5, 8, 12 and 20, the largest component was 287,
343, 372 and 414 chunks respectively. The cause is not any single hub file but
transitive chaining: A shares a file with B, B shares a *different* file with C,
and the component swallows all three. On a corpus where the median file is
claimed by 2 chunks and the p90 by 8, that chains into a giant component
regardless of where the ceiling sits. It is percolation, not a parameter.

The relation is now an overlapping **cover**: one cluster per shared file,
`{chunks that claim src/foo.py}`. A chunk claiming five files appears in five
clusters. Nothing the audit needs is lost — two chunks can only be redundant if
they claim a file in common, and that file's cluster holds them both — and each
cluster explains itself in a line. Clusters generated by different files with
identical membership collapse into one.

The fan-in ceiling is kept, for a different reason than the plan gave it. It no
longer rescues the relation; it removes clusters that carry no signal. Fifty
chunks claim `src/ve.py`; "both of these touch the CLI entry point" says nothing
about redundancy. The default is `HEALTHY_MAX_SIZE` (8), reusing the constant
`cluster_analysis` already defines as the size at which a grouping stops being
informative, and `--fan-in-ceiling` overrides it. Excluded paths are reported in
`high_fan_in_paths` rather than dropped.

Result on this corpus: 294 clusters, largest 8 members, 1060 cluster slots, 6
chunks unclustered, 58 hub files reported as skipped.

Consequence for the GOAL: the JSON shape gained `high_fan_in_paths`, and
"partition" is a loose name for the overlap half — the code and CLI help say
"cover" where precision matters. The similarity half remains a true partition.

### Step 8: end-to-end validation run on a bounded scope, inline

The plan called for running the skill against this repository's whole corpus.
That is a ~100-agent fan-out (91 per-chunk batches plus 294 overlap clusters),
and spawning it was not authorized as part of this chunk's implementation. The
report format was instead validated inline over three code-overlap clusters and
the highest-scoring similarity cluster, with the auditing role played directly
rather than by sub-agents.

That bounded run produced actionable findings on its first cluster, which is the
criterion the GOAL names:

- `scratchpad_remove_infra` is ACTIVE and its goal says *"This is pure cleanup -
  no behavioral changes, just removal of dead code paths"*. A chunk with no
  enduring intent should not hold ACTIVE ownership (CHUNKS.md principles 2 and
  4). Proposed action: `ve chunk status scratchpad_remove_infra HISTORICAL`.
- `scratchpad_revert_migrate` uses a `## Goal` heading where the current
  template uses `## Minor Goal` — template drift from an older schema.
- `scratchpad_remove_infra` and `scratchpad_docs_cleanup` both claim to complete
  the same reversion, and are correctly **not** redundant: one owns the code
  removal, the other the templates. The discrimination the relational prompt
  asks for held.

What this does not establish: behavior at fan-out scale, wave commit handling,
or whether the read-only constraint survives contact with `intent-auditor`
(Risk 2 remains open). A full-corpus run is the operator's call.

### Step 2: `ClusterResult` gained `cluster_scores`

The GOAL's illustrative JSON shows a `score` on each similarity cluster, but
`cluster_chunks` returned membership and themes only. Rather than recompute
TF-IDF in the partition (two implementations that could disagree),
`cluster_chunks` now also returns mean pairwise cosine similarity per cluster,
as an additive field defaulting to empty. Its tie-break sort also became total
(size, then first member) so cluster order no longer inherits filesystem
enumeration order — a prerequisite for the determinism criterion.
