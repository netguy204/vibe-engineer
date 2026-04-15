

# Implementation Plan

## Approach

This chunk is purely additive: create new Jinja2 template files and extend `Entities.create_entity()` to render them. No existing behavior changes.

The three templates (`wiki_schema.md.jinja2`, `wiki/identity.md.jinja2`, `wiki/index.md.jinja2`, `wiki/log.md.jinja2`) are Jinja2 files in `src/templates/entity/`. They follow the conventions already established by `src/templates/entity/identity.md.jinja2`.

`create_entity()` in `src/entities.py` already uses `render_template()` to produce files in the entity directory. We extend it to also render the four wiki templates, creating `wiki/` alongside the existing `identity.md` and `memories/` directories.

The wiki schema template (`wiki_schema.md`) is the "CLAUDE.md for the wiki" — an instruction document rendered inside `wiki/` that tells the entity how to maintain its wiki during sessions. It has no Jinja2 variables (it is entity-agnostic prose); the other three page templates receive `name`, `role`, and `created` for their frontmatter.

The investigation's three prototype wikis (`wiki_a/`, `wiki_b/`, `wiki_uniharness/`) are the golden references. The schema and page templates must match the conventions observed in those prototypes.

No new decision needs to be added to DECISIONS.md — this is a straightforward template addition using the existing `render_template()` pattern (DEC-009).

## Subsystem Considerations

No subsystems are relevant — this chunk adds template files and extends a single method. The template rendering system is used but not modified.

## Sequence

### Step 1: Write the wiki schema template

Create `src/templates/entity/wiki_schema.md.jinja2`.

This is the instruction document that tells the entity how to maintain its wiki. It has no Jinja2 variables — it is pure markdown prose. The content should cover:

- **Directory structure**: The canonical layout (`index.md`, `identity.md`, `log.md`, `domain/`, `projects/`, `techniques/`, `relationships/`) with one-line purpose descriptions for each.
- **Page conventions**: YAML frontmatter (`title`, `created`, `updated` minimum), wikilinks (`[[page_name]]`), page size guideline (~500 words, split when exceeded), one concept per page.
- **What to capture by category**:
  - `identity.md`: role, strengths, working style, values, hard-won lessons — especially lessons from failures and adversity
  - `domain/` pages: concepts, how they relate, key facts, open questions
  - `techniques/` pages: what it is, when to use it, pitfalls, examples from experience
  - `projects/` pages: goals, constraints, current state, key decisions made
  - `relationships/` pages: who they are, what they do, how you work with them
  - `log.md`: chronological session record, format `## [YYYY-MM-DD] session | Brief summary` with subsections Task, What Happened, Key Learnings
- **Maintenance workflow**: Maintain the wiki _during_ the session as a natural part of working (not as a separate post-session step). When you learn something, update the relevant page. When you complete a session, add a log entry.
- **Index maintenance**: `index.md` is the content catalog. Every page must have a row in the index table for its category. Keep summaries to one line. Update the index when creating a new page.
- **Page operations**: When to create a new page (new distinct concept), when to update an existing one (refinement, new examples, corrected understanding), when to split (page exceeds ~500 words and covers multiple separable concepts).
- **Cross-references**: Use `[[page_name]]` for references within the same directory level, `[[domain/topic]]` for cross-directory references.
- **Ingest signal**: The entity should treat every discovery, failure, correction, and hard-won insight as a wiki update trigger. The most valuable content comes from adversity.

Location: `src/templates/entity/wiki_schema.md.jinja2`

Backreference: `{# Chunk: docs/chunks/entity_wiki_schema - Wiki schema instruction document for entity self-maintenance #}`

### Step 2: Write the wiki/identity.md page template

Create `src/templates/entity/wiki/identity.md.jinja2`.

This template renders the initial `wiki/identity.md` page for a new entity. It receives the same variables already used by `identity.md.jinja2`: `name`, `role`, and `created`.

Frontmatter:
```yaml
title: Identity
created: {{ created }}
updated: {{ created }}
```

Sections (based on the prototype `wiki_a/identity.md`):
- **Who I Am**: Placeholder text acknowledging this is populated as the entity works; starts minimal
- **Role**: Render `{{ role }}` if provided, otherwise a placeholder
- **Working Style**: Empty skeleton with prompt ("Document how you approach work — methodologies, phase structures, decision patterns")
- **Values**: Empty skeleton ("Document what you optimize for — what tradeoffs you make, what you refuse to compromise on")
- **Hard-Won Lessons**: Empty skeleton ("This section becomes your most valuable asset — document failures, surprising discoveries, and corrected assumptions. Especially capture lessons from adversity.")

The template should guide the entity to fill it in, not pre-fill it with generic content.

Location: `src/templates/entity/wiki/identity.md.jinja2`

Backreference: `{# Chunk: docs/chunks/entity_wiki_schema - Initial identity page template for entity wiki #}`

### Step 3: Write the wiki/index.md page template

Create `src/templates/entity/wiki/index.md.jinja2`.

This template renders the initial `wiki/index.md` — the content catalog that the entity reads at startup to orient itself. It receives `name` and `created`.

Frontmatter:
```yaml
title: Wiki Index — {{ name }}
created: {{ created }}
updated: {{ created }}
```

Content:
- Brief description: "Personal knowledge base for `{{ name }}`."
- **Core** table with rows for `[[identity]]` and `[[log]]`
- **Domain Knowledge** table — empty (placeholder row or empty table with comment)
- **Projects** table — empty
- **Techniques** table — empty
- **Relationships** table — empty

Each table uses the two-column format from the prototype (`| Page | Summary |`).

Add a comment block instructing the entity: "Keep this index current. Every page you create should appear here. One-line summaries only."

Location: `src/templates/entity/wiki/index.md.jinja2`

Backreference: `{# Chunk: docs/chunks/entity_wiki_schema - Initial index page template for entity wiki #}`

### Step 4: Write the wiki/log.md page template

Create `src/templates/entity/wiki/log.md.jinja2`.

This template renders the initial `wiki/log.md` — the chronological session log. It receives `created`.

Frontmatter:
```yaml
title: Session Log
created: {{ created }}
updated: {{ created }}
```

Content:
- A brief description: "Chronological record of sessions. Add an entry at the end of each session."
- Format instructions: `## [YYYY-MM-DD] session | Brief summary` header, then `### Task`, `### What Happened`, `### Key Learnings` subsections
- One example entry that is clearly marked as an example/template (use a comment or a visually distinct placeholder), so the entity understands the format without being confused about whether the example reflects real history

Location: `src/templates/entity/wiki/log.md.jinja2`

Backreference: `{# Chunk: docs/chunks/entity_wiki_schema - Initial log page template for entity wiki #}`

### Step 5: Extend create_entity() to render wiki templates

Modify `src/entities.py` → `Entities.create_entity()`.

After creating the `memories/` tier directories, also:

1. Create the `wiki/` directory and subdirectories:
   ```python
   wiki_dir = entity_path / "wiki"
   wiki_dir.mkdir()
   for subdir in ["domain", "projects", "techniques", "relationships"]:
       (wiki_dir / subdir).mkdir()
   ```

2. Render and write `wiki/wiki_schema.md` from `wiki_schema.md.jinja2` (no variables needed):
   ```python
   schema_content = render_template("entity", "wiki_schema.md.jinja2")
   (wiki_dir / "wiki_schema.md").write_text(schema_content)
   ```

3. Render and write the three page templates (all receive `name`, `role`, `created`):
   ```python
   for template_name, output_path in [
       ("wiki/identity.md.jinja2", wiki_dir / "identity.md"),
       ("wiki/index.md.jinja2",    wiki_dir / "index.md"),
       ("wiki/log.md.jinja2",      wiki_dir / "log.md"),
   ]:
       content = render_template("entity", template_name, name=name, role=role, created=created)
       output_path.write_text(content)
   ```

Update the module docstring to include `wiki/` in the documented directory structure.

Add a backreference comment at the extension point: `# Chunk: docs/chunks/entity_wiki_schema - Wiki directory initialization`

### Step 6: Update GOAL.md code_paths

Update `docs/chunks/entity_wiki_schema/GOAL.md` `code_paths` to include:
- `src/templates/entity/wiki_schema.md.jinja2`
- `src/templates/entity/wiki/identity.md.jinja2`
- `src/templates/entity/wiki/index.md.jinja2`
- `src/templates/entity/wiki/log.md.jinja2`
- `src/entities.py` (modified)
- `tests/test_entities.py` (modified)

These paths were listed in the GOAL.md frontmatter already for the first four. Add `src/entities.py` and `tests/test_entities.py`.

### Step 7: Write tests

Extend `tests/test_entities.py` with a new `TestCreateEntityWiki` class. Tests to write (TDD order — write failing tests first, then implement):

**Structural tests** (verify wiki directory creation):

- `test_creates_wiki_directory`: `create_entity()` creates `wiki/` directory
- `test_creates_wiki_subdirectories`: `wiki/domain/`, `wiki/projects/`, `wiki/techniques/`, `wiki/relationships/` all exist
- `test_creates_wiki_initial_pages`: `wiki/wiki_schema.md`, `wiki/identity.md`, `wiki/index.md`, `wiki/log.md` all exist

**Content tests** (verify meaningful properties of rendered output):

- `test_wiki_schema_mentions_directory_structure`: `wiki_schema.md` contains "domain", "projects", "techniques", "relationships" (the directory names) — verifies schema document describes the structure
- `test_wiki_schema_mentions_wikilinks`: `wiki_schema.md` contains `[[` — verifies wikilink convention is documented
- `test_wiki_schema_mentions_log_format`: `wiki_schema.md` contains `YYYY-MM-DD` — verifies log entry format is documented
- `test_wiki_identity_contains_entity_name`: `wiki/identity.md` contains the entity name passed to `create_entity()`
- `test_wiki_identity_valid_frontmatter`: `wiki/identity.md` has parseable YAML frontmatter with `title`, `created`, `updated`
- `test_wiki_index_contains_identity_link`: `wiki/index.md` contains `[[identity]]`
- `test_wiki_index_contains_log_link`: `wiki/index.md` contains `[[log]]`
- `test_wiki_index_valid_frontmatter`: `wiki/index.md` has parseable YAML frontmatter
- `test_wiki_log_valid_frontmatter`: `wiki/log.md` has parseable YAML frontmatter with `title`, `created`, `updated`
- `test_wiki_log_contains_format_example`: `wiki/log.md` contains `YYYY-MM-DD` — the log format is documented/exemplified

Use the existing `temp_project` fixture and the `entities` fixture already defined in `test_entities.py`. Parse frontmatter via `yaml.safe_load()` on the lines between `---` delimiters — no need to import the full frontmatter module.

## Dependencies

No external dependencies. All required infrastructure (`render_template`, `Entities`, `MemoryTier`, test fixtures) already exists.

## Risks and Open Questions

- **Template subdirectory resolution**: `render_template("entity", "wiki/identity.md.jinja2")` — verify that the `render_template()` function handles subdirectory template paths correctly. If it doesn't, we may need to use `"wiki_identity.md.jinja2"` (flat names) or adjust the template lookup. Read `src/template_system.py` before implementing Step 5 to confirm.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION, not at planning time. -->
