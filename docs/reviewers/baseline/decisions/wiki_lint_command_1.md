---
decision: FEEDBACK  # APPROVE | FEEDBACK | ESCALATE
summary: "All four lint checks implemented and tested correctly, but the lint command was placed in entity.py rather than the established cli/wiki.py module, breaking the existing reindex command."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve wiki lint <entity>` reports dead wikilinks, frontmatter errors, missing index entries, and orphan pages

- **Status**: satisfied
- **Evidence**: `lint_wiki()` in `src/entity_repo.py:1356` implements all four checks in three passes. Pass 1 handles frontmatter errors and dead wikilinks while building the inbound link map. Pass 2 detects pages missing from index. Pass 3 detects orphan pages. All four check types are tested and pass.

### Criterion 2: Exit code 0 when clean, non-zero when issues found

- **Status**: satisfied
- **Evidence**: `src/cli/entity.py:1199-1200` — `raise SystemExit(1)` when `not result.ok`. `TestCliExitCodes::test_cli_exit_code_clean` verifies exit 0; `test_cli_exit_code_with_issues` verifies exit 1.

### Criterion 3: Output is structured (one issue per line with file path and issue type)

- **Status**: satisfied
- **Evidence**: `src/cli/entity.py:1197` — `click.echo(f"{issue.file}: [{issue.issue_type}] {issue.detail}")` matches the plan's spec of `<relative_path>: [<issue_type>] <detail>`.

### Criterion 4: Test covers each check type

- **Status**: satisfied
- **Evidence**: `tests/test_entity_wiki_lint.py` — 17 tests cover all four check types (`TestDeadWikilinks`, `TestFrontmatterErrors`, `TestMissingFromIndex`, `TestOrphanPages`), structural exemptions, and CLI exit codes. All 17 pass.

## Feedback Items

### issue-f001: lint command placed in wrong module, breaking existing reindex

- **Location**: `src/cli/entity.py:1153-1200`, `src/cli/__init__.py:36,56`
- **Concern**: The `wiki_reindex_command` chunk (already merged to main) established `src/cli/wiki.py` as the dedicated module for wiki CLI commands, with `__init__.py` importing `wiki` from `cli.wiki`. This chunk instead added a new `wiki` click group to `entity.py` and changed `__init__.py` to import from `cli.entity`. After merging main into this branch, `src/cli/wiki.py` (with the `reindex` subcommand) is staged but unreachable — `__init__.py` imports the `entity.py` wiki group, which has no `reindex` command. The existing `ve wiki reindex` command is broken.
- **Suggestion**:
  1. Move the `wiki_lint` function and `@wiki.command("lint")` decorator from `entity.py` into `src/cli/wiki.py` as an additional subcommand on the existing `wiki` group.
  2. Remove the `wiki` click group definition from `entity.py`.
  3. Revert `__init__.py` to import `wiki` from `cli.wiki` (as it was on main): `from cli.wiki import wiki`.
- **Severity**: functional
- **Confidence**: high
