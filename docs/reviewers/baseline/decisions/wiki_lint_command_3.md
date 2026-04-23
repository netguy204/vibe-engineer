---
decision: FEEDBACK
summary: "The chunk introduces a critical name collision: a second `_WIKILINK_RE` definition in entity_repo.py shadows the wiki-rename regex and breaks all 12 wiki-rename tests with IndexError."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve wiki lint <entity>` reports dead wikilinks, frontmatter errors, missing index entries, and orphan pages

- **Status**: satisfied
- **Evidence**: `lint_wiki()` in `src/entity_repo.py:1653` implements all four checks in three passes; all 17 lint tests pass.

### Criterion 2: Exit code 0 when clean, non-zero when issues found

- **Status**: satisfied
- **Evidence**: `wiki_lint` CLI in `src/cli/wiki.py` calls `raise SystemExit(1)` when `not result.ok`; confirmed by `TestCliExitCodes`.

### Criterion 3: Output is structured (one issue per line with file path and issue type)

- **Status**: satisfied
- **Evidence**: `click.echo(f"{issue.file}: [{issue.issue_type}] {issue.detail}")` in `src/cli/wiki.py`.

### Criterion 4: Test covers each check type

- **Status**: satisfied
- **Evidence**: `tests/test_entity_wiki_lint.py` has 17 tests covering dead wikilinks, frontmatter errors (missing + malformed), missing-from-index, orphan pages, structural exemptions, and CLI exit codes. All pass.

## Feedback Items

### Issue 1: Duplicate `_WIKILINK_RE` definition breaks wiki rename (critical regression)

- **Location**: `src/entity_repo.py:1616`
- **Concern**: A second module-level `_WIKILINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")` is defined at line 1616, shadowing the wiki-rename regex defined at line 1329 (`re.compile(r"\[\[([^\]|]+?)(\|[^\]]+?)?\]\]")`). Since Python resolves module-level names at call time, `_rewrite_wikilinks` (line 1332) now uses the lint regex, which has only one capture group. The `_replace` closure at line 1349 accesses `m.group(2)`, causing `IndexError: no such group` for every call. All 12 wiki-rename tests fail as a result.
- **Suggestion**: Rename the lint-specific regex to `_LINT_WIKILINK_RE` at line 1616 and update `_extract_wikilinks` to reference `_LINT_WIKILINK_RE`. The rename regex at line 1329 should keep the name `_WIKILINK_RE` unchanged.
- **Severity**: functional
- **Confidence**: high
