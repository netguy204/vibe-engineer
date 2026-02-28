---
status: SOLVED
trigger: "Recovering 3 chunks stuck at REVIEW phase required ~30 manual steps across multiple systems"
proposed_chunks:
- prompt: "Change work-unit delete to check for unmerged commits before deleting branch. Use git rev-list to detect unmerged work and refuse delete if found. Change git branch -D to -d as default. Add --force flag to override."
  chunk_directory: orch_safe_branch_delete
  depends_on: []
- prompt: "Add ve orch work-unit retry command that transitions NEEDS_ATTENTION to READY with proper state reset (clear session_id, attention_reason, retry counters, verify worktree). Support batch retry-all with optional phase/error filter."
  chunk_directory: orch_retry_command
  depends_on: []
- prompt: "Add Scenarios F (partial merge - implementation on branch, docs on main) and G (systematic code bug affecting all chunks in same phase) to the orchestrator-investigate skill template. Add warning about work-unit delete vs status DONE."
  chunk_directory: orch_investigate_scenarios
  depends_on: []
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
- **Status**: VERIFIED

### H2: A pre-delete safety check on branches would prevent the worst failure mode

- **Rationale**: The single most dangerous moment in today's recovery was `git branch -D` on branches with unmerged implementation. A check that compares the branch diff against main before deletion would have flagged the problem immediately.
- **Test**: Prototype a `ve orch work-unit delete` pre-check that refuses to delete a work unit if its orch branch has commits not reachable from main. Evaluate false-positive rate.
- **Status**: VERIFIED

### H3: The REVIEW phase failure needs a graceful retry path beyond NEEDS_ATTENTION

- **Rationale**: When a code bug (like the missing import) causes the same failure across all REVIEW-phase chunks, NEEDS_ATTENTION is a dead end — the operator must fix the code, restart, and manually recover each chunk. The orchestrator could detect "same error across N chunks" and offer batch retry after the fix.
- **Test**: Review the NEEDS_ATTENTION → resolution flow. Determine if `ve orch work-unit status <chunk> READY` is sufficient to retry, or if worktree/session state also needs reset.
- **Status**: VERIFIED

### H4: The `/orchestrator-investigate` skill lacks guidance for partial-merge recovery

- **Rationale**: The current skill covers clean scenarios (Scenario A-E) but doesn't address the case where docs are merged to main but implementation lives only on the orch branch. Today's recovery required: merge branch → resolve conflicts → set chunk to IMPLEMENTING → run chunk-complete → commit → restart orchestrator. None of this is documented in the skill.
- **Test**: Review the current `/orchestrator-investigate` template against the actual recovery steps performed today. Identify gaps and draft a new "Scenario F: Partial merge" section.
- **Status**: VERIFIED

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

### Verified Findings

**F1: `work-unit delete` force-deletes branches without merge verification (HIGH severity)**

`delete_work_unit_endpoint` (api/work_units.py:246) deletes the SQLite row first (line 252), then calls `remove_worktree(chunk, remove_branch=True)` (line 267) which uses `git branch -D` (force delete) at worktree.py:666. No check on whether the branch has unmerged commits. The entire cleanup is wrapped in try/except that swallows errors. This is the exact mechanism that destroyed branches in the motivating incident.

Contrast: the normal finalization path (`finalize_work_unit` at worktree.py:1229) uses `git branch -d` (safe delete), which refuses to delete unmerged branches. The asymmetry means normal completion is safe, but manual deletion is dangerous.

**F2: NEEDS_ATTENTION → READY via generic PATCH does not reset session state**

The PATCH endpoint (api/work_units.py:157) updates only the fields provided. Setting `{"status": "READY"}` does NOT clear `session_id`, `worktree`, `attention_reason`, `api_retry_count`, or `next_retry_at`. A stale `session_id` causes the scheduler to attempt resuming a dead Claude session. Contrast with the "answer" endpoint (attention.py:155) which properly clears state.

A proper retry needs to clear: `session_id`, `attention_reason`, `api_retry_count`, `next_retry_at`, and verify `worktree` validity.

**F3: No batch retry or error pattern detection exists**

There is no mechanism to retry multiple NEEDS_ATTENTION work units at once, and no detection of common error patterns across work units. Each must be individually transitioned. When a systematic bug affects N chunks, the operator must repeat the same recovery N times.

**F4: No on-demand consistency audit between work unit state and git state**

The only consistency check is `_recover_from_crash` (scheduler.py:315) which runs at daemon startup. There is no on-demand `ve orch audit` or `ve orch health-check` command. No code checks: branches without work units, work units marked DONE with surviving branches, or work units whose code was never merged.

**F5: The `/orchestrator-investigate` skill has two scenario gaps**

- **Missing Scenario F**: "Implementation on branch, docs on main" — where main has chunk doc commits but implementation code lives only on the orch branch. The current scenarios assume either the branch needs merging (A/B) or the agent failed (C). None warn about the "partial merge illusion" where `git log` shows chunk commits that only contain docs.
- **Missing Scenario G**: "Systematic code bug affecting all chunks in same phase" — where the fix is in the VE codebase, not in any individual chunk. Current Scenario C covers individual agent failure but not framework-level bugs requiring code fix → restart → batch retry.

**F6: There are 22 distinct code paths to NEEDS_ATTENTION**

Spread across scheduler.py (18 paths), review_routing.py (3 paths), and the API layer. Most go through `_mark_needs_attention()` which sets status and reason but does NOT clear session state. This means all non-question NEEDS_ATTENTION items carry stale session state.

### Hypotheses/Opinions

- A `ve orch work-unit retry <chunk>` command that properly resets state (clear session_id, attention_reason, reset retry counters, verify worktree) would address F2 and partially address F3. Batch variant (`ve orch retry-all`) would fully address F3.
- Changing `remove_worktree` to use `git branch -d` instead of `-D` would be the simplest fix for F1, but may cause issues if the orchestrator legitimately needs to force-delete branches (e.g., abandoned work). A better approach is a pre-delete check that warns/blocks when unmerged commits exist, with a `--force` flag to override.
- A `ve orch audit` command that cross-references work unit status, branch existence, and merge status would be valuable but may be over-engineering if the simpler fixes (F1, F2) eliminate the root causes.

## Proposed Chunks

1. **Safe branch deletion on work-unit delete**: Change `delete_work_unit_endpoint` (api/work_units.py:264-270) to check for unmerged commits before deleting the branch. Use `git rev-list main..orch/<chunk> --count` to detect unmerged work. If unmerged commits exist, refuse the delete and report the unmerged commit count. Add a `--force` flag/query param to override. Also change `_remove_single_repo_worktree` (worktree.py:665) from `git branch -D` to `git branch -d` as the default, with force-delete only when explicitly requested.
   - Priority: High
   - Dependencies: None
   - Notes: Addresses F1. The normal finalization path already uses `-d` (safe); only the manual delete path uses `-D` (dangerous). This is the single highest-impact change — it would have prevented the worst part of the motivating incident.

2. **Work unit retry command with proper state reset**: Add a `ve orch work-unit retry <chunk>` CLI command and corresponding API endpoint that transitions a NEEDS_ATTENTION work unit back to READY while properly resetting stale state: clear `session_id`, `attention_reason`, `api_retry_count`, `next_retry_at`, and verify `worktree` validity. Also support `ve orch retry-all` to batch-retry all NEEDS_ATTENTION work units (optionally filtered by phase or error pattern).
   - Priority: High
   - Dependencies: None
   - Notes: Addresses F2 and F3. Currently the only retry path is the generic PATCH which doesn't clear session state, causing dead session resume attempts. The "answer" endpoint (attention.py:155) is a good model for how to properly reset state.

3. **Add Scenarios F and G to orchestrator-investigate skill**: Update `src/templates/commands/orchestrator-investigate.md.jinja2` to add two new scenarios: (F) "Implementation on branch, docs on main" covering the partial-merge illusion with full recovery steps (merge → resolve conflicts → set IMPLEMENTING → chunk-complete → commit), and (G) "Systematic code bug affecting all chunks in same phase" covering framework-level bugs requiring code fix → restart → batch retry. Also add a warning about the difference between `work-unit status DONE` (preserves branch) and `work-unit delete` (destroys branch).
   - Priority: Medium
   - Dependencies: None
   - Notes: Addresses F5. Draft scenario text is available in the exploration notes. This is a documentation-only change but high-value for operator guidance during incidents.

## Resolution Rationale

All four hypotheses verified through code analysis. The investigation identified three concrete improvement areas with clear implementation paths:

1. **Safety** (highest priority): The `work-unit delete` path force-deletes branches without merge verification — a single-line change from `-D` to `-d` plus a pre-delete check would have prevented the worst part of the incident.
2. **Recovery ergonomics**: The NEEDS_ATTENTION → READY transition via generic PATCH doesn't reset session state, making retries fail silently. A dedicated `retry` command is needed.
3. **Operator guidance**: The `/orchestrator-investigate` skill needs two new scenarios for partial-merge recovery and systematic phase failures.

Three proposed chunks capture this work. The investigation is SOLVED — the questions are answered and the implementation path is clear.