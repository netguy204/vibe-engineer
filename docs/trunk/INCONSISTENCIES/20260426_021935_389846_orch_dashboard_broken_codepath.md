---
discovered_by: audit batch 9d
discovered_at: 2026-04-26T02:19:35
severity: low
status: open
artifacts:
  - docs/chunks/orch_dashboard/GOAL.md
---

## Claim

`docs/chunks/orch_dashboard/GOAL.md` lists `src/orchestrator/api.py` in `code_paths` (line 6) and references symbols under that path in its `code_references`:

- `src/orchestrator/api.py#dashboard_endpoint`
- `src/orchestrator/api.py#websocket_endpoint`
- `src/orchestrator/api.py#answer_endpoint`
- `src/orchestrator/api.py#resolve_conflict_endpoint`
- `src/orchestrator/api.py#_get_jinja_env`

## Reality

`src/orchestrator/api.py` does not exist. It has been refactored into a package at `src/orchestrator/api/` containing multiple files. The symbols are now distributed across that package:

- `dashboard_endpoint` → `src/orchestrator/api/streaming.py:325`
- `websocket_endpoint` → `src/orchestrator/api/streaming.py:283`
- `answer_endpoint` → `src/orchestrator/api/attention.py:106`
- `resolve_conflict_endpoint` → `src/orchestrator/api/conflicts.py:117`
- `_get_jinja_env` → not located by grep across the new package; may have been inlined or renamed.

Reproduction:

```
$ ls src/orchestrator/api.py
ls: src/orchestrator/api.py: No such file or directory
$ ls src/orchestrator/api/
__init__.py  app.py  attention.py  common.py  conflicts.py  scheduling.py  streaming.py  work_units.py  worktrees.py
```

## Workaround

None applied — audit logs only, does not finish implementations or restructure metadata.

The audit treated the broken file ref as not-uniquely-fixable per the audit's "fix-in-place only when alternative is unambiguous" rule. The endpoint symbols are split across at least three files in the new package, so a mechanical rewrite of `src/orchestrator/api.py` → some single replacement is not viable.

## Fix paths

1. **Update the chunk's metadata**: replace `src/orchestrator/api.py` in `code_paths` with `src/orchestrator/api/` (package directory) or with the explicit list of files containing referenced symbols. Update each `code_references[].ref` to point at the file where the symbol now lives. Find `_get_jinja_env`'s current home (or remove the reference if it was inlined). This is mechanical metadata cleanup.
2. **Restructure the package back into a single module**: not advised — the split into `api/` subpackage is an architectural improvement; fixing the doc is cheaper than reverting code.

Preference: option 1.
