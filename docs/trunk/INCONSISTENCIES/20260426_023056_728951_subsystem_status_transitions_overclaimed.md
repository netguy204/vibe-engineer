---
discovered_by: audit batch 10g
discovered_at: 2026-04-26T02:30:56Z
severity: medium
status: open
artifacts:
  - docs/chunks/subsystem_status_transitions/GOAL.md
---

# Claim

`docs/chunks/subsystem_status_transitions/GOAL.md` Success Criteria #2 ("ID resolution") asserts:

> The command accepts either:
> - Full subsystem directory name: `0001-validation`
> - Just the shortname: `validation`
>
> If shortname is provided, it resolves to the full directory name using `Subsystems.find_by_shortname()`

The chunk also describes ID examples in error messages (SC #5) that imply the `0001-` prefix is part of the canonical directory layout, and the `## Minor Goal` body references sibling chunks by their old prefixed names (`Chunk 0014-subsystem_schemas_and_model`, `Chunk 0016-subsystem_cli_scaffolding`).

# Reality

The `ordering_remove_seqno` chunk removed the `{NNNN}-{short_name}/` directory naming convention. Subsystem directories now live at `docs/subsystems/<shortname>/` with no prefix:

```
$ ls docs/subsystems/
cluster_analysis
cross_repo_operations
friction_tracking
orchestrator
template_system
workflow_artifacts
```

`Subsystems.find_by_shortname()` (`src/subsystems.py:139-153`) iterates `enumerate_subsystems()` and only matches when `dirname == shortname` — there is no longer a "full directory name" form distinct from the shortname.

The chunks `0014-subsystem_schemas_and_model` and `0016-subsystem_cli_scaffolding` no longer exist under those names; the corresponding chunk dirs (if still present) carry the un-prefixed slug.

# Workaround

None — the `ve subsystem status` CLI works correctly against the current naming scheme. The doc/code drift is purely in the GOAL.md narrative.

# Fix paths

1. **Rewrite SC #2 and the body's "builds upon" references** to drop the `0001-` and `0014-`/`0016-` prefixes. Preferred: a follow-up chunk that sweeps stale `{NNNN}-` references out of all chunk GOAL.md files post-`ordering_remove_seqno`.
2. Historicalize this chunk after a successor chunk owns the present-day `ve subsystem status` contract under post-prefix naming.

# Audit context

Detected by `intent_active_audit` batch 10g. Veto fired on prose rewrite — the SC over-claim makes any tense rewrite a substitution of one stale claim for another. Code_paths reference `src/models.py` (which no longer exists; the module has been split into `src/models/`) was fixed in place to `src/models/subsystem.py` per the audit's broken-code_paths action rule, since the symbol `VALID_STATUS_TRANSITIONS` lives at `src/models/subsystem.py:29`.
