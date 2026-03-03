---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/reviewer.py
- src/reviewers.py
- tests/test_reviewer_decisions.py
- tests/test_reviewers.py
code_references:
  - ref: src/reviewers.py#CuratedDecision
    implements: "Dataclass for curated decision results with path, frontmatter, and mtime"
  - ref: src/reviewers.py#Reviewers::list_curated_decisions
    implements: "Shared helper encapsulating glob/parse/filter/sort/limit pipeline"
  - ref: src/cli/reviewer.py#_format_curated_decision
    implements: "Shared CLI formatting helper with optional nudge note support"
  - ref: src/cli/reviewer.py#decisions
    implements: "Group handler --recent path delegates to shared helper"
  - ref: src/cli/reviewer.py#list_decisions
    implements: "List subcommand delegates to shared helper (without nudge)"
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

The `decisions` group handler's `--recent` path (lines 74-128 of `src/cli/reviewer.py`) and the `decisions list` subcommand (lines 185-274) implement nearly identical logic: glob decision files, parse YAML frontmatter manually, filter for curated decisions (non-null `operator_review`), sort by modification time, and format output. Both also bypass the `Reviewers` class entirely, duplicating raw YAML parsing that `Reviewers.parse_decision_frontmatter()` already provides.

This chunk extracts a shared helper (e.g., `_list_curated_decisions()`) in the `Reviewers` class that encapsulates the common "glob, parse, filter curated, sort by mtime, limit" pipeline, and has both the group handler's `--recent` path and the `list` subcommand delegate to it. This also resolves the confusing UX overlap where `ve reviewer decisions --recent 5` and `ve reviewer decisions list --recent 5` do nearly the same thing with slightly different behavior (the group handler adds an agent nudge note for feedback reviews; the subcommand does not).

This advances the project's goal of maintaining a clean, well-factored CLI by eliminating a concrete source of maintenance burden and divergence risk identified during architecture review.

## Success Criteria

- A shared helper method exists on the `Reviewers` class (e.g., `list_curated_decisions(reviewer, limit)`) that encapsulates: globbing decision files, parsing frontmatter via the existing `parse_decision_frontmatter()` method, filtering for non-null `operator_review`, sorting by modification time (newest first), and limiting to N results. No raw YAML parsing remains in `src/cli/reviewer.py`.
- The `decisions` group handler's `--recent` code path delegates to the shared helper instead of implementing its own glob/parse/filter/sort pipeline.
- The `decisions list` subcommand delegates to the same shared helper instead of implementing its own glob/parse/filter/sort pipeline.
- The agent nudge note (`NOTE TO AGENT: Read the full decision context...`) that the group handler currently emits for `FeedbackReview` entries is preserved in its output path; the formatting difference between the two call sites is handled at the CLI formatting layer, not in the shared helper.
- The `--recent` flag on the `decisions` group and the `--recent` flag on the `decisions list` subcommand produce consistent output for the same inputs (aside from the intentional nudge note difference), eliminating the current silent behavioral divergence.
- Existing tests continue to pass. If tests exist for both `decisions --recent` and `decisions list --recent`, both still pass with identical data-level results.
- No new public API is added to `Reviewers` beyond the shared helper; the helper returns structured data (e.g., list of tuples or dataclass instances) rather than formatted strings, keeping presentation in the CLI layer.

