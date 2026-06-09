---
name: audit-intent
description: Migrate the project's ACTIVE chunks to the present-tense, intent-owning standard. Audits each chunk's goal against the code it claims to govern; rewrites retrospective framing inline; logs over-claims that need operator triage; historicalizes chunks with no enduring intent. Designed for full-corpus migrations — fans out across many parallel sub-agents at 5 chunks per agent. Use when the operator asks to audit chunk intent, migrate the chunk corpus, or clean up retrospective chunk framing.
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(ve chunk list:*)
---

<!-- Chunk: docs/chunks/plugin_orch_commands - Static plugin port of audit-intent -->
<!-- Chunk: docs/chunks/plugin_subagents - Fan-out delegates to the intent-auditor plugin agent -->

## Context

- ve CLI: !`ve --help >/dev/null 2>&1 && echo "installed" || echo "(ve CLI not found)"`
- Task workspace: !`cat .ve-task.yaml 2>/dev/null || cat ../.ve-task.yaml 2>/dev/null || echo "(not a task workspace)"`
- Project config: !`cat .ve-config.yaml 2>/dev/null || echo "(no .ve-config.yaml — defaults apply)"`

## Runtime context

Interpret the context above before following the instructions:

- **ve CLI**: The `ve` command is an installed CLI tool, not a file in the
  repository. Do not search for it — run it directly via Bash. If the
  context shows "(ve CLI not found)", tell the operator that the
  vibe-engineer plugin requires the separately installed `ve` CLI, suggest
  `uv tool install vibe-engineer` (or `pip install vibe-engineer`), and
  stop.
- **Uninitialized project**: If `ve` is installed but commands fail because
  there is no `docs/chunks/` structure, tell the operator to run `ve init`
  in the project root, then stop.
- **Task workspace**: If the Task workspace context shows YAML (keys
  `external_artifact_repo` and `projects`) instead of "(not a task
  workspace)", you are in a multi-project task workspace. Artifacts
  (chunks, narratives, investigations) live in the external artifact repo
  named by `external_artifact_repo`; code changes happen in the
  participating `projects`. Command-specific task guidance appears below.
- **Project config**: `.ve-config.yaml` holds project configuration.
  Known keys: `cluster_subsystem_threshold` (default 5 — the cluster size
  at which to suggest subsystem documentation). When the context shows
  "(no .ve-config.yaml — defaults apply)", use the defaults.

## Tips

- This skill spawns parallel sub-agents (10 per wave, 5 chunks each). Use it on substantial chunk corpora.
- The skill is idempotent: clean chunks stay clean, rewritten chunks don't trigger again. Safe to re-run.

## Purpose

This skill enforces the four principles in `docs/trunk/CHUNKS.md` against the existing chunk corpus:

1. Code owns implementation; chunks own intent.
2. Chunks exist only for intent-bearing work.
3. A chunk's GOAL.md describes intent in present tense.
4. Status answers a single question — how much of the intent does this chunk own?

It performs five categories of action per chunk:

- **Rewrite tense in place** when the goal is retrospectively framed but the post-state is genuinely realized in code.
- **Log over-claims** when the goal asserts behaviors the code doesn't implement (operator triage required).
- **Fix broken `code_paths` / `code_references`** when the correct target is unambiguous (typically post-refactor drift).
- **Historicalize** chunks with no enduring intent (Pattern A: bug-fix-only; Pattern B: intent fully superseded).
- **Log cross-artifact inconsistencies** discovered along the way (template-vs-template, doc-vs-code mismatches).

## Prerequisites

Before running, verify the project has the required infrastructure. Run these checks; if any fail, stop and direct the operator to the fix.

```bash
# (1) Canonical principles doc must exist
test -f docs/trunk/CHUNKS.md || echo "MISSING: docs/trunk/CHUNKS.md — run 've init' to install."

# (2) Chunk GOAL.md files must declare COMPOSITE in their STATUS VALUES block
grep -q "COMPOSITE" docs/trunk/CHUNKS.md 2>/dev/null || \
  echo "MISSING: COMPOSITE status in docs/trunk/CHUNKS.md — upgrade ve and run 've init'."

# (3) Runtime must accept COMPOSITE as a chunk status
ve chunk list --status COMPOSITE >/dev/null 2>&1 || \
  echo "MISSING: COMPOSITE chunk status support — upgrade ve."
```

If any check reports MISSING, stop and tell the operator what's needed. Do not proceed with the audit on an unprepared project.

## Step 1: Bootstrap the inconsistencies log if absent

The audit writes findings to `docs/trunk/INCONSISTENCIES/`. If that directory doesn't exist, create it with this README:

```bash
mkdir -p docs/trunk/INCONSISTENCIES
```

Then write `docs/trunk/INCONSISTENCIES/README.md` with the schema documentation:

```markdown
# Inconsistencies Log

A running log of discovered mismatches between what the project's chunks (or
trunk docs) claim about the system and what the code or runtime actually does.

## When to add an entry

Whenever you discover that a chunk's GOAL.md, a trunk doc, a template comment,
or a skill description claims something the code or runtime contradicts:

- A doc says behavior X is supported; the runtime rejects it.
- A chunk's GOAL.md asserts the system does X; grepping shows it doesn't.
- A chunk's `code_references` admit `status: partial` while the GOAL claims completeness.

## Filename convention

```
YYYYMMDD_HHMMSS_microseconds_<slug>.md
```

Microsecond precision plus a descriptive slug makes collisions effectively
impossible across concurrent writers. Generate timestamps with:

```
python3 -c "from datetime import datetime; print(datetime.now().strftime('%Y%m%d_%H%M%S_%f'))"
```

## Entry format

YAML frontmatter:
- `discovered_by`: agent name or "operator"
- `discovered_at`: ISO 8601 timestamp
- `severity`: low | medium | high
- `status`: open | resolved
- `resolved_by`: chunk name, commit SHA, or null
- `artifacts`: list of file paths involved

Body sections: **Claim**, **Reality**, **Workaround**, **Fix paths**.

## Lifecycle

Entries land with `status: open`. When a chunk or commit resolves the
inconsistency, set `status: resolved` and `resolved_by:` to the resolution
reference. Resolved entries stay indefinitely as archaeological record.
```

## Step 2: Build the audit pool

Enumerate ACTIVE chunks. Exclude any that have been recently audited (those would have committed prose changes mentioning "audit" — operators can use a different filter if their commit history doesn't follow this convention):

```bash
ve chunk list --status ACTIVE 2>&1 | sed 's| \[ACTIVE\].*||' | sed 's|docs/chunks/||' > /tmp/audit_pool.txt
wc -l /tmp/audit_pool.txt
```

Decide whether to audit fresh (all ACTIVE chunks) or resume an in-progress audit (skip chunks already touched). For a fresh run, the pool is the entire ACTIVE list.

Tell the operator the pool size and confirm before proceeding. For corpora over 200 chunks, expect ~5 minutes of wall-clock per wave of 50.

## Step 3: Wave-based parallel execution

For each wave of 50 chunks:

1. Partition the next 50 chunks into 10 batches of 5.
2. Spawn 10 sub-agents in parallel via the Agent tool, subagent type `intent-auditor`. **All 10 calls must be in a single message** so they run concurrently.
3. Each sub-agent carries the full audit protocol in its agent definition (see "The intent-auditor agent" below); the task message supplies only its batch ID and 5-chunk scope.
4. Collect summaries when all 10 sub-agents return.
5. Verify the working tree (`git status --short`); flag anything outside expected scope.
6. Commit. Typically 2-3 commits per wave:
   - `audit: wave N — rewrites + codepath fixes (X chunks)` for chunk modifications
   - `audit: log Y inconsistency entries (wave N)` for new entries in `docs/trunk/INCONSISTENCIES/`
   - `audit: historicalize <names> (wave N)` if any chunks went HISTORICAL

7. Update the audit pool (remove the 50 audited chunks) and continue.

Stop when the pool is empty.

## Step 4: Final report

Produce a cumulative summary:

- Total chunks audited
- Counts per action (rewrote, logged, historicalized, codepath-fixed, clean)
- Number of inconsistency entries (open vs resolved)
- Top patterns (refactor-related stale references, half-shipped chunks, quantitative-criteria slips)
- Recommendations for follow-up (mechanical sweep chunks, per-chunk operator triage)

## The intent-auditor agent

Each batch is handled by the **intent-auditor** plugin agent
(`agents/intent-auditor.md`), which carries the full self-contained audit
protocol: detection criteria for retrospective framing and over-claimed
scope, action rules, the veto rule, mandatory symmetric verification, the
inconsistency entry format, and the per-chunk return format. Do not restate
the protocol when spawning agents — it is versioned once in the agent
definition.

The task message for each agent supplies only the per-invocation values:

```
You are batch <BATCH_ID> of this audit wave.

Audit these 5 chunks:

<list of 5 absolute paths to GOAL.md files>
```

---

## Notes for the orchestrating agent

- **Quality over speed.** Each sub-agent reads several files, verifies symbol existence, and applies judgment. A 5-chunk batch typically takes 2-3 minutes of agent time. Don't reduce the batch size below 5 (overhead per agent dominates) or above 10 (context overload reduces quality).
- **The veto rule is non-negotiable.** Sub-agents that over-aggressively rewrite chunks with over-claimed scope produce false-on-false: a tense fix that papers over a real implementation gap. The veto is the only thing preventing this.
- **Symmetric verification catches what the metadata hides.** Many chunks have honest `code_references` but stale prose, or honest prose but stale `code_references`. Both shapes need the symbols to actually exist before any rewrite is safe.
- **HISTORICAL chunks keep their goal text.** This is intentional — HISTORICAL semantically means "archaeology", and the goal becomes the historical record. A rewrite would erase that record.
- **The cross-artifact rule is opportunistic.** Sub-agents are auditing a chunk; they shouldn't go hunting for unrelated inconsistencies. But when verification crosses paths with a real mismatch (README vs workflow, two templates disagreeing), logging it is cheap and the alternative is the inconsistency staying invisible until someone trips on it again.
- **Patterns to expect.** Most projects with substantial chunk corpora will surface these patterns:
  - Refactor-related stale references (file moved, package split, CLI modularized)
  - Half-shipped chunks with quantitative success criteria that drifted (file size targets, line counts)
  - Bug-fix chunks that should have been HISTORICAL when the bug was fixed
  - Chunk-centric framing in older chunks ("This chunk adds...") that hasn't been updated to system-centric

If the audit catches none of these, the corpus is suspiciously clean — spot-check a few rewrites manually before trusting the run.
