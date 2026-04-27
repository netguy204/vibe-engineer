---
discovered_by: claude
discovered_at: 2026-04-26T04:58:36+00:00
severity: low
status: open
resolved_by: null
artifacts:
  - docs/chunks/wiki_rename_command/GOAL.md
  - src/entity_repo.py
  - src/cli/wiki.py
---

# wiki_rename does not update the page's own frontmatter

## Claim

`docs/chunks/wiki_rename_command/GOAL.md` lists, under "What the command does":

> 2. Update the page's own frontmatter (title if derived from filename)

The CLI command's docstring (`src/cli/wiki.py:43-50`) similarly asserts the
command "Moves the file, rewrites all `[[wikilinks]]` that referenced the old
path, and updates index.md automatically."

## Reality

`wiki_rename` in `src/entity_repo.py:1364-1418` does exactly three things:

1. Validates the rename (wiki/ exists, old page exists, new page free).
2. Moves the file with `Path.rename`.
3. Sweeps every `wiki/**/*.md` and rewrites `[[old_path]]` and bare
   `[[old_stem]]` wikilinks via `_rewrite_wikilinks`.

It does NOT read or rewrite the renamed page's own YAML frontmatter — there is
no frontmatter parser invocation, no `title:` mutation, nothing. If the page
had a `title` field derived from its old filename, that title remains stale
after the rename.

The "updates index.md" claim is technically satisfied as a side effect of the
wikilink sweep (index.md is just one of the swept .md files, and it references
pages via `[[wikilinks]]`), but only for index entries written as wikilinks.
A non-wikilink reference in index.md would be missed.

## Workaround

None applied this session. The rename works correctly for its core purpose
(file move + inbound link rewrite); the missing frontmatter update is a
silent gap that callers may not notice until a downstream tool reads a stale
title.

## Fix paths

1. **Trim the GOAL** — drop step 2 ("Update the page's own frontmatter") from
   the "What the command does" list. The success criteria do not call out
   frontmatter, so the goal is internally inconsistent rather than
   contradicted by the criteria; trimming the prose to match the implemented
   behavior is the smallest change.
2. **Implement frontmatter update** — extend `wiki_rename` to parse the
   moved page's frontmatter and update its `title` field if the existing
   title was derived from the filename. Requires deciding the heuristic for
   "derived from filename" (case- and separator-insensitive match? exact
   match against the slug? against the stem?).

Option 1 is preferred unless a concrete consumer needs the frontmatter
update — chasing a hypothetical title-derivation rule risks introducing
fragile string-matching for no observed user benefit.
