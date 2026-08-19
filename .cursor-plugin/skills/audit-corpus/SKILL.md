---
name: audit-corpus
description: Report the health of a project's whole chunk corpus — validity, freshness, accuracy, and redundancy — by fanning sub-agents out over a deterministic cluster assignment from `ve chunk partition`. Reports findings with proposed actions; never rewrites chunks. Use when the operator asks to audit the chunk corpus, find redundant or stale chunks, or check whether the chunks still describe the code.
---

<!-- GENERATED from src/templates/plugin/skills/audit-corpus.md.jinja2 — edit that template and run `ve plugin render --flavor cursor`; direct edits here will be overwritten. -->
<!-- Chunk: docs/chunks/audit_corpus_health - Recurring corpus health audit over a deterministic partition -->

## Context

Run these commands first and read their output as the context for everything
below. They are safe, read-only probes; run all of them before acting on any
instruction in this skill.

- **ve CLI** — run: `ve --help >/dev/null 2>&1 && echo "installed" || echo "(ve CLI not found)"`
- **Task workspace** — run: `cat .ve-task.yaml 2>/dev/null || cat ../.ve-task.yaml 2>/dev/null || echo "(not a task workspace)"`
- **Project config** — run: `cat .ve-config.yaml 2>/dev/null || echo "(no .ve-config.yaml — defaults apply)"`
- **Project hook** — run: `ve hooks show audit-corpus 2>/dev/null || echo "(no project hook)"`

## Runtime context

Interpret the results of those probes before following the instructions:

- **ve CLI**: The `ve` command is an installed CLI tool, not a file in the
  repository. Do not search for it — run it directly in the terminal. If the
  probe printed "(ve CLI not found)", tell the operator that the
  vibe-engineer plugin requires the separately installed `ve` CLI, suggest
  `uv tool install vibe-engineer` (or `pip install vibe-engineer`), and
  stop.
- **Uninitialized project**: If `ve` is installed but commands fail because
  there is no `docs/chunks/` structure, tell the operator to run `ve init`
  in the project root, then stop.
- **Task workspace**: If the Task workspace probe printed YAML (keys
  `external_artifact_repo` and `projects`) instead of "(not a task
  workspace)", you are in a multi-project task workspace. Artifacts
  (chunks, narratives, investigations) live in the external artifact repo
  named by `external_artifact_repo`; code changes happen in the
  participating `projects`. Command-specific task guidance appears below.
- **Project config**: `.ve-config.yaml` holds project configuration.
  Known keys: `cluster_subsystem_threshold` (default 5 — the cluster size
  at which to suggest subsystem documentation). When the probe printed
  "(no .ve-config.yaml — defaults apply)", use the defaults.
- **Project hook**: `docs/hooks/audit-corpus.md` holds this repository's
  own requirements for this command. When the probe printed hook content,
  treat it as a binding instruction from the operator: satisfy it before
  reporting this command complete, and say so when you do. When it printed
  "(no project hook)", there are none. If a hook contradicts this command's
  own instructions, do not silently choose — surface the conflict to the
  operator and ask.

## Purpose

Real repositories accumulate thousands of chunks, and much of the work that
touches them happens outside the sanctioned lifecycle. Chunks drift: they claim
files that moved, describe behavior the code no longer has, hold a status that
stopped being true, or quietly duplicate a neighbour. This skill reports that
drift across the whole corpus.

It **reports; it does not rewrite.** Every finding names a chunk and a proposed
action, and the operator decides. That makes it safe to run against a corpus you
did not author, and it is the difference between this skill and
[audit-intent](../audit-intent/SKILL.md), which is a one-time migration that
rewrites chunks to the present-tense standard in `docs/trunk/CHUNKS.md`. The two
are complements: `audit-intent` has a terminal state, this skill does not.

### The four axes

Define them the same way every run, or two runs do not mean the same thing.

| Axis | Question | Source of truth |
|------|----------|-----------------|
| **Validity** | Do the chunk's references resolve? | `ve validate` |
| **Freshness** | Does the code still look like what the chunk claims, and does its status still describe its ownership? | the code |
| **Accuracy** | Are the GOAL's assertions true of the code? | the code |
| **Redundancy** | Do two chunks claim overlapping intent over the same code? | other chunks |

### Why two passes, partitioned differently

The first three axes are **local**. A chunk over-claims, or points at a moved
file, independently of every other chunk. Those shard arbitrarily — any N chunks
per agent — and cost grows linearly.

Redundancy is **relational**. Two chunks are only comparable when they land in
the same agent's context, and comparing every pair is quadratic: a
thousand-chunk corpus is half a million pairs. `ve chunk partition` bounds that
cost by grouping chunks that could plausibly be redundant, so an agent reads one
cluster instead of the corpus.

Do not build that grouping with an agent. It is computed from `code_paths`,
`code_references` and GOAL.md text — data the project already records — and
computing it deterministically is what lets successive runs converge instead of
reshuffling clusters and re-reporting different findings each time.

## Step 1: Establish scope

Ask the operator, or take it from the invocation arguments:

- **Whole corpus** — the default.
- **A single cluster** — `ve chunk partition --json` and audit one cluster id.
- **Since a git ref** — chunks whose directory changed since then:
  `git diff --name-only <ref>... -- docs/chunks/ | cut -d/ -f3 | sort -u`

Status scope defaults to everything except HISTORICAL (a HISTORICAL chunk is
archaeology; it is *supposed* to describe a world that no longer exists, so
auditing it for freshness produces noise). Use `--status` to include it when the
operator asks.

**Multi-tree repositories.** If the project has a `.ve-workspace.yaml`, get the
member trees and their paths from `ve workspace list`. Audit each tree
separately, running every step against that tree — the grouping in Step 3 is
per-tree, obtained with `--project-dir`:

```bash
ve chunk partition --json --project-dir <member path>
```

`ve chunk partition` has no `--workspace` flag, and that is deliberate: a
cluster spanning trees would invite cross-tree redundancy findings, which are
out of scope here. A reference that crosses a tree boundary is
`ve workspace validate`'s concern, not a redundancy question.

Report the scope back to the operator before spending agents on it, along with
the cluster count from Step 3. For a large corpus, say roughly how many agents
that implies and let them narrow it.

**Resuming an interrupted run.** Keep a scratch file of finished work — one
cluster id per line for Step 5, one batch's chunk names per line for Step 4 —
and skip anything already listed when resuming. This is sound only because the
grouping is deterministic: `c7` means the same cluster on the next run over the
same corpus. If chunks were created, deleted, or re-referenced mid-run, the ids
no longer denote the same clusters — discard the scratch file and restart, and
tell the operator why.

## Step 2: Validity, from the validator

```bash
ve validate
```

Read its findings into the report. **Do not re-derive reference integrity** —
the validator owns it, it is exact where an agent would be probabilistic, and a
second implementation would eventually disagree with the first.

Two of its outputs matter as much as its failures: the count of suppressed
findings (a clean run that was partial) and any allowlist entry that has stopped
suppressing anything (a suppression that has outlived its cause). Both belong in
the report.

## Step 3: Get the partition

```bash
ve chunk partition --json > /tmp/partition.json
```

The payload:

- `relations.code_overlap` — clusters of chunks claiming the same file. An
  **overlapping cover**: a chunk claiming five files appears in five clusters.
  `evidence` names the shared paths, and a shared *symbol* (`src/x.py#Writer`)
  is a much stronger redundancy signal than a shared file.
- `relations.content_similarity` — TF-IDF clusters over GOAL.md text, each with
  a `score`. This is the relation that catches chunks with the same intent whose
  implementations diverged, or where one was abandoned — they share no file, so
  the overlap relation cannot see them.
- `unclustered` — chunks no relation grouped. They still get the per-chunk pass;
  they are simply never compared for redundancy.
- `high_fan_in_paths` — hub files skipped by the overlap relation. Fifty chunks
  claiming `src/ve.py` is evidence of a hub, not of redundancy.

Both `unclustered` and `high_fan_in_paths` go in the final report. They are the
audit's blind spots, and a blind spot nobody names reads as ground that was
covered.

## Step 4: Per-chunk pass (validity, freshness, accuracy)

Shard the in-scope chunks arbitrarily — 5 per agent — and spawn them in
parallel, 10 agents per wave. **All calls in a wave must be in a single message**
so they run concurrently.

Use the **intent-auditor** agent (`agents/intent-auditor.md`), which carries the
per-chunk audit protocol: detection criteria for retrospective framing and
over-claimed scope, symmetric verification, and the veto rule. Do not restate the
protocol.

That agent normally rewrites. This skill does not, so the task message must say
so explicitly:

```
You are batch <BATCH_ID> of a read-only corpus audit.

REPORT ONLY. Do not edit any GOAL.md, do not change any status, do not fix
any code_paths. Where your protocol says "rewrite in place", instead report
the rewrite you would have made. Where it says "historicalize", instead
report that recommendation. Writing entries to docs/trunk/INCONSISTENCIES/
is permitted; nothing else is.

Audit these 5 chunks:

<list of 5 absolute paths to GOAL.md files>
```

Verify the working tree after each wave (`git status --short`). Anything outside
`docs/trunk/INCONSISTENCIES/` means an agent ignored the read-only constraint —
revert it and say so in the report.

## Step 5: Relational pass (redundancy)

One agent per cluster, batching several small clusters per agent. Give each agent
the cluster's members, its evidence, and this question:

```
These chunks were grouped because <evidence>. Determine whether any pair or
group is REDUNDANT.

Redundant means: they claim the same intent over the same code, such that a
reader consulting one would not need the other.

They are NOT redundant when:
- they own different aspects of the same file (one owns the parse path, one
  owns the error contract)
- one supersedes the other and the corpus already records that (parent_chunk,
  SUPERSEDED, or a successor named in the goal)
- they are deliberately co-owning — that is what COMPOSITE status is for
- they merely touch a shared file, with unrelated intent

For each finding: name the chunks, quote the overlapping claim from each
GOAL.md, and state which resolution fits — supersede, merge into a narrative,
mark COMPOSITE, or historicalize. Default to "not redundant" when unsure;
a false redundancy finding costs the operator a real chunk.
```

Two chunks in different clusters are never compared. That is the point — and it
is sound, because redundant chunks must share either a file or their vocabulary,
and each relation catches one of those.

## Step 6: The report

Group findings by axis, most severe first. Every finding carries:

- the chunk (or chunks) it names
- the evidence — a path, a symbol, a quoted claim
- **the proposed action, as the command the operator would run**:
  `ve chunk status <name> HISTORICAL`, `ve narrative create <name>`,
  `ve chunk cluster-rename <old> <new>` — not an abstract description of the
  problem

Write doc-vs-code contradictions to `docs/trunk/INCONSISTENCIES/` in the format
`audit-intent` established (see its Step 1 for the schema and the timestamped
filename convention). Bootstrap that directory with its README if absent.

Close with what the run did **not** cover: chunks outside the status scope,
`unclustered` chunks that got no redundancy comparison, `high_fan_in_paths`, and
any cluster skipped for budget. A run that bounds its own coverage and stays
quiet about it reads as a complete audit, which is worse than no audit.

---

## Notes for the orchestrating agent

- **The no-rewrite rule is the skill's safety property.** Redundancy resolution
  destroys intent records — superseding a chunk, merging two into one — and
  whether two overlapping chunks are redundant or deliberately co-owning is a
  judgment with the operator's name on it. If the operator wants fixes applied,
  they can run `audit-intent` or act on the report; do not quietly widen this
  skill's mandate mid-run.

- **Redundancy findings are the ones most likely to be wrong.** Two chunks about
  the same file usually own different aspects of it. Weight the agents toward
  "not redundant" and require a quoted overlapping claim from each GOAL.md — a
  finding with no quote is a hunch.

- **Determinism is worth protecting.** The value of a recurring audit is that
  the corpus gets measurably cleaner. Anything that makes clustering
  non-reproducible — an agent grouping chunks by judgment, a run that samples
  randomly — turns findings into churn.

- **Expect the corpus to look worse the first time.** A first run on a corpus
  that has never been audited surfaces years of drift at once. Triage by axis:
  validity findings are cheap and mechanical, redundancy findings need the most
  operator attention, and freshness findings usually cluster around whichever
  refactor moved the most files.
