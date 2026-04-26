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

Shared CLI formatting helpers live in a single `src/cli/formatters.py` module, so the four artifact CLI modules (`cli/chunk.py`, `cli/narrative.py`, `cli/subsystem.py`, `cli/investigation.py`) neither duplicate the formatting logic nor reach into each other for private symbols.

`formatters.py` exposes a single generic `artifact_to_json_dict(name, frontmatter, tips=None)` function that converts artifact frontmatter to a JSON-serializable dictionary for any artifact type. It handles the `None` frontmatter case, calls `model_dump()`, normalizes StrEnum status values, builds a result dict with `name` first then `status`, adds an `is_tip` indicator, and merges remaining frontmatter fields. There is no per-artifact variant.

`format_grouped_artifact_list()` and `format_grouped_artifact_list_json()` also live in `formatters.py` as public (non-underscore) functions. The four artifact CLI modules import these helpers from `cli.formatters`, with no cross-module imports of underscore-prefixed symbols between sibling CLI modules.

## Success Criteria

- `src/cli/formatters.py` exists and contains `artifact_to_json_dict()`, `format_grouped_artifact_list()`, and `format_grouped_artifact_list_json()` as public functions.
- A single generic `artifact_to_json_dict(name, frontmatter, tips=None)` function replaces the four separate `_chunk_to_json_dict()`, `_narrative_to_json_dict()`, `_subsystem_to_json_dict()`, and `_investigation_to_json_dict()` functions. The chunk-specific extra parameters (`chunks_manager`, `project_dir`) are removed from the generic signature since they are unused in the conversion logic.
- No CLI module imports private (underscore-prefixed) symbols from another CLI module. Specifically, `cli/subsystem.py` and `cli/investigation.py` no longer contain `from cli.chunk import _format_grouped_artifact_list` or `from cli.chunk import _format_grouped_artifact_list_json`.
- All CLI output (both text and JSON modes) for `ve chunk list`, `ve narrative list`, `ve subsystem list`, and `ve investigation list` remains byte-identical before and after the change. This is a pure refactor with no behavioral changes.
- All existing tests pass (`uv run pytest tests/`).

