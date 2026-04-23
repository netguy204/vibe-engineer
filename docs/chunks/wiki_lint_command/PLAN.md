
<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add `ve wiki lint <entity>` as a new top-level `wiki` command group (alongside `ve entity`,
`ve chunk`, etc.) defined in `src/cli/entity.py` and registered in `src/cli/__init__.py`.

The lint logic lives in `src/entity_repo.py` as a pure function `lint_wiki(wiki_dir: Path) ->
WikiLintResult` so that the CLI is thin and the logic is testable in isolation.

We follow TDD: write failing tests first, then implement until they pass.

The four checks:

1. **Dead wikilinks** — regex-extract `[[target]]` from every `.md` file; resolve each target
   to a file path (Obsidian shortest-path: bare `[[name]]` searches wiki tree for `name.md`;
   `[[dir/name]]` resolves to `wiki/dir/name.md`); report if missing.

2. **Frontmatter parse errors** — for every `.md` file except `wiki_schema.md` (which has no
   frontmatter by design), attempt a raw YAML parse of the frontmatter block. Report if
   the `---` delimiters are missing OR if YAML parsing raises an error.

3. **Pages missing from index** — extract all `[[target]]` wikilink targets from `index.md`;
   compare against content pages (those under `domain/`, `projects/`, `techniques/`,
   `relationships/`). Report content pages not referenced in `index.md`.

4. **Orphan pages** — build a map of inbound wikilinks for every page across the whole wiki
   (including links from `index.md`). Content pages with zero inbound links are orphans.

Output format: one issue per line, `<relative_path>: [<issue_type>] <detail>`.
Exit 0 if clean, exit 1 if any issues.

## Subsystem Considerations

No relevant subsystems in `docs/subsystems/` apply to this chunk. The `frontmatter.py`
module is used for raw YAML parsing; we reuse its `_FRONTMATTER_PATTERN` regex pattern
(or the exported `parse_frontmatter_from_content_with_errors`) rather than duplicating
it.

## Sequence

### Step 1: Write failing tests in `tests/test_entity_wiki_lint.py`

Create the test file with a `tmp_wiki` pytest fixture that builds a minimal wiki
directory structure (index.md, identity.md, wiki_schema.md, a couple of content pages
in `domain/`).

Tests to write (all should fail before implementation):

- **`test_clean_wiki_no_issues`** — a well-formed wiki with valid frontmatter, correct
  index entries, and at least one inbound wikilink per content page reports zero issues.

- **`test_dead_wikilink_detected`** — a page containing `[[nonexistent]]` reports one
  issue with `issue_type == "dead_wikilink"`.

- **`test_frontmatter_error_missing`** — a content page with no `---` frontmatter block
  reports one `"frontmatter_error"` issue.

- **`test_frontmatter_error_malformed`** — a content page whose frontmatter YAML is
  syntactically invalid (e.g. `key: [unclosed`) reports one `"frontmatter_error"` issue.

- **`test_missing_from_index`** — a content page under `domain/` with no corresponding
  `[[pagename]]` entry in `index.md` reports one `"missing_from_index"` issue.

- **`test_orphan_page`** — a content page with no inbound wikilinks from any other page
  (including `index.md`) reports one `"orphan_page"` issue.

- **`test_wiki_schema_exempt_from_frontmatter_check`** — `wiki_schema.md` (no frontmatter)
  does not trigger a `"frontmatter_error"` issue.

- **`test_structural_pages_exempt_from_index_and_orphan`** — `identity.md`, `log.md`,
  `SOP.md` are not reported as `"missing_from_index"` (they live in the Core section of
  index.md and are linked there, so they're covered by the orphan inbound-link count).

- **`test_cli_exit_code_clean`** — CLI runner invocation of `ve wiki lint <entity>` on a
  clean entity exits with code 0 and prints nothing to stdout.

- **`test_cli_exit_code_with_issues`** — CLI runner invocation on an entity with a dead
  wikilink exits with code 1 and prints one line containing `"dead_wikilink"`.

Location: `tests/test_entity_wiki_lint.py`

### Step 2: Add result dataclasses to `src/entity_repo.py`

Add near the top of entity_repo.py (after existing imports and dataclasses):

```python
# Chunk: docs/chunks/wiki_lint_command - Wiki integrity lint result types
@dataclasses.dataclass
class WikiLintIssue:
    file: str         # relative to wiki root, e.g. "domain/foo.md"
    issue_type: str   # "dead_wikilink" | "frontmatter_error" | "missing_from_index" | "orphan_page"
    detail: str       # human-readable description

@dataclasses.dataclass
class WikiLintResult:
    issues: list[WikiLintIssue]

    @property
    def ok(self) -> bool:
        return len(self.issues) == 0
```

`dataclasses` is already imported in entity_repo (or add the import if needed).

### Step 3: Implement `lint_wiki` and helpers in `src/entity_repo.py`

Add the following functions at the bottom of entity_repo.py.

#### 3a. `_extract_wikilinks(content: str) -> list[str]`

```python
_WIKILINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")

def _extract_wikilinks(content: str) -> list[str]:
    """Return all [[target]] link targets found in content."""
    return _WIKILINK_RE.findall(content)
```

#### 3b. `_resolve_wikilink(wiki_dir: Path, target: str) -> Path | None`

Resolution rules:
- If `target` contains `/` → look for `wiki_dir / target` (with `.md` appended if not present)
- If no `/` → search all `.md` files recursively under `wiki_dir` for one named `<target>.md`
  (Obsidian shortest-path). If multiple match, pick any (ambiguity is not an error for lint
  purposes; dead link check only needs existence).

```python
def _resolve_wikilink(wiki_dir: Path, target: str) -> Path | None:
    """Resolve a wikilink target to an absolute Path, or None if not found."""
    if not target.endswith(".md"):
        target_with_ext = target + ".md"
    else:
        target_with_ext = target

    if "/" in target:
        candidate = wiki_dir / target_with_ext
        return candidate if candidate.exists() else None
    else:
        # Obsidian shortest-path: find any file named <target>.md in the wiki tree
        for candidate in wiki_dir.rglob(target_with_ext):
            return candidate  # return first match
        return None
```

#### 3c. `_get_index_references(index_content: str) -> set[str]`

Extract all wikilink targets from index.md. Return a set of bare filenames (without `.md`)
for easy comparison.

```python
def _get_index_references(index_content: str) -> set[str]:
    """Return the set of wikilink targets referenced in index.md."""
    targets = _extract_wikilinks(index_content)
    return {t.split("/")[-1] for t in targets}  # bare name only
```

#### 3d. `lint_wiki(wiki_dir: Path) -> WikiLintResult`

```python
# Chunk: docs/chunks/wiki_lint_command - Wiki integrity linting
def lint_wiki(wiki_dir: Path) -> WikiLintResult:
    """Lint a wiki directory for integrity issues.

    Checks dead wikilinks, frontmatter errors, pages missing from index,
    and orphan pages (no inbound wikilinks).

    Args:
        wiki_dir: Path to the entity's wiki/ directory.

    Returns:
        WikiLintResult with zero or more issues.
    """
    import re as _re
    from frontmatter import _FRONTMATTER_PATTERN  # reuse existing regex

    issues: list[WikiLintIssue] = []

    # Structural pages that are always present and not expected to be content pages
    STRUCTURAL_NAMES = {"index.md", "wiki_schema.md", "identity.md", "log.md", "SOP.md"}
    # wiki_schema.md has no frontmatter by design
    NO_FRONTMATTER = {"wiki_schema.md"}

    all_pages = list(wiki_dir.rglob("*.md"))

    # Build inbound link map: rel_path -> set of source rel_paths
    inbound: dict[str, set[str]] = {
        str(p.relative_to(wiki_dir)): set() for p in all_pages
    }

    # --- Pass 1: per-page checks + populate inbound map ---
    for page in all_pages:
        rel = str(page.relative_to(wiki_dir))
        content = page.read_text(encoding="utf-8", errors="replace")

        # 1. Frontmatter check
        if page.name not in NO_FRONTMATTER:
            if not _FRONTMATTER_PATTERN.search(content):
                issues.append(WikiLintIssue(rel, "frontmatter_error", "missing frontmatter"))
            else:
                # Check YAML validity
                match = _FRONTMATTER_PATTERN.search(content)
                if match:
                    try:
                        yaml.safe_load(match.group(1))
                    except yaml.YAMLError as e:
                        issues.append(WikiLintIssue(rel, "frontmatter_error", f"invalid YAML: {e}"))

        # 2. Wikilink extraction + dead link check + inbound map population
        for target in _extract_wikilinks(content):
            resolved = _resolve_wikilink(wiki_dir, target)
            if resolved is None:
                issues.append(WikiLintIssue(rel, "dead_wikilink", f"[[{target}]] not found"))
            else:
                target_rel = str(resolved.relative_to(wiki_dir))
                if target_rel in inbound:
                    inbound[target_rel].add(rel)

    # --- Pass 2: index coverage check ---
    index_path = wiki_dir / "index.md"
    if index_path.exists():
        index_refs = _get_index_references(index_path.read_text(encoding="utf-8", errors="replace"))
        for page in all_pages:
            if page.name in STRUCTURAL_NAMES:
                continue
            if page.parent == wiki_dir:
                continue  # root-level non-structural files (unusual) — skip for now
            # Content pages are those in subdirectories: domain/, projects/, techniques/, relationships/
            rel = str(page.relative_to(wiki_dir))
            if page.stem not in index_refs:
                issues.append(WikiLintIssue(rel, "missing_from_index", "no entry in index.md"))

    # --- Pass 3: orphan check ---
    for page in all_pages:
        if page.name in STRUCTURAL_NAMES or page.parent == wiki_dir:
            continue  # exempt structural + root-level pages
        rel = str(page.relative_to(wiki_dir))
        if not inbound.get(rel):
            issues.append(WikiLintIssue(rel, "orphan_page", "no inbound wikilinks"))

    return WikiLintResult(issues=issues)
```

Note: `yaml` is already imported in entity_repo.py via frontmatter.py or directly. Confirm
and add `import yaml` at the top if needed.

Also confirm `import re` is present (it is — entity_repo uses it elsewhere).

### Step 4: Add `wiki` command group and `lint` command to `src/cli/entity.py`

At the **bottom** of entity.py (after all `entity` commands), add:

```python
# --- wiki command group ---
# Chunk: docs/chunks/wiki_lint_command - Top-level wiki command group

@click.group()
def wiki():
    """Wiki integrity and maintenance commands for entities."""
    pass


@wiki.command("lint")
@click.argument("entity_name")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
    help="Project directory (default: auto-detected from CWD)",
)
def wiki_lint(entity_name: str, project_dir: pathlib.Path | None) -> None:
    """Check wiki integrity for an entity.

    # Chunk: docs/chunks/wiki_lint_command - Wiki lint CLI command

    Checks for dead wikilinks, frontmatter errors, pages missing from
    the index, and orphan pages. Exits 0 if clean, 1 if issues found.

    Output format: one issue per line:
      <file>: [<type>] <detail>
    """
    project_dir = resolve_entity_project_dir(project_dir)
    entities = Entities(project_dir)

    if not entities.entity_exists(entity_name):
        raise click.ClickException(f"Entity '{entity_name}' not found")

    if not entities.has_wiki(entity_name):
        raise click.ClickException(
            f"Entity '{entity_name}' has no wiki directory. "
            "Only wiki-based entities can be linted."
        )

    wiki_dir = entities.entity_dir(entity_name) / "wiki"
    result = entity_repo.lint_wiki(wiki_dir)

    for issue in result.issues:
        click.echo(f"{issue.file}: [{issue.issue_type}] {issue.detail}")

    if not result.ok:
        raise SystemExit(1)
```

### Step 5: Register `wiki` in `src/cli/__init__.py`

Add to the import block and `add_command` section in `__init__.py`:

```python
from cli.entity import entity, wiki   # add `wiki` to existing import

# ...
cli.add_command(wiki)                 # add alongside entity
```

### Step 6: Run tests and fix until green

```bash
uv run pytest tests/test_entity_wiki_lint.py -v
```

Iterate on the implementation until all tests pass. Then run the full test suite to
ensure no regressions:

```bash
uv run pytest tests/ -x -q
```

## Dependencies

- `yaml` (already available as `pyyaml` dependency)
- `re` (stdlib)
- `frontmatter._FRONTMATTER_PATTERN` — reuse existing regex to avoid duplication
  (if importing private symbol feels wrong, inline the same pattern)

## Risks and Open Questions

- **Wikilink resolution ambiguity**: If two pages share the same stem in different
  directories (e.g. `domain/foo.md` and `techniques/foo.md`), `[[foo]]` is ambiguous.
  For lint purposes, we report "not dead" if any match is found (conservative: we don't
  want false positives for dead links). A future chunk could add an "ambiguous link" warning.

- **Index format variation**: The index.md template uses `[[pagename]]` wikilink syntax.
  If operators write index entries as plain text (not wikilinks), `_get_index_references`
  won't detect them, leading to false "missing from index" reports. Accept this tradeoff
  for now; the schema prescribes wikilink syntax.

- **Structural page exemptions**: The `STRUCTURAL_NAMES` set is hardcoded. If operators
  add custom root-level pages (not in `domain/`, etc.), they'll be silently skipped by
  the orphan and index checks. This is conservative (avoids false positives on unusual
  setups). Document in the command's `--help` if it becomes confusing.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION, not at planning time. -->
