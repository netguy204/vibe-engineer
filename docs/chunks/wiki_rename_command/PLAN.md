

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Added a new `ve wiki rename <entity> <old_path> <new_path>` command as a
top-level `wiki` click group (analogous to the existing `entity` group).
Business logic lives in `entity_repo.py` following the existing pattern of
result dataclasses and pure-function operations on entity repo paths.

Wikilink rewriting uses a regex `\[\[([^\]|]+?)(\|[^\]]+?)?\]\]` to find
all wikilinks and rewrite:
- Full-path links: `[[domain/foo]]` → `[[domain/bar]]`
- Bare-stem links: `[[foo]]` → `[[bar]]` (when stem changes)
- Display-text variants: `[[domain/foo|Display]]` → `[[domain/bar|Display]]`

`index.md` is updated automatically as part of the same scan over all wiki
`.md` files — no special case needed.

## Sequence

### Step 1: Add WikiRenameResult dataclass to entity_repo.py

Added after the existing result dataclasses (PushResult, PullResult, etc.).

### Step 2: Add _rewrite_wikilinks() and wiki_rename() to entity_repo.py

`_rewrite_wikilinks(filepath, old_path, new_path, old_stem, new_stem) → bool`
applies the compiled wikilink regex and returns True if the file was modified.

`wiki_rename(entity_path, old_path, new_path) → WikiRenameResult` validates
paths, moves the file, derives stems, and calls `_rewrite_wikilinks` on all
`.md` files in the wiki directory tree.

### Step 3: Create src/cli/wiki.py with wiki group and rename subcommand

New module following the same pattern as `src/cli/entity.py`. Reuses
`resolve_entity_project_dir` from `cli.entity` to find the project root.
Entity is looked up at `project_dir / ".entities" / entity`.

### Step 4: Register wiki in src/cli/__init__.py

Added import and `cli.add_command(wiki)`.

### Step 5: Write tests in tests/test_entity_wiki_rename.py

18 tests covering:
- Unit tests: file move, subdirectory creation, full-path link rewriting,
  stem link rewriting, display-text preservation, multi-page updates,
  index.md updates, unchanged-stem behavior, error cases
- CLI tests: success path with output verification, actual file move,
  multi-page link rewriting, entity-not-found, page-not-found, collision

## Deviations

- `src/cli/entity.py` was not modified (code_paths in GOAL.md was updated
  to reflect the actual files touched). The wiki command is a peer group,
  not a subcommand of entity, which matches the `ve wiki rename` command
  signature from the goal.