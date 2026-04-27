---
discovered_by: audit batch 10g
discovered_at: 2026-04-26T02:30:56Z
severity: medium
status: open
artifacts:
  - docs/chunks/subsystem_docs_update/GOAL.md
---

# Claim

`docs/chunks/subsystem_docs_update/GOAL.md` Success Criteria #4 ("Directory naming transition documented") asserts the workflow_artifacts subsystem doc states:

> - Current: All existing artifacts use `{NNNN}-{short_name}/`, new artifacts still created with prefix
> - Terminal: `{short_name}/` only (sequence prefixes fully retired, no backwards compatibility)

The chunk's goal also describes Hard Invariant #1 as "currently mandates `{NNNN}-{short_name}` directory naming" — a mid-flight framing.

# Reality

The `ordering_remove_seqno` chunk has already shipped the "Terminal" state — sequence prefixes are gone from `docs/chunks/`, `docs/subsystems/`, `docs/narratives/`, and `docs/investigations/`:

```
$ ls docs/subsystems/
cluster_analysis
cross_repo_operations
friction_tracking
orchestrator
template_system
workflow_artifacts
```

`Subsystems.create_subsystem` (`src/subsystems.py:189`) writes `docs/subsystems/<shortname>/` with no prefix; `is_subsystem_dir` only matches the bare-shortname pattern; same story for chunks/narratives/investigations.

So SC #4's "Current"/"Terminal" framing is inverted — what the SC calls Terminal is the actual current state, and what it calls Current is the historical state. The chunk's body framing ("currently mandates `{NNNN}-{short_name}`") is similarly stale.

The chunk's `code_paths` referenced `docs/subsystems/0002-workflow_artifacts/OVERVIEW.md`, which no longer exists — the file lives at `docs/subsystems/workflow_artifacts/OVERVIEW.md`. (Fixed in place during this audit per the broken-code_paths action rule.)

# Workaround

None — the workflow_artifacts subsystem documentation does describe causal ordering and the post-prefix world; the GOAL.md just narrates a transition that has since completed.

# Fix paths

1. Sweep this and the other ACTIVE chunks that still reference the `{NNNN}-` transition in a post-`ordering_remove_seqno` cleanup chunk. Update SC #4's "Current/Terminal" wording to reflect that the terminal state is now current.
2. Historicalize once the workflow_artifacts subsystem docs have been audited against this chunk's SCs and the SC content is owned by a more current artifact (the workflow_artifacts OVERVIEW.md itself, ideally).

# Audit context

Detected by `intent_active_audit` batch 10g. Veto fired on prose rewrite — SC #4 is over-claim relative to current code. Code_paths fix applied: `docs/subsystems/0002-workflow_artifacts/OVERVIEW.md` → `docs/subsystems/workflow_artifacts/OVERVIEW.md` (unambiguous; same shortname, only the directory naming changed).
