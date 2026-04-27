---
discovered_by: audit batch 10d sub-agent
discovered_at: 2026-04-26T02:30:48Z
severity: low
status: resolved
resolved_by: "audit batch 10d — code_paths and code_references rewritten in place to point at src/cli/external.py"
artifacts:
  - docs/chunks/external_resolve_all_types/GOAL.md
---

# external_resolve_all_types references symbols at src/ve.py that moved to src/cli/external.py

## Claim

`docs/chunks/external_resolve_all_types/GOAL.md` lists three `code_references`
pointing into `src/ve.py`:

- `src/ve.py#resolve` — "CLI command updated to accept local_artifact_id with
  --main-only/--secondary-only options"
- `src/ve.py#_detect_artifact_type_from_id` — "Auto-detection of artifact type
  from project directory structure"
- `src/ve.py#_display_resolve_result` — "Type-aware display showing artifact
  type in header and appropriate file names"

`src/ve.py` is also listed in `code_paths`.

## Reality

These three symbols no longer live in `src/ve.py`. They are in
`src/cli/external.py`:

```bash
$ grep -n "_detect_artifact_type_from_id\|_display_resolve_result\|^def resolve" src/ve.py
# (no matches)

$ grep -n "_detect_artifact_type_from_id\|_display_resolve_result\|def resolve" src/cli/external.py
40: def resolve(local_artifact_id, main_only, secondary_only, goal_only, plan_only, project, project_dir):
82: def _detect_artifact_type_from_id(project_path: pathlib.Path, local_artifact_id: str) -> tuple[ArtifactType, str]:
210: def _display_resolve_result(result: ResolveResult, main_only: bool, secondary_only: bool):
```

The chunk's `code_references` list does include
`src/cli/external.py#resolve` ("after CLI modularization") as a final entry —
suggesting the chunk author was aware of the move but did not delete the stale
`src/ve.py#*` entries.

## Workaround

None applied. Functions exist and behave as described; only the `code_paths`
and three `code_references` are misrouted.

## Fix paths

1. Replace the three `src/ve.py#*` `code_references` entries with their
   `src/cli/external.py#*` equivalents and remove `src/ve.py` from `code_paths`
   (or replace it with `src/cli/external.py` if not already implied by another
   chunk). Update via `/chunks-resolve-references` or by direct edit.

2. Alternative: leave the entries as historical pointers; downstream tooling
   that walks `code_references` will simply skip the missing symbols.
   Discouraged — silent broken references erode trust in the index.
