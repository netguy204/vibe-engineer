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

Extract the file manipulation logic from the `narrative compact` CLI command into a domain method on the `Narratives` class.

Currently, the `compact` command in `src/cli/narrative.py` (lines 233-304) is the only CLI command that directly reads an artifact file, regex-parses its YAML frontmatter, modifies the parsed dict, re-serializes it, and writes the file back. Every other CLI command delegates file manipulation to its corresponding domain class. This inconsistency violates the layering convention that CLI commands handle argument parsing, validation, and user-facing output while domain classes handle artifact I/O.

The fix is to create a `Narratives.compact()` method in `src/narratives.py` that accepts the validated chunk IDs and description, performs the OVERVIEW.md frontmatter manipulation (setting `proposed_chunks` and `advances_trunk_goal`), and returns the created narrative path. The CLI command should then delegate to this method, keeping only its input validation and output formatting responsibilities.

This aligns with the project goal that "following the workflow must maintain the health of documents over time and should not grow more difficult over time" -- a consistent CLI-to-domain delegation pattern makes each layer independently testable and easier to modify as the project evolves. The existing `frontmatter.py` utilities (`extract_frontmatter_dict`, `update_frontmatter_field`) can be leveraged rather than reimplementing regex-based frontmatter parsing in the new domain method.

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
