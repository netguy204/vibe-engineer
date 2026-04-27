---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/narratives.py
- src/cli/narrative.py
- tests/test_narratives.py
code_references:
- ref: src/narratives.py#Narratives::compact
  implements: "Domain method for chunk consolidation into narrative"
- ref: src/cli/narrative.py#compact
  implements: "CLI command that delegates to domain method"
- ref: tests/test_narratives.py#TestNarrativeCompact
  implements: "Test coverage for Narratives.compact() method"
narrative: arch_review_gaps
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- cli_decompose
- integrity_deprecate_standalone
- low_priority_cleanup
- optimistic_locking
- spec_and_adr_update
- test_file_split
- orch_session_auto_resume
---

# Chunk Goal

## Minor Goal

The `narrative compact` workflow follows the project's CLI-to-domain delegation convention: file manipulation lives in a domain method, and the CLI command handles only argument parsing, validation, and user-facing output.

`Narratives.compact(chunk_ids, name, description)` in `src/narratives.py` performs the consolidation. It calls `self.create_narrative(name)` to create the narrative directory (reusing existing creation logic), then uses `frontmatter.update_frontmatter_field` to set `proposed_chunks` (with entries for each chunk ID) and `advances_trunk_goal` (with the description) on the generated `OVERVIEW.md`, and returns the created narrative path. No regex-based frontmatter parsing or inline `yaml.safe_load`/`yaml.dump` lives in this layer.

The `compact` CLI command in `src/cli/narrative.py` delegates all file manipulation to `Narratives.compact()`, retaining only chunk-existence validation (via `Chunks`), CLI output formatting, and error handling. It does not import `re` or `yaml` directly.

This consistent CLI-to-domain delegation pattern makes each layer independently testable and easier to modify as the project evolves, in line with the project goal that following the workflow must maintain the health of documents over time and not grow more difficult.

## Success Criteria

- A `Narratives.compact(chunk_ids: list[str], description: str)` method exists in `src/narratives.py` that:
  - Calls `self.create_narrative(name)` to create the narrative directory (reusing existing creation logic)
  - Reads the generated `OVERVIEW.md`, updates its frontmatter to set `proposed_chunks` (with entries for each chunk ID) and `advances_trunk_goal` (with the description), and writes the file back
  - Uses utilities from `src/frontmatter.py` rather than inline regex parsing
  - Returns the created narrative path
- The `compact` CLI command in `src/cli/narrative.py` delegates all file manipulation to `Narratives.compact()` and retains only: argument parsing, chunk existence validation (via `Chunks`), CLI output formatting, and error handling with `click.echo`/`SystemExit`
- The `compact` CLI command no longer imports `re` or `yaml` directly and does not contain any regex patterns or `yaml.safe_load`/`yaml.dump` calls
- The behavior of `ve narrative compact` is unchanged: given the same inputs, it produces the same narrative directory with the same OVERVIEW.md frontmatter content and the same CLI output
- All existing tests continue to pass
