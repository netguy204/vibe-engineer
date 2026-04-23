---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/wiki.py
- src/cli/__init__.py
- src/entity_repo.py
- tests/test_entity_wiki_reindex.py
code_references:
  - ref: src/cli/wiki.py#wiki
    implements: "wiki CLI command group entry point"
  - ref: src/cli/wiki.py#reindex
    implements: "ve wiki reindex <entity> subcommand — CLI glue for reindex_wiki"
  - ref: src/cli/__init__.py
    implements: "Registration of the wiki command group into the main CLI"
  - ref: src/entity_repo.py#WikiReindexResult
    implements: "Result dataclass for wiki reindex operation (pages_total, directories_scanned)"
  - ref: src/entity_repo.py#_parse_existing_summaries
    implements: "Extract page→summary mapping from existing index.md to preserve manual summaries"
  - ref: src/entity_repo.py#_scan_wiki_pages
    implements: "Scan wiki directory and return pages grouped by section (core/domain/techniques/projects/relationships)"
  - ref: src/entity_repo.py#_generate_index_md
    implements: "Render fresh index.md content from scanned pages, reusing preserved summaries"
  - ref: src/entity_repo.py#reindex_wiki
    implements: "Main reindex function — orchestrates scan, summary preservation, and index overwrite"
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

Add `ve wiki reindex <entity>` command that regenerates `wiki/index.md` from
page frontmatter, eliminating manual index maintenance toil.

Currently, entities must manually add a row to `index.md` every time they
create a wiki page. This is mechanical work that drifts — the entity forgets,
pages go unlisted, and the next startup's wake payload shows an out-of-date
index. The wiki_schema.md already says "every page you create must have a
row in the appropriate table" — this command enforces that programmatically.

### What the command does

1. Scan all wiki pages across all directories (domain/, techniques/, projects/,
   relationships/, plus core pages)
2. Read each page's frontmatter (title, created, updated)
3. Generate `index.md` with one row per page, grouped by directory, sorted
   alphabetically
4. Write the regenerated index

Could optionally be integrated into `ve entity shutdown` to auto-reindex
before session end.

### Cross-project context

Requested by the world-model project alongside wiki rename and lint.

## Success Criteria

- `ve wiki reindex <entity>` regenerates `index.md` from page frontmatter
- All wiki pages with valid frontmatter appear in the generated index
- Pages are grouped by directory (domain, techniques, projects, relationships)
- Existing `index.md` is overwritten (not appended to)
- Test covers reindex with pages across multiple directories

