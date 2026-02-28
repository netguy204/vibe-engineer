---
status: ONGOING
trigger: "Recovering 3 chunks stuck at REVIEW phase required ~30 manual steps across multiple systems"
proposed_chunks: []
created_after: ["reviewer_log_concurrency"]
---

<!--
DO NOT DELETE THIS COMMENT until the investigation reaches a terminal status.
This documents the frontmatter schema and guides investigation workflow.

STATUS VALUES:
- ONGOING: Investigation is active; exploration and analysis in progress
- SOLVED: The investigation question has been answered. If proposed_chunks exist,
  implementation work remains—SOLVED indicates the investigation is complete, not
  that all resulting work is done.
- NOTED: Findings documented but no action required; kept for future reference
- DEFERRED: Investigation paused; may be revisited later when conditions change

TRIGGER:
- Brief description of what prompted this investigation
- Examples:
  - "Test failures in CI after dependency upgrade"
  - "User reported slow response times on dashboard"
  - "Exploring whether GraphQL would simplify our API"
- The trigger naturally captures whether this is an issue (problem to solve)
  or a concept (opportunity to explore)

PROPOSED_CHUNKS:
- Starts empty; entries are added if investigation reveals actionable work
- Each entry records a chunk prompt for work that should be done
- Format: list of {prompt, chunk_directory, depends_on} where:
  - prompt: The proposed chunk prompt text
  - chunk_directory: Populated when/if the chunk is actually created via /chunk-create
  - depends_on: Optional array of integer indices expressing implementation dependencies.

    SEMANTICS (null vs empty distinction):
    | Value           | Meaning                                 | Oracle behavior |
    |-----------------|----------------------------------------|-----------------|
    | omitted/null    | "I don't know dependencies for this"  | Consult oracle  |
    | []              | "Explicitly has no dependencies"       | Bypass oracle   |
    | [0, 2]          | "Depends on prompts at indices 0 & 2"  | Bypass oracle   |

    - Indices are zero-based and reference other prompts in this same array
    - At chunk-create time, index references are translated to chunk directory names
    - Use `[]` when you've analyzed the chunks and determined they're independent
    - Omit the field when you don't have enough context to determine dependencies
- Unlike narrative chunks (which are planned upfront), these emerge from investigation findings
-->

## Trigger

Three orchestrator chunks (`orch_review_approve_bypass`, `orch_merge_rebase_retry`, `orch_rename_propagation`) got stuck at NEEDS_ATTENTION due to a missing `ReviewToolDecision` import in `scheduler.py`. The bug had been active since Feb 8, silently failing every chunk that reached the REVIEW phase.

Recovery required a long, error-prone manual process:
1. Diagnose the root cause (missing import)
2. Fix the code bug and restart the orchestrator
3. Discover that "merged" commits on main only contained docs, not implementation
4. Recover implementation branches from deleted branch refs via `git reflog`
5. Merge each branch to main (one had conflicts requiring manual resolution)
6. Fix stray conflict markers that were accidentally committed
7. Manually run chunk-complete on each, including populating code references
8. Restart the orchestrator again to pick up schema migrations

Several missteps along the way (marking chunks ACTIVE prematurely, force-deleting branches that held unmerged work, stashing/conflict issues) added friction. The `/orchestrator-investigate` command helped diagnose but doesn't cover recovery automation.

## Success Criteria

- Identify which recovery steps can be automated vs which require operator judgment
- Determine whether a single `ve orch recover <chunk>` command is feasible and what it would do
- Understand what safety invariants must hold during recovery (e.g., never delete branches with unmerged work)
- Produce improved guidance for `/orchestrator-investigate` that covers full chunk recovery after early/partial merges (merge branch, set status, run chunk-complete, restart orchestrator)
- Propose concrete chunks for any automation or safety-check work identified

## Testable Hypotheses

### H1: Most recovery pain comes from the gap between work unit state and git state

- **Rationale**: The orchestrator tracks work units in SQLite and branches in git independently. When a work unit is marked DONE or deleted, the branch may still hold unmerged implementation. Today's incident: we deleted work units and force-deleted branches before verifying the code was on main — losing implementation that had to be recovered from reflog.
- **Test**: Audit the orchestrator's finalization and work-unit-delete paths to identify where state divergence can occur. Map each code path to whether it verifies branch merge status before cleanup.
- **Status**: UNTESTED

### H2: A pre-delete safety check on branches would prevent the worst failure mode

- **Rationale**: The single most dangerous moment in today's recovery was `git branch -D` on branches with unmerged implementation. A check that compares the branch diff against main before deletion would have flagged the problem immediately.
- **Test**: Prototype a `ve orch work-unit delete` pre-check that refuses to delete a work unit if its orch branch has commits not reachable from main. Evaluate false-positive rate.
- **Status**: UNTESTED

### H3: The REVIEW phase failure needs a graceful retry path beyond NEEDS_ATTENTION

- **Rationale**: When a code bug (like the missing import) causes the same failure across all REVIEW-phase chunks, NEEDS_ATTENTION is a dead end — the operator must fix the code, restart, and manually recover each chunk. The orchestrator could detect "same error across N chunks" and offer batch retry after the fix.
- **Test**: Review the NEEDS_ATTENTION → resolution flow. Determine if `ve orch work-unit status <chunk> READY` is sufficient to retry, or if worktree/session state also needs reset.
- **Status**: UNTESTED

### H4: The `/orchestrator-investigate` skill lacks guidance for partial-merge recovery

- **Rationale**: The current skill covers clean scenarios (Scenario A-E) but doesn't address the case where docs are merged to main but implementation lives only on the orch branch. Today's recovery required: merge branch → resolve conflicts → set chunk to IMPLEMENTING → run chunk-complete → commit → restart orchestrator. None of this is documented in the skill.
- **Test**: Review the current `/orchestrator-investigate` template against the actual recovery steps performed today. Identify gaps and draft a new "Scenario F: Partial merge" section.
- **Status**: UNTESTED

## Exploration Log

### 2026-02-28: Motivating incident — 3 chunks stuck at REVIEW

Missing `ReviewToolDecision` import in `scheduler.py:31` caused every chunk reaching the REVIEW phase to fail with `NameError`. Bug active since Feb 8. Three chunks were stuck: `orch_review_approve_bypass`, `orch_merge_rebase_retry`, `orch_rename_propagation`.

**Recovery timeline and missteps:**

1. Diagnosed via `/orchestrator-investigate` — identified the missing import quickly
2. Fixed the import, committed, restarted orchestrator
3. **Misstep**: Assumed chunks were code-complete because `git log` showed `feat: chunk <name>` commits on main. Marked all 3 as DONE and force-deleted branches.
4. **Discovery**: Those commits only contained docs (GOAL.md + PLAN.md). Implementation code lived only on the orch branches we just deleted.
5. **Recovery**: Recovered branch tips from `git reflog` (objects still in store), recreated branches
6. **Misstep**: Injected chunks back into orchestrator as FUTURE — they started from PLAN phase, redoing all work
7. Cancelled orchestrator work units, merged branches manually instead
8. `orch_rename_propagation` had merge conflicts in `models.py` and `state.py` (both branches added fields to same model). Resolved by keeping both fields, renumbering migrations (v14 + v15).
9. **Misstep**: Committed merge with stray `<<<<<<< HEAD` markers in two files. Had to fix in a follow-up commit.
10. Ran chunk-complete on each: populated code_references, set final status, removed comment blocks

**Key observations:**
- The orchestrator's `work-unit delete` happily deletes units with unmerged branches
- `git branch -d` warned "not fully merged" (squash merge) but `-D` was used to override — destroying the safety check
- No single command recovers a stuck chunk end-to-end
- The `/orchestrator-investigate` skill doesn't cover the "docs merged, code not merged" scenario

## Findings

<!--
GUIDANCE:

Summarize what was learned, distinguishing between what you KNOW and what you BELIEVE.

### Verified Findings

Facts established through evidence (measurements, code analysis, reproduction steps).
Each finding should reference the evidence that supports it.

Example:
- **Root cause identified**: The ImageCache singleton holds references indefinitely,
  preventing garbage collection. (Evidence: heap dump analysis, see Exploration Log 2024-01-16)

### Hypotheses/Opinions

Beliefs that haven't been fully verified, or interpretations that reasonable people
might disagree with. Be honest about uncertainty.

Example:
- Adding LRU eviction is likely the simplest fix, but we haven't verified it won't
  cause cache thrashing under our workload.
- The 100MB cache limit is a guess; actual optimal size needs load testing.

This distinction matters for decision-making. Verified findings can be acted on
with confidence. Hypotheses may need more investigation or carry accepted risk.
-->

## Proposed Chunks

<!--
GUIDANCE:

If investigation reveals work that should be done, list chunk prompts here.
These are candidates for `/chunk-create` - the investigation equivalent of a
narrative's chunks section.

Not every investigation produces chunks:
- SOLVED investigations may produce implementation chunks
- NOTED investigations typically don't produce chunks (that's why they're noted, not acted on)
- DEFERRED investigations may produce chunks later when revisited

Format:
1. **[Chunk title]**: Brief description of the work
   - Priority: High/Medium/Low
   - Dependencies: What must happen first (if any)
   - Notes: Context that would help when creating the chunk

Example:
1. **Add LRU eviction to ImageCache**: Implement configurable cache eviction to prevent
   memory leaks during batch processing.
   - Priority: High
   - Dependencies: None
   - Notes: See Exploration Log 2024-01-16 for implementation approach

Update the frontmatter `proposed_chunks` array as prompts are defined here.
When a chunk is created via `/chunk-create`, update the array entry with the
chunk_directory.
-->

## Resolution Rationale

<!--
GUIDANCE:

When marking this investigation as SOLVED, NOTED, or DEFERRED, explain why.
This captures the decision-making for future reference.

Questions to answer:
- What evidence supports this resolution?
- If SOLVED: What was the answer or solution?
- If NOTED: Why is no action warranted? What would change this assessment?
- If DEFERRED: What conditions would trigger revisiting? What's the cost of delay?

Example (SOLVED):
Root cause was identified (unbounded ImageCache) and fix is straightforward (LRU eviction).
Chunk created to implement the fix. Investigation complete.

Example (NOTED):
GraphQL migration would require significant investment (estimated 3-4 weeks) with
marginal benefits for our use case. Our REST API adequately serves current needs.
Would revisit if: (1) we add mobile clients needing flexible queries, or
(2) API versioning becomes unmanageable.

Example (DEFERRED):
Investigation blocked pending vendor response on their API rate limits. Cannot
determine feasibility of proposed integration without this information.
Expected response by 2024-02-01; will revisit then.
-->