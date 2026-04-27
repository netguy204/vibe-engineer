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
   - **Retrospective framing tells** (case-insensitive grep): `Currently,`, `was`, `we added`, `this chunk fixes`, `this chunk adds`, `the fix:`, `will change to`. Plus markdown header forms: `^#+\s+The\s+fix\b`, `^#+\s+The\s+bug\b`, `^#+\s+The\s+problem\b`. The header forms are soft tells — they don't always indicate stale framing, but combined with present-state body content they often signal the prose is narrating a transition rather than describing the system.
   - **Over-claimed scope tells**: any `code_references[].status: partial`; `implements:` text containing `does NOT implement`, `partial`, `only Step N of M`, `TODO`, `not yet`; success-criteria list count meaningfully exceeding `code_references` count after **filtering generic criteria**. Generic criteria — `tests pass`, `existing X remains correct`, `lint passes`, `no regressions` — are not real implementation claims and inflate the ratio. Subtract them before comparing.

3. **Action rules** —
   - **Retrospective framing → rewrite in place** to present tense, system-centric framing. Prefer `The schema template now distinguishes X from Y` over `This chunk extends the schema template to add X vs Y`. The goal is a description of the system, not a description of the chunk. Do not change the chunk's intent — only tense and framing change. Success criteria and architectural claims are off-limits.
   - **Over-claimed scope → write inconsistency entry, log only**. Do not revise the goal. Do not finish the implementation.
   - **Broken `code_paths` references** (file in `code_paths` doesn't exist, but a clearly-correct alternative is identifiable — same directory, name similarity, content match) → **fix in place**. This is a metadata fix, not an intent change. If the correct target isn't unambiguous, leave it and write an inconsistency entry instead.
   - **No enduring intent → historicalize.** Set the chunk's status to HISTORICAL when it no longer owns intent that governs current code. **Do not edit the goal text** — HISTORICAL semantically means "archaeology, not canon", and the goal stays as-is to preserve the original intent record. Don't delete the chunk; let a future cleanup pass handle deletion. Two patterns trigger historicalization (high bar — every signal must hold for one pattern):

     **Pattern A — bug-fix-only chunk:**
     - (a) Goal opens with `Fix X` / `Resolve Y` framing or describes a one-time defect.
     - (b) Success criteria are all "the bug no longer reproduces" style — no architectural decisions, constraints, or contracts.
     - (c) Code references are tactical (one or two functions/lines, not establishing a pattern).
     - (d) `bug_type: implementation` if the field is still present.

     **Pattern B — intent fully superseded:**
     - (a) Veto rule fired on this chunk (multi-axis drift confirmed against current code).
     - (b) The code sites referenced by the chunk carry 3+ successor chunk names in `# Chunk:` backreferences (the live contract is owned elsewhere).
     - (c) **For every load-bearing claim in the goal, the claim is either contradicted by current code OR owned by a named successor chunk / subsystem.** No claim is uniquely held by this chunk. This is the load-bearing signal — if any claim is genuinely unique to this chunk and still true, do NOT historicalize; log instead.
     - (d) Nothing about the architecture would become unclear if this chunk's content disappeared from `docs/chunks/`.

     Miss any signal in either pattern → default to safer action (log scope concern, leave status alone). When historicalizing, also scan `docs/trunk/INCONSISTENCIES/` for open entries naming this chunk; mark them `status: resolved` with `resolved_by: "audit batch N — historicalized"`.
   - **Cross-artifact inconsistencies** discovered during the audit (mismatches NOT inside the chunk being audited — e.g., README contradicting a workflow file, two skill templates disagreeing) → **write an inconsistency entry**. Use slug `<area>_<short-description>` (e.g., `pip_publish_readme_workflow_mismatch`). The audit's job is to capture truth across the project, not just per-chunk; if you tripped over a real inconsistency while verifying, log it.

4. **Veto rule (load-bearing)** — If over-claimed scope is detected, **do not rewrite the prose for tense, even if retrospective framing is also detected.** The two failure modes interact: a chunk that over-claims has no truthful present-tense form available, so any rewrite would substitute one false claim for another. When the veto fires: write the inconsistency entry, leave the GOAL.md prose untouched, set `action_taken: logged` (not `both`), note the veto in the summary.

5. **Symmetric verification (load-bearing)** — Before rewriting any prose to a present-tense claim, **verify the post-state actually exists in the named source files**. Read the `code_references` and grep the implementations. Also **`ls` every entry in `code_paths`** to catch broken file references (which become fix-in-place candidates per Action rule above). The veto rule catches *declared* over-claim (`status: partial`); this verification catches *undeclared* over-claim (chunk author was honest about success criteria but the code is stale or incomplete relative to what the prose asserts). If the named symbols don't exist or don't behave as described, treat as over-claim: log instead of rewrite.

6. **Filename convention** for inconsistency entries:
   ```
   YYYYMMDD_HHMMSS_microseconds_<chunk_name>_<failure_mode>.md
   ```
   Generate the timestamp with `python3 -c "from datetime import datetime; print(datetime.now().strftime('%Y%m%d_%H%M%S_%f'))"`. Slug: `<chunk_name>_<failure_mode>` (e.g., `respect_future_intent_overclaimed`). Chunk name + failure mode is unique per finding.

7. **What to return** — a short structured summary per chunk:
   ```
   ## <chunk_name>
   - action_taken: rewrote | logged | historicalized | clean | skipped
   - evidence: <one-line>
   - entry_filename: <if logged>
   - veto_fired: true | false
   - verification_did: <one-line — what you did to verify the post-state exists, and what you found>
   - codepath_fixes: <list of broken→fixed code_paths entries, if any>
   - notes: <judgment calls, edge cases>
   ```
   Plus an overall summary: counts per action, vetoes fired, cross-artifact inconsistencies logged, suggestions for the parent audit's logic.

8. **Pointer to the inconsistency log README** at `docs/trunk/INCONSISTENCIES/README.md` so the sub-agent has the entry format reference.

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
- **Veto accuracy depends on chunk authors being honest in `code_references`.** The veto rule fires on declared over-claim (`status: partial`, "does NOT implement" admissions). A chunk that quietly over-claims without flagging it in metadata escapes the veto — only the symmetric verification step (Step 5 of the sub-agent prompt) catches that case. The verification step is therefore not optional; it's the safety net for un-self-aware over-claim.
- **Imperative-voice prose in template/schema-additions chunks.** Some chunks (e.g., `wiki_snapshot_vs_log`) have bodies written as planning prose ("Content to add: ...") that's neither retrospective nor present-tense in the system-description sense. Sub-agents should leave such bodies alone unless an explicit chunk-centric tell appears in them; the chunk-centric "Relationship to Parent" sentence is fair game. Escalate to the operator if a chunk has substantial planning-prose bodies that feel mis-fit for ACTIVE status — the chunk template may need revision.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->
