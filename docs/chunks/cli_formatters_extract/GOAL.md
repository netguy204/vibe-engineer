---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/cli/formatters.py
  - src/cli/chunk.py
  - src/cli/narrative.py
  - src/cli/subsystem.py
  - src/cli/investigation.py
code_references:
  - ref: src/cli/formatters.py#artifact_to_json_dict
    implements: "Generic artifact-to-JSON conversion for all artifact types"
  - ref: src/cli/formatters.py#format_grouped_artifact_list
    implements: "Text output formatting for grouped artifact listings (task context)"
  - ref: src/cli/formatters.py#format_grouped_artifact_list_json
    implements: "JSON output formatting for grouped artifact listings (task context)"
narrative: arch_decompose
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- chunks_decompose
- orch_worktree_cleanup
- validation_error_surface
- validation_length_msg
- orch_ready_critical_path
- orch_pre_review_rebase
- orch_merge_before_delete
---

# Chunk Goal

## Minor Goal

Extract shared CLI formatting helpers into a new `src/cli/formatters.py` module, eliminating duplicated code and cross-module private imports that have accumulated across the four artifact CLI modules.

Today, each artifact CLI module (`cli/chunk.py`, `cli/narrative.py`, `cli/subsystem.py`, `cli/investigation.py`) contains its own `_*_to_json_dict()` function that converts artifact frontmatter to a JSON-serializable dictionary. These four functions share identical core logic: handle the `None` frontmatter case, call `model_dump()`, normalize StrEnum status values, build a result dict with `name` first then `status`, add an `is_tip` indicator, and merge remaining frontmatter fields. The only variation is that the chunk version accepts additional parameters (`chunks_manager`, `project_dir`) that it does not actually use in its logic beyond passing them through.

Additionally, `_format_grouped_artifact_list()` and `_format_grouped_artifact_list_json()` are defined in `cli/chunk.py` but imported as private symbols by both `cli/subsystem.py` (line 137) and `cli/investigation.py` (line 221) via `from cli.chunk import _format_grouped_artifact_list, _format_grouped_artifact_list_json`. This cross-module import of private (underscore-prefixed) functions couples modules that should be independent.

This chunk will:

1. Create `src/cli/formatters.py` with a single generic `artifact_to_json_dict(name, frontmatter, tips=None)` function that replaces all four `_*_to_json_dict()` variants.
2. Move `_format_grouped_artifact_list()` and `_format_grouped_artifact_list_json()` from `cli/chunk.py` into `cli/formatters.py` as public functions (without underscore prefix).
3. Update all four CLI modules to import from `cli.formatters` instead of defining their own copies or importing private symbols from `cli.chunk`.

## Success Criteria

- `src/cli/formatters.py` exists and contains `artifact_to_json_dict()`, `format_grouped_artifact_list()`, and `format_grouped_artifact_list_json()` as public functions.
- A single generic `artifact_to_json_dict(name, frontmatter, tips=None)` function replaces the four separate `_chunk_to_json_dict()`, `_narrative_to_json_dict()`, `_subsystem_to_json_dict()`, and `_investigation_to_json_dict()` functions. The chunk-specific extra parameters (`chunks_manager`, `project_dir`) are removed from the generic signature since they are unused in the conversion logic.
- No CLI module imports private (underscore-prefixed) symbols from another CLI module. Specifically, `cli/subsystem.py` and `cli/investigation.py` no longer contain `from cli.chunk import _format_grouped_artifact_list` or `from cli.chunk import _format_grouped_artifact_list_json`.
- All CLI output (both text and JSON modes) for `ve chunk list`, `ve narrative list`, `ve subsystem list`, and `ve investigation list` remains byte-identical before and after the change. This is a pure refactor with no behavioral changes.
- All existing tests pass (`uv run pytest tests/`).

