

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add `ve wiki reindex <entity>` by introducing a new top-level `wiki` Click
command group (in `src/cli/wiki.py`), wiring it into `src/main.py`, and
implementing the scan-and-generate logic as a standalone function in
`src/entity_repo.py`.

**Why a new `wiki.py` rather than expanding `entity.py`?**
`entity.py` is already large. The three planned wiki commands (`reindex`,
`lint`, `rename`) form a coherent tool group; giving them their own CLI
module keeps the entity module focused on entity lifecycle and the wiki
module focused on wiki maintenance tooling. This decision is consistent
with how `board.py`, `orch.py`, etc. are split.

**Why `entity_repo.py` for business logic?**
`entity_repo.py` owns the wiki directory structure (subdirectory layout,
template rendering, page creation). Scanning those same directories and
regenerating the index belongs naturally alongside that existing
knowledge.

**Index regeneration strategy:** Parse the existing `index.md` first to
extract manually-written summaries. Then scan all wiki pages, group them
by section (Core / Domain / Projects / Techniques / Relationships), sort
alphabetically by title within each section, and generate a fresh
`index.md` that re-uses preserved summaries where available and leaves
new-page summary cells empty. This preserves manual work while
mechanically fixing membership.

All code follows TDD per `docs/trunk/TESTING_PHILOSOPHY.md`: failing
tests are written before implementation.

## Subsystem Considerations

No documented subsystems are directly relevant. The `frontmatter` module
is used (DEC-008) for parsing page frontmatter.

## Sequence

### Step 1: Update GOAL.md code_paths

Before writing any code, update `docs/chunks/wiki_reindex_command/GOAL.md`
frontmatter to reflect the actual files that will be created/modified:

```yaml
code_paths:
- src/cli/wiki.py
- src/main.py
- src/entity_repo.py
- tests/test_entity_wiki_reindex.py
```

### Step 2: Write failing tests

Create `tests/test_entity_wiki_reindex.py` covering the success criteria
from the chunk GOAL.

**Test setup helper**: A `make_wiki_entity(tmp_path, pages)` fixture that
creates a minimal wiki directory structure:

```
tmp_path/
  wiki/
    index.md          ← may start empty or with some rows
    wiki_schema.md    ← stub (should be excluded from pages)
    identity.md       ← core page
    log.md            ← core page
    domain/
      caching.md      ← example domain page
    techniques/
      refactoring.md  ← example techniques page
    projects/
      alpha.md        ← example project page
    relationships/
      alice.md        ← example relationship page
```

Each `.md` file should have minimal YAML frontmatter:
```markdown
---
title: Page Title
created: 2026-01-01T00:00:00+00:00
updated: 2026-01-01T00:00:00+00:00
---
Body content here.
```

**Tests to write (all must fail before implementation):**

```python
class TestReindexWiki:

    def test_reindex_produces_index_md(self, tmp_path):
        """After reindex, index.md exists in the wiki dir."""

    def test_reindex_includes_all_sections(self, tmp_path):
        """Generated index contains Core, Domain, Projects, Techniques,
        Relationships section headers."""

    def test_reindex_lists_pages_by_directory(self, tmp_path):
        """Pages in domain/ appear in Domain section, pages in
        techniques/ appear in Techniques section, etc."""

    def test_reindex_excludes_index_and_schema(self, tmp_path):
        """index.md and wiki_schema.md are not listed as pages."""

    def test_reindex_alphabetical_order(self, tmp_path):
        """Within each section, pages are sorted alphabetically by title."""

    def test_reindex_overwrites_existing_index(self, tmp_path):
        """An existing index.md with stale rows is replaced entirely."""

    def test_reindex_preserves_existing_summaries(self, tmp_path):
        """Summaries from the existing index are kept for pages that
        still exist after reindex."""

    def test_reindex_returns_page_count(self, tmp_path):
        """reindex_wiki() returns a result with correct pages_total."""

    def test_reindex_empty_subdirectory(self, tmp_path):
        """Sections with no pages render an empty table (headers only),
        not an error."""
```

**CLI smoke test** (in the same file):
```python
class TestWikiReindexCli:

    def test_cli_reindex_exits_zero(self, runner, tmp_path):
        """ve wiki reindex <entity> exits 0 for a valid wiki entity."""

    def test_cli_reindex_missing_entity_exits_nonzero(self, runner, tmp_path):
        """ve wiki reindex for an unknown entity exits non-zero."""
```

Run `uv run pytest tests/test_entity_wiki_reindex.py` — all tests must
fail at this point (import errors are acceptable; assertion failures are
the goal).

### Step 3: Implement `reindex_wiki` in `src/entity_repo.py`

Add the following to `entity_repo.py` (near existing wiki-related code):

**3a. Result dataclass**

```python
# Chunk: docs/chunks/wiki_reindex_command - Result of wiki reindex operation
@dataclass
class WikiReindexResult:
    pages_total: int          # total pages written to index
    directories_scanned: int  # number of subdirectories scanned
```

**3b. Helper: parse existing summaries**

```python
def _parse_existing_summaries(index_path: Path) -> dict[str, str]:
    """Extract page→summary mapping from existing index.md.

    Parses markdown table rows of the form:
        | [[page_stem]] | summary text |
    Returns a dict mapping page stem to summary string.
    Returns empty dict if index doesn't exist or has no table rows.
    """
```

Implementation: read file line by line; use a simple regex
`r"\|\s*\[\[([^\]]+)\]\]\s*\|\s*(.*?)\s*\|"` to extract stem → summary
pairs.

**3c. Helper: scan wiki pages**

```python
def _scan_wiki_pages(wiki_dir: Path) -> dict[str, list[dict]]:
    """Scan wiki directory and return pages grouped by section.

    Returns:
        {
            "core": [{"stem": ..., "title": ..., "path": ...}, ...],
            "domain": [...],
            "techniques": [...],
            "projects": [...],
            "relationships": [...],
        }
    Keys always present; values are lists (may be empty).
    """
```

Implementation:
- **Core pages**: glob `wiki_dir/*.md`, exclude `index.md` and
  `wiki_schema.md` (and `SOP.md` — it is operational meta, not content).
  Read frontmatter with `parse_frontmatter_from_content` (or plain
  `yaml.safe_load` on the extracted block) to get `title`; fall back to
  `Path.stem.replace("_", " ").title()` if frontmatter is absent.
- **Subdirectory pages**: for each of `domain`, `techniques`, `projects`,
  `relationships`, glob `wiki_dir/<subdir>/*.md`.  Read frontmatter the
  same way.
- Sort each list by `title` (case-insensitive).

**3d. Helper: generate index markdown**

```python
def _generate_index_md(
    sections: dict[str, list[dict]],
    summaries: dict[str, str],
    entity_name: str,
) -> str:
    """Render the full index.md content from scanned pages."""
```

Output format mirrors the template:

```markdown
---
title: Wiki Index — {entity_name}
updated: {now_iso}
---

# Wiki Index

Personal knowledge base for `{entity_name}`.

<!-- Keep this index current. Every page you create should appear here. One-line summaries only. -->

## Core

| Page | Summary |
|------|---------|
| [[identity]] | Who I am … |
| [[log]] | … |

## Domain Knowledge

| Page | Summary |
|------|---------|
| [[caching]] |  |

## Projects

…

## Techniques

…

## Relationships

…
```

Note: preserve the `created` field from the original `index.md` if
parseable; set `updated` to `datetime.now(timezone.utc).isoformat()`.
If no original exists, omit `created` from the frontmatter entirely.

**3e. Main function**

```python
# Chunk: docs/chunks/wiki_reindex_command - Regenerate index.md from page frontmatter
def reindex_wiki(wiki_dir: Path, entity_name: str | None = None) -> WikiReindexResult:
    """Regenerate wiki/index.md from page frontmatter.

    Scans all wiki pages, reads their frontmatter, and overwrites
    index.md with a fresh table grouped by directory. Existing
    summaries are preserved for pages that still exist.

    Args:
        wiki_dir: Path to the entity's wiki/ directory.
        entity_name: Optional entity name for the index title.
                     Falls back to wiki_dir.parent.name.

    Raises:
        FileNotFoundError: If wiki_dir does not exist.
    """
```

### Step 4: Create `src/cli/wiki.py`

```python
"""Wiki maintenance commands.

# Chunk: docs/chunks/wiki_reindex_command - wiki CLI command group
"""

import pathlib
import click
from entities import Entities
from entity_repo import reindex_wiki
from cli.entity import resolve_entity_project_dir


@click.group()
def wiki():
    """Wiki maintenance commands for entity knowledge bases."""
    pass


@wiki.command("reindex")
@click.argument("entity")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
    help="Project directory containing .entities/ (default: auto-detected)",
)
def reindex(entity: str, project_dir: pathlib.Path | None) -> None:
    """Regenerate wiki/index.md from page frontmatter.

    Scans all wiki pages for ENTITY and rewrites index.md, grouping
    pages by directory (domain, techniques, projects, relationships)
    and sorting alphabetically. Existing summaries are preserved.
    """
    project = resolve_entity_project_dir(project_dir)
    entities = Entities(project)

    if not entities.entity_exists(entity):
        raise click.ClickException(f"Entity '{entity}' not found")
    if not entities.has_wiki(entity):
        raise click.ClickException(
            f"Entity '{entity}' does not have a wiki/ directory"
        )

    wiki_dir = entities.entity_dir(entity) / "wiki"
    result = reindex_wiki(wiki_dir, entity_name=entity)

    click.echo(
        f"Reindexed wiki for '{entity}': "
        f"{result.pages_total} page(s) across {result.directories_scanned} section(s)"
    )
```

### Step 5: Register `wiki` in `src/main.py`

Add to `src/main.py`:

```python
from cli.wiki import wiki
# …
cli.add_command(wiki)
```

### Step 6: Run tests — all must pass

```bash
uv run pytest tests/test_entity_wiki_reindex.py -v
```

Fix any failures until the full suite is green. Also run the full test
suite to confirm no regressions:

```bash
uv run pytest tests/ -x
```

### Step 7: Manual smoke test

```bash
# Create a test entity with a wiki page
uv run ve entity create testbot --output-dir /tmp/testve
# Manually create a page in domain/ with frontmatter
mkdir -p /tmp/testve/testbot/wiki/domain
cat > /tmp/testve/testbot/wiki/domain/caching.md << 'EOF'
---
title: Caching
created: 2026-01-01T00:00:00+00:00
updated: 2026-01-01T00:00:00+00:00
---
Notes on caching strategies.
EOF
# Reindex
uv run ve wiki reindex testbot --project-dir /tmp/testve
# Verify
cat /tmp/testve/testbot/wiki/index.md
```

Confirm `caching` appears in the Domain section.

## Dependencies

No new library dependencies. Uses only stdlib (`pathlib`, `re`, `datetime`,
`yaml`) and existing project utilities (`parse_frontmatter`, `entities.py`,
`entity_repo.py`).

## Risks and Open Questions

- **SOP.md placement**: SOP.md is an operational meta-page, not content.
  The plan excludes it from the Core section. If the operator prefers it
  listed, this is a one-line change (remove from the exclusion set).

- **Summary extraction regex**: If existing index rows use non-standard
  formatting (e.g., bold titles, extra spaces), the simple regex may miss
  them. The fallback is an empty summary, which is acceptable — users will
  re-fill on the next manual edit. A more robust parser can be added later.

- **`created` field preservation**: The existing index.md may not have a
  `created` field in its frontmatter (if the entity was migrated from the
  legacy format). The implementation should handle `None` gracefully.

- **Optional integration with `ve entity shutdown`**: The GOAL notes this
  as a possibility. It is out of scope for this chunk; a future chunk or
  the entity_shutdown chunk can call `reindex_wiki` if desired.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
