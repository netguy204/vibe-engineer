# Implementation Plan

## Approach

The audit is a fan-out / collect / commit pipeline. The implementing (parent) agent does enumeration, partitioning, sub-agent dispatch, result collection, verification, and commit. Sub-agents do the per-chunk work in parallel and write directly to the working tree (in-place rewrites + new files in `docs/trunk/INCONSISTENCIES/`).

**Why fan out at all:** an exhaustive sweep of every ACTIVE chunk in `docs/chunks/` is many chunks (currently ~150+). Sequential audit would be slow; reading + reasoning per chunk is the long pole, and each chunk is independent of every other. Five-per-sub-agent gives each sub-agent enough chunks to amortize startup but few enough that any single sub-agent's context stays focused.

**Why sub-agents write directly to the working tree:** the inconsistency log is concurrency-safe by design (one file per entry, microsecond-precision filenames). The tense rewrites are per-chunk so different sub-agents can't conflict on the same file. There's no shared mutable state for sub-agents to fight over. The parent agent doesn't need to merge sub-agent outputs; it just commits whatever the working tree has accumulated.

**What the parent commits:** one commit per logical unit of work — one for tense rewrites (potentially batched if the sub-agents produce a lot), one for inconsistency-log additions. Fine-grained per-chunk commits aren't useful here because the audit is a single coordinated pass.

## Subsystem Considerations

- **`docs/subsystems/workflow_artifacts`** (STABLE): The audit USES the workflow_artifacts subsystem — it reads chunk frontmatter and prose, writes back tense-corrected prose. No structural changes to artifacts themselves.

No other subsystems involved. No new subsystems emerge from this work; the inconsistency log is too project-specific to count as a cross-cutting pattern (yet).

## Sequence

### Step 1: Enumerate ACTIVE chunks

```bash
uv run ve chunk list --status ACTIVE
```

Capture the list. Verify the two anchor cases are present: `orch_activate_on_inject` and `respect_future_intent`. If either is missing, stop and surface — the audit's anchor cases must be in scope.

Strip `intent_principles` and any other chunks already touched by this narrative from the list (they shouldn't appear in the audit, but if they do, the audit shouldn't rewrite work this session just produced).

### Step 2: Partition into batches of 5

Split the ACTIVE chunk list into groups of 5. The last group may be smaller. Record the partition (chunk → sub-agent index) so the parent can reconstruct who handled what when results return.

### Step 3: Define the sub-agent prompt template

Each sub-agent gets a self-contained prompt with:

1. **Scope** — the 5 chunk names assigned to this sub-agent (full paths under `docs/chunks/`).
2. **Detection criteria** —
   - Retrospective framing tells: `Currently,`, `was`, `we added`, `this chunk fixes`, `this chunk adds`, `the fix:`, `will change to`. Case-insensitive grep.
   - Over-claimed scope tells: any `code_references[].status: partial`; `implements:` text containing `does NOT implement`, `partial`, `only Step N of M`, `TODO`, `not yet`; success-criteria list count meaningfully exceeding code_references count.
3. **Action rules** —
   - Retrospective framing → rewrite the prose **in place** to present tense. **Do not change the chunk's intent.** Only the tense and framing change. If the rewrite would alter the goal's claim, leave the prose alone and write an inconsistency entry instead, explaining why a safe rewrite isn't possible.
   - Over-claimed scope → write an entry to `docs/trunk/INCONSISTENCIES/` per its README. Do not revise the goal. Do not finish the implementation.
4. **Filename convention** for inconsistency entries:
   ```
   YYYYMMDD_HHMMSS_microseconds_<chunk_name>_<failure_mode>.md
   ```
   Use `python3 -c "from datetime import datetime; print(datetime.now().strftime('%Y%m%d_%H%M%S_%f'))"` to generate the timestamp. Slug suggestion: `<chunk_name>_<failure_mode>` (e.g., `respect_future_intent_overclaimed`). Chunk name + failure mode is unique per finding.
5. **What to return** — a short structured summary per chunk: `{chunk_name, action_taken: rewrote|logged|skipped, evidence: <one-line>, entry_filename: <if logged>}`. Plain markdown is fine.
6. **Pointer to the inconsistency log README** so the sub-agent has the entry format reference.

### Step 4: Spawn sub-agents in parallel

Launch all sub-agents in a single message via the Agent tool, subagent_type `general-purpose` (needs Edit + Write access for inline rewrites and new entries; Explore is read-only). Run in the foreground — the parent needs the summaries before commit.

### Step 5: Collect summaries and verify anchor coverage

When sub-agents return, gather the structured summaries. Verify:
- `orch_activate_on_inject` shows `action_taken: rewrote` (the leading `Currently,` should have been rewritten).
- `respect_future_intent` shows `action_taken: logged` with an `entry_filename` pointing at a new file in `docs/trunk/INCONSISTENCIES/`.

If either anchor case isn't handled correctly, surface to the operator — the detection logic in the sub-agent prompt may need tightening before re-running the affected batch.

### Step 6: Verify the working tree

Inspect the working tree:
- Tense rewrites should be limited to prose changes inside `docs/chunks/*/GOAL.md`. No success criteria, code_paths, code_references, or other frontmatter fields should have moved. Diff each rewritten chunk against `HEAD` and skim — flag any rewrite that touches structured fields.
- Inconsistency entries should be net-new files in `docs/trunk/INCONSISTENCIES/`, each conforming to the README's frontmatter schema.

### Step 7: Run verification

```bash
uv run ve init
uv run pytest tests/
```

Both should pass cleanly. If a test breaks, the rewrite went beyond grammar — investigate before committing.

### Step 8: Commit

Two commits:

1. `audit: rewrite retrospective framing in N ACTIVE chunks` — staging the modified `docs/chunks/*/GOAL.md` files.
2. `audit: log N intent-vs-code inconsistencies` — staging the new entries in `docs/trunk/INCONSISTENCIES/`.

If either set is empty, skip that commit.

### Step 9: Produce the parent-level summary

Print a final report:
- Number of ACTIVE chunks audited.
- Number of tense rewrites applied (chunks).
- Number of inconsistency entries written (with filenames listed).
- Any sub-agent escalations or skips.
- Pointer to the inconsistency log for operator triage.

## Risks and Open Questions

- **Detector false positives.** A chunk's prose may use `was` or `the fix:` in a context that's already present-tense (e.g., describing a historical event the current system records). Sub-agents need to apply judgment — the rule is "would changing this to present tense make it false?" not "does this string appear?" Risk is wasted effort or unwanted rewrites; mitigation is the "leave alone + log" escape hatch.
- **Detector false negatives.** Chunks with subtle retrospective framing (no obvious tells) may slip through. The audit can be re-run with sharper detectors later; this run isn't expected to be comprehensive against subtle cases.
- **Sub-agent variance in rewrite quality.** Different sub-agents may produce stylistically different rewrites. Acceptable for a first pass — the goal is to remove lies, not to achieve uniform prose. If quality varies wildly, a follow-up polish pass is cheap.
- **Concurrency safety on inconsistency entries.** The README documents microsecond-precision timestamps. Sub-agents writing entries at near-identical times *could* collide if both call `datetime.now()` within the same microsecond and pick the same slug. Slug includes chunk name, which is unique per chunk, so two sub-agents writing for different chunks can't collide. Two entries about the same chunk (one per failure mode) include the failure_mode in the slug. Effectively zero collision risk in practice.
- **Working tree contamination.** Sub-agents might accidentally modify files outside their scope. Mitigation: the parent reviews `git status` before committing; anything unexpected gets investigated.
- **`intent_principles` and `respect_future_intent` are the only known anchors.** If the detectors run and find *only* the anchors with no other hits across 150+ chunks, that's suspicious — most likely a detector bug. Spot-check a few random chunks manually if the count is suspiciously low.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->
