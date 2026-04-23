---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/wiki.py
- src/entity_repo.py
- tests/test_entity_wiki_lint.py
code_references:
- ref: src/entity_repo.py#WikiLintIssue
  implements: "Data type representing a single wiki integrity issue (file, type, detail)"
- ref: src/entity_repo.py#WikiLintResult
  implements: "Aggregated lint result with ok property for clean/dirty status"
- ref: src/entity_repo.py#lint_wiki
  implements: "Core wiki integrity linting logic: dead wikilinks, frontmatter errors, missing index entries, orphan pages"
- ref: src/entity_repo.py#_extract_wikilinks
  implements: "Regex extraction of [[target]] wikilink targets from page content"
- ref: src/entity_repo.py#_resolve_wikilink
  implements: "Obsidian shortest-path wikilink resolution to absolute file path"
- ref: src/entity_repo.py#_get_index_references
  implements: "Extract set of page stems referenced in index.md via wikilinks"
- ref: src/cli/wiki.py#wiki_lint
  implements: "CLI command ve wiki lint <entity> — invokes lint_wiki and formats output"
- ref: tests/test_entity_wiki_lint.py
  implements: "Test coverage for all four lint check types plus CLI exit codes"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_worktree_process_reap
---

# Chunk Goal

## Minor Goal

Add `ve wiki lint <entity>` command that validates wiki integrity for an
entity. Checks:

1. **Dead wikilinks** — `[[target]]` where the target file doesn't exist
2. **Frontmatter parse errors** — missing or malformed YAML frontmatter
3. **Pages missing from index** — wiki pages that exist on disk but have
   no entry in `index.md`
4. **Orphan pages** — pages with no inbound wikilinks from other pages

Useful both ad-hoc (operator audit) and as a post-shutdown check. The
wiki_schema.md already documents a "Lint" operation under the Operations
section — this command implements it programmatically.

### Cross-project context

Requested by the world-model project alongside wiki rename and reindex.
Complements the Identity.md Health Check added by wiki_identity_routing.

## Success Criteria

- `ve wiki lint <entity>` reports dead wikilinks, frontmatter errors,
  missing index entries, and orphan pages
- Exit code 0 when clean, non-zero when issues found
- Output is structured (one issue per line with file path and issue type)
- Test covers each check type

