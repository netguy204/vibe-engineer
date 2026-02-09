---
decision: APPROVE
summary: All success criteria satisfied - shared helper `list_curated_decisions()` extracted to `Reviewers` class, both CLI paths delegate to it, formatting handled in CLI layer via `_format_curated_decision()`.
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: A shared helper method exists on the `Reviewers` class (e.g., `list_curated_decisions(reviewer, limit)`) that encapsulates: globbing decision files, parsing frontmatter via the existing `parse_decision_frontmatter()` method, filtering for non-null `operator_review`, sorting by modification time (newest first), and limiting to N results. No raw YAML parsing remains in `src/cli/reviewer.py`.

- **Status**: satisfied
- **Evidence**: `Reviewers.list_curated_decisions()` method added at lines 219-274 of `src/reviewers.py`. It globs `*.md` files, calls `self.parse_decision_frontmatter()` (line 247), filters for `frontmatter.operator_review is None` (line 253), sorts by mtime descending (line 268), and slices to `[:limit]` (line 272). `src/cli/reviewer.py` has no `yaml.` imports or `safe_load`/`dump` calls - verified via grep.

### Criterion 2: The `decisions` group handler's `--recent` code path delegates to the shared helper instead of implementing its own glob/parse/filter/sort pipeline.

- **Status**: satisfied
- **Evidence**: Lines 115-125 of `src/cli/reviewer.py` show the group handler now calls `reviewers.list_curated_decisions(reviewer_name, limit=recent)` and formats via `_format_curated_decision()`. The original 50+ line inline implementation (lines 74-128 in the old version) was removed.

### Criterion 3: The `decisions list` subcommand delegates to the same shared helper instead of implementing its own glob/parse/filter/sort pipeline.

- **Status**: satisfied
- **Evidence**: Lines 182-201 of `src/cli/reviewer.py` show the `list` subcommand now calls `reviewers.list_curated_decisions(reviewer_name, limit=recent)` and formats via `_format_curated_decision()`. The original 90+ line inline implementation (lines 185-274 in the old version) was removed.

### Criterion 4: The agent nudge note (`NOTE TO AGENT: Read the full decision context...`) that the group handler currently emits for `FeedbackReview` entries is preserved in its output path; the formatting difference between the two call sites is handled at the CLI formatting layer, not in the shared helper.

- **Status**: satisfied
- **Evidence**: The `_format_curated_decision()` helper (lines 21-60 of `src/cli/reviewer.py`) takes an `include_nudge` parameter. The group handler calls it with `include_nudge=True` (line 125), while the list subcommand calls it with `include_nudge=False` (line 201). The nudge note logic is preserved at lines 55-57 of the helper. Test `test_nudge_appears_for_feedback_review` and `test_list_does_not_include_nudge` verify this difference.

### Criterion 5: The `--recent` flag on the `decisions` group and the `--recent` flag on the `decisions list` subcommand produce consistent output for the same inputs (aside from the intentional nudge note difference), eliminating the current silent behavioral divergence.

- **Status**: satisfied
- **Evidence**: Both paths now use the same `list_curated_decisions()` method and `_format_curated_decision()` helper. Test `test_list_produces_same_format_as_group_handler` verifies that both commands produce identical core content. Test `test_list_vs_group_nudge_difference` verifies the nudge is the only difference. All 47 tests pass.

### Criterion 6: Existing tests continue to pass. If tests exist for both `decisions --recent` and `decisions list --recent`, both still pass with identical data-level results.

- **Status**: satisfied
- **Evidence**: `uv run pytest tests/test_reviewer_decisions.py tests/test_reviewers.py -v` shows 47 tests passing. The `TestDecisionsListSubcommand` test class (15 tests) was added to verify the list subcommand behavior matches the group handler behavior.

### Criterion 7: No new public API is added to `Reviewers` beyond the shared helper; the helper returns structured data (e.g., list of tuples or dataclass instances) rather than formatted strings, keeping presentation in the CLI layer.

- **Status**: satisfied
- **Evidence**: Only `list_curated_decisions()` was added to `Reviewers`. It returns `list[CuratedDecision]` where `CuratedDecision` is a dataclass (lines 28-39 of `src/reviewers.py`) containing `path`, `frontmatter`, and `mtime`. All formatting (markdown headers, bullets, nudge notes) happens in `_format_curated_decision()` in the CLI layer.
