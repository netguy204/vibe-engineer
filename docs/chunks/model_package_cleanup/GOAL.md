---
status: ACTIVE
ticket: null
parent_chunk: models_subpackage
code_paths: []
code_references:
  - ref: src/models/__init__.py
    implements: "Verification target - confirms models package is the sole source of truth after monolith deletion"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_prune_consolidate
- chunk_validator_extract
- cli_formatters_extract
- frontmatter_import_consolidate
- models_subpackage
- orch_client_context
- project_artifact_registry
- remove_legacy_prefix
- scheduler_decompose
---

# Chunk Goal

## Minor Goal

Delete the dead `src/models.py` monolith file (814 lines) that is a complete duplicate of the `src/models/` package.

When both `src/models.py` and `src/models/` exist, Python's import resolution prefers the package directory. This means `from models import X` always resolves to `src/models/__init__.py`, making the monolith file entirely unreachable dead code. The file shows as untracked in git (`?? src/models.py`), indicating it was extracted into the `src/models/` package but never deleted.

This is a hazard: any future developer who edits `src/models.py` thinking it is the source of truth would have their changes silently ignored at runtime. Removing it eliminates confusion and makes the codebase honest about where model definitions live.

## Success Criteria

- `src/models.py` is deleted from the working tree
- No import statements across the codebase resolve to `src/models.py` (all imports already resolve to the `src/models/` package, so this is a verification step, not a code change)
- The full test suite (`uv run pytest tests/`) passes with zero regressions
- This is a zero-functional-change cleanup: no behavior differences before and after

