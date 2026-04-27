---
discovered_by: audit batch 10c
discovered_at: 2026-04-26T02:31:02Z
severity: low
status: open
artifacts:
  - docs/chunks/task_aware_investigations/GOAL.md
---

## Claim

`docs/chunks/task_aware_investigations/GOAL.md` (success criterion 4, "Model updates"):

> - Add `dependents: list[InvestigationDependent]` field to track which projects reference this investigation
> - `InvestigationDependent` model with `project_path` and `artifact_id` fields (following `NarrativeDependent` pattern)

The chunk asserts that an `InvestigationDependent` model exists, with the typed field `dependents: list[InvestigationDependent]`, and that it follows a `NarrativeDependent` pattern.

## Reality

Neither `InvestigationDependent` nor `NarrativeDependent` exists in `src/models/`. The actual implementation in `src/models/investigation.py:42` uses the generic `ExternalArtifactRef`:

```python
dependents: list[ExternalArtifactRef] = []  # For cross-repo investigations
```

`src/models/narrative.py` likewise uses `list[ExternalArtifactRef]`. The dedicated dependent dataclass envisioned in the chunk's success criterion was never created — the existing cross-repo reference type was reused instead.

Reproduction:

```
$ grep -rn "class InvestigationDependent\|class NarrativeDependent" src/models/
(no matches)
$ grep -n "dependents" src/models/investigation.py
42:    dependents: list[ExternalArtifactRef] = []
```

## Workaround

None needed at runtime — the `ExternalArtifactRef` choice is functional. The mismatch is purely between the chunk's stated model shape and the shipped model.

## Fix paths

1. **Update GOAL.md to match reality (preferred):** Drop the `InvestigationDependent` model claim and the "following `NarrativeDependent` pattern" wording. State that `dependents: list[ExternalArtifactRef]` was added, matching the existing `NarrativeFrontmatter.dependents` field. Cheaper and more honest — the chunk's intent (cross-repo dependent tracking) is satisfied, only the implementation choice differs.
2. **Introduce dedicated dependent models:** Create `InvestigationDependent` (and `NarrativeDependent`) wrapping `ExternalArtifactRef`-equivalent fields. More structured but also more code for no current benefit; only worth doing if the per-artifact dependent shape needs to diverge from `ExternalArtifactRef` later.
