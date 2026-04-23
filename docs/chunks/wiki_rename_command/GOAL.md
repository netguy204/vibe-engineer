---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/wiki.py
- src/cli/__init__.py
- src/entity_repo.py
- tests/test_entity_wiki_rename.py
code_references:
- ref: src/entity_repo.py#WikiRenameResult
  implements: "Result dataclass for wiki rename operation"
- ref: src/entity_repo.py#_rewrite_wikilinks
  implements: "Regex-based wikilink rewriting across wiki pages"
- ref: src/entity_repo.py#wiki_rename
  implements: "Core wiki rename logic: move file, update frontmatter, rewrite all wikilinks"
- ref: src/cli/wiki.py#wiki
  implements: "Top-level wiki click group"
- ref: src/cli/wiki.py#rename
  implements: "ve wiki rename subcommand: validates entity/page, invokes wiki_rename, reports results"
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

Add `ve wiki rename <entity> <old_path> <new_path>` command that moves a wiki
page and updates all inbound `[[wikilinks]]` across the entity's wiki.

Currently, renaming a wiki page requires manually: moving the file, fixing
frontmatter, rewriting all inbound wikilinks across every page, updating the
index, and updating in-page references. Missing one `[[link]]` creates a
silent dead link. This is the most valuable of three wiki tooling requests
from the world-model project, where wiki renames happen naturally as project
names evolve.

### What the command does

1. Move the file from old path to new path within the entity's wiki directory
2. Update the page's own frontmatter (title if derived from filename)
3. Find and rewrite all `[[wikilinks]]` in every wiki page that referenced
   the old path
4. Update `index.md` to reflect the new path/name

### Cross-project context

Requested by the world-model project's steward entity (skippy), which runs
as a Slack agent and frequently renames domain pages as project understanding
evolves.

## Success Criteria

- `ve wiki rename <entity> <old> <new>` moves the file and updates all
  inbound wikilinks
- Command reports how many files were updated
- Dead links are not created by the rename
- `index.md` is updated automatically
- Test covers rename with inbound wikilinks from multiple pages

