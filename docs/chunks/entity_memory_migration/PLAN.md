

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Build a migration tool that reads the legacy `.entities/<name>/` directory
structure, synthesizes wiki pages from existing memories using the Anthropic
Messages API (following the same pattern as `entity_shutdown.py`), and writes
them into a freshly created entity repo (via `create_entity_repo` from
`entity_repo.py`).

The synthesis step is LLM-assisted: one API call produces `wiki/identity.md`
(from core/correction/autonomy memories + identity body), one produces the
`wiki/domain/` pages (domain-category memories), and one produces the
`wiki/techniques/` pages (skill/confirmation memories). Journal entries are
converted to `wiki/log.md` mechanically — no LLM needed. This matches the
investigation's finding that "the wiki update produced exactly the kind of
insight core memories should distill" — the LLM synthesis step bridges the gap
between raw memories and the structured wiki.

Legacy memories are preserved in the new repo's `memories/` directory and
sessions are copied to `episodic/`. The original `.entities/<name>/` directory
is never modified (non-destructive).

**Testing**: `read_legacy_entity` and `classify_memories` are tested against
real memory fixtures (no mocking). LLM-dependent functions are tested with a
`monkeypatch` on the `anthropic.Anthropic` client returning fixed stub content.
The migration integration test verifies structural correctness without caring
about wiki prose.

**Existing code this chunk builds on**:
- `entity_repo.py` → `create_entity_repo`, `ENTITY_REPO_NAME_PATTERN`,
  `_run_git`, `_git_commit_all`
- `entities.py` → `Entities.parse_memory` (reuse for reading legacy files)
- `entity_shutdown.py` → anthropic import guard pattern, `claude-sonnet-4-20250514` model
- `models/entity.py` → `MemoryFrontmatter`, `MemoryTier`, `MemoryCategory`, `EntityIdentity`
- `frontmatter.py` → `parse_frontmatter`

See `docs/investigations/entity_wiki_memory/prototypes/wiki_a/identity.md` for
the quality bar of synthesized wiki content. The GOAL's success criteria use
`58d36632-bf65-4ba3-8f34-481cf64e9701` as the canonical example UUID input.

## Subsystem Considerations

No existing subsystems are directly in scope. The `entity_repo.py` module (from
`entity_repo_structure`) is the foundational dependency — this chunk consumes
its `create_entity_repo` and git helpers.

## Sequence

### Step 1: Define data models in `entity_migration.py`

Create `src/entity_migration.py` with these data structures (no behavior yet):

```python
@dataclass
class LegacyMemory:
    tier: MemoryTier
    frontmatter: MemoryFrontmatter
    content: str
    file_path: Path

@dataclass
class ClassifiedMemories:
    identity: list[LegacyMemory]      # core tier + correction + autonomy
    domain: list[LegacyMemory]        # domain category
    techniques: list[LegacyMemory]    # skill + confirmation categories
    relationships: list[LegacyMemory] # coordination category
    log: list[LegacyMemory]           # journal tier (chronological)
    unclassified: list[LegacyMemory]  # anything that doesn't fit

@dataclass
class MigrationResult:
    entity_name: str
    source_dir: Path
    dest_dir: Path
    wiki_pages_created: list[str]
    memories_preserved: int
    sessions_migrated: int
    unclassified_count: int
```

Add module docstring with `# Chunk: docs/chunks/entity_memory_migration` backreference.

### Step 2: Implement `read_legacy_entity(entity_dir)`

```python
def read_legacy_entity(
    entity_dir: Path,
) -> tuple[EntityIdentity | None, str, list[LegacyMemory]]:
    """Read legacy entity structure.

    Returns:
        Tuple of (EntityIdentity|None, identity_body_text, list[LegacyMemory]).
        identity_body_text is the markdown body after frontmatter in identity.md.
    """
```

Implementation:
1. Parse `identity.md` frontmatter via `parse_frontmatter(identity_path, EntityIdentity)`
2. Read the body of `identity.md` using the same regex pattern as `Entities._read_body`
3. Walk `memories/journal/`, `memories/consolidated/`, `memories/core/` (in that order)
4. For each `.md` file, use `Entities.parse_memory()` (or its logic directly) to get `(MemoryFrontmatter, content)`
5. Build `LegacyMemory` with the tier inferred from the subdirectory name
6. Return `(identity, identity_body, memories)` — handles missing dirs gracefully (returns empty list)

### Step 3: Implement `classify_memories(memories)`

```python
def classify_memories(memories: list[LegacyMemory]) -> ClassifiedMemories:
```

Classification rules (applied to each memory):
- `identity`: tier == CORE **or** category in {CORRECTION, AUTONOMY}
- `domain`: category == DOMAIN (regardless of tier)
- `techniques`: category in {SKILL, CONFIRMATION}
- `relationships`: category == COORDINATION
- `log`: tier == JOURNAL (regardless of category)
- `unclassified`: anything not matched above

Note: a memory may appear in multiple buckets by design (e.g., a CORE-tier
DOMAIN memory goes into `identity` AND `domain`). The synthesis step handles
deduplication via LLM.

Sort `log` entries by filename (filenames are timestamp-prefixed, so this is
chronological order).

### Step 4: Implement `format_log_page(log_entries, created_date)` (mechanical, no LLM)

```python
def format_log_page(log_entries: list[LegacyMemory], created_date: str) -> str:
```

Converts journal-tier memories to chronological log format:
1. Start with the log.md template header (YAML frontmatter `title: Log`, `created`, `updated`)
2. Group entries by their `last_reinforced` date
3. For each date group, emit a `## YYYY-MM-DD` heading followed by
   bullet-formatted memory titles and content
4. If `log_entries` is empty, emit the template's placeholder entry

This function never calls an LLM. The output is deterministic.

### Step 5: Implement `synthesize_identity_page(identity, identity_body, memories, client)`

```python
def synthesize_identity_page(
    identity: EntityIdentity | None,
    identity_body: str,
    memories: list[LegacyMemory],
    client,  # anthropic.Anthropic instance
) -> str:
```

Builds a prompt that includes:
- All `identity` classified memories (formatted as title + content)
- The original `identity_body` text (if any)
- The entity's name and role
- Instructions to produce `wiki/identity.md` with standard sections:
  `## Who I Am`, `## Role`, `## Working Style`, `## Values`, `## Hard-Won Lessons`
- Instructions to use wikilinks `[[page_name]]` for cross-references
- YAML frontmatter requirements (`title`, `created`, `updated`)

Sends one `client.messages.create()` call with `model="claude-sonnet-4-20250514"`,
`max_tokens=2048`. Returns the response content as a string.

Guard the `anthropic` import at module level:
```python
try:
    import anthropic
except ModuleNotFoundError:
    anthropic = None
```

If `anthropic is None`, raise `RuntimeError("anthropic package not installed")`.

### Step 6: Implement `synthesize_knowledge_pages(memories, wiki_type, client)`

```python
def synthesize_knowledge_pages(
    memories: list[LegacyMemory],
    wiki_type: str,  # "domain" or "techniques"
    client,
) -> list[tuple[str, str]]:  # [(filename, content), ...]
```

Builds a prompt that includes:
- All memories in the `memories` list (title + category + content)
- `wiki_type` to communicate the target directory
- Instructions to group related memories into focused wiki pages (one concept per
  page) and return a **JSON array** of `{"filename": "...", "content": "..."}` objects
- Page naming convention: lowercase slug + `.md` (e.g., `proving_model.md`)
- YAML frontmatter requirement on each page
- Instruction to use wikilinks

Sends one `client.messages.create()` call. Parses the JSON response using the
same `strip_code_fences` + `json.loads` pattern from `entity_shutdown.py`.

Returns a list of `(filename, content)` tuples. Returns `[]` if `memories` is
empty (no LLM call needed).

### Step 7: Implement `migrate_entity(source_dir, dest_parent, new_name, role)`

```python
# Chunk: docs/chunks/entity_memory_migration - Full entity migration orchestration
def migrate_entity(
    source_dir: Path,
    dest_parent: Path,
    new_name: str,
    role: str | None = None,
) -> MigrationResult:
```

Full orchestration:

1. **Validate inputs**:
   - `source_dir.exists()` → `ValueError("Source entity directory not found: ...")`
   - `ENTITY_REPO_NAME_PATTERN.match(new_name)` → `ValueError("Invalid name: ...")`

2. **Read legacy entity**:
   - Call `read_legacy_entity(source_dir)` → `(identity, identity_body, memories)`
   - If `role is None` and `identity.role` exists, use `identity.role`

3. **Classify memories**: `classified = classify_memories(memories)`

4. **Create new entity repo**:
   - Call `create_entity_repo(dest_parent, new_name, role=role)` → `repo_path`
   - This creates the wiki stub pages (identity.md, index.md, log.md, wiki_schema.md)

5. **Synthesize and overwrite wiki pages** (only if anthropic is available):
   - Create `client = anthropic.Anthropic()`
   - Synthesize `wiki/identity.md` → overwrite stub
   - Synthesize `wiki/domain/` pages → write each to `repo_path / "wiki" / "domain" / filename`
   - Synthesize `wiki/techniques/` pages → write each to `repo_path / "wiki" / "techniques" / filename`
   - Format `wiki/log.md` mechanically → overwrite stub
   - If `anthropic is None`: keep the stub pages (warn to stderr, still migrate memories)

6. **Preserve legacy memories**:
   - Copy `source_dir/memories/` tree to `repo_path/memories/` using `shutil.copytree`
     with `dirs_exist_ok=True` (overwrites the empty tier subdirs created by `create_entity_repo`)

7. **Migrate sessions → episodic**:
   - If `source_dir/sessions/` exists, copy all `*.jsonl` files to `repo_path/episodic/`
   - Count migrated sessions

8. **Commit migration result**:
   - Stage all changes: `_run_git(repo_path, "add", "-A")`
   - Commit: `_run_git(repo_path, "commit", "--allow-empty", "-m", f"Migration: {source_dir.name} → {new_name}")`

9. **Build and return `MigrationResult`**:
   - `wiki_pages_created`: list of paths relative to `repo_path` that were written
   - `memories_preserved`: count of `.md` files copied from legacy `memories/`
   - `sessions_migrated`: count of `.jsonl` files copied
   - `unclassified_count`: `len(classified.unclassified)`

### Step 8: Add `ve entity migrate` CLI command in `src/cli/entity.py`

```python
# Chunk: docs/chunks/entity_memory_migration - Migration CLI command
@entity.command("migrate")
@click.argument("entity_name")
@click.option("--name", required=True, help="New human-readable entity name for the migrated repo")
@click.option("--role", default=None, help="Override entity role (default: read from identity.md)")
@click.option(
    "--entity-dir",
    type=click.Path(path_type=pathlib.Path),
    default=None,
    help="Path to legacy entity directory (default: .entities/<entity_name>/)",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=pathlib.Path),
    default=None,
    help="Parent directory for new entity repo (default: current directory)",
)
def migrate(entity_name, name, role, entity_dir, output_dir):
    """Migrate a legacy entity to the wiki-based git repo structure.

    ENTITY_NAME is the legacy entity identifier (UUID or name).
    --name is the new human-readable name for the migrated entity repo.

    Example:
        ve entity migrate 58d36632-bf65-4ba3-8f34-481cf64e9701 --name slack-watcher
    """
```

Implementation:
1. Resolve `entity_dir`:
   - If `--entity-dir` provided, use it directly
   - Else, `resolve_entity_project_dir(None) / ".entities" / entity_name`
2. Resolve `output_dir` to `Path.cwd()` if not provided
3. Call `entity_migration.migrate_entity(entity_dir, output_dir, name, role=role)`
4. Print structured migration summary:
   ```
   Migrated entity '<entity_name>' → '<name>'
     New repo:           <dest_dir>
     Wiki pages created: <n>
     Memories preserved: <n>
     Sessions migrated:  <n>
     Unclassified:       <n> (review manually)
   ```
5. Wrap `ValueError` and `RuntimeError` in `click.ClickException`

Import `entity_migration` at the top of the command function (lazy import, like `entity_shutdown`).

### Step 9: Write tests in `tests/test_entity_migration.py`

**Fixtures**: A `legacy_entity_dir` fixture that creates a minimal legacy entity
directory in `tmp_path` with:
- `identity.md` with valid `EntityIdentity` frontmatter and body text
- `memories/core/20260101_core_values.md` — one core memory (domain category)
- `memories/consolidated/20260102_domain_pattern.md` — one consolidated memory (domain)
- `memories/consolidated/20260103_skill_pattern.md` — one consolidated memory (skill)
- `memories/journal/20260104_session_note.md` — one journal memory (correction)
- `sessions/abc123.jsonl` — a dummy session file

**`TestReadLegacyEntity`** (no LLM):
- `test_reads_identity_when_present`: identity.name matches fixture
- `test_reads_all_memory_tiers`: returns memories from all three tiers
- `test_returns_empty_for_missing_memories_dir`: no crash on absent `memories/`
- `test_returns_identity_body_text`: body content extracted correctly

**`TestClassifyMemories`** (no LLM):
- `test_core_tier_memory_goes_to_identity`: core-tier memory → `classified.identity`
- `test_domain_category_goes_to_domain`: domain memory → `classified.domain`
- `test_skill_category_goes_to_techniques`: skill memory → `classified.techniques`
- `test_journal_tier_goes_to_log`: journal memory → `classified.log`
- `test_correction_category_goes_to_identity`: correction → `classified.identity`
- `test_log_sorted_chronologically`: journal entries sorted by filename

**`TestFormatLogPage`** (no LLM):
- `test_format_log_page_with_entries`: produced content includes session date and memory titles
- `test_format_log_page_empty`: returns valid markdown with placeholder entry

**`TestMigrateEntityStructure`** (mocked LLM):
Use `monkeypatch` to replace `anthropic.Anthropic` with a stub that returns
fixed wiki content for every `messages.create()` call. Verify:
- `test_migrate_creates_valid_git_repo`: git log shows two commits ("Initial entity state" + "Migration:")
- `test_migrate_wiki_pages_overwritten`: `wiki/identity.md` contains synthesized content (not just the stub)
- `test_migrate_preserves_memories`: `memories/core/*.md` exists in new repo
- `test_migrate_copies_sessions_to_episodic`: `episodic/abc123.jsonl` exists in new repo
- `test_migrate_returns_correct_result`: `MigrationResult.memories_preserved == 3` (matching fixture)

**`TestMigrateEntityEdgeCases`** (mocked LLM):
- `test_migrate_empty_entity`: entity with no memories succeeds, wiki/log.md has placeholder
- `test_migrate_only_core_memories`: no domain/technique pages created, identity.md written
- `test_migrate_invalid_new_name`: `ValueError` on names starting with digit or uppercase
- `test_migrate_nonexistent_source`: `ValueError` on missing source directory

**`TestMigrateCLI`** in `tests/test_entity_migrate_cli.py`:
Use Click's `CliRunner`. Monkeypatch `entity_migration.migrate_entity` to return
a fixed `MigrationResult`.
- `test_migrate_cli_success`: exit code 0, output contains new entity name and summary
- `test_migrate_cli_default_entity_dir_resolution`: resolves `.entities/<name>/` from project dir
- `test_migrate_cli_custom_entity_dir`: `--entity-dir` flag respected
- `test_migrate_cli_error_propagates`: `ValueError` from migration → non-zero exit + error message

### Step 10: Update `GOAL.md` code_paths

Add `src/entity_migration.py` and `tests/test_entity_migration.py` and
`tests/test_entity_migrate_cli.py` to the `code_paths` list in
`docs/chunks/entity_memory_migration/GOAL.md`.

## Dependencies

- `entity_repo_structure` chunk: `create_entity_repo`, `ENTITY_REPO_NAME_PATTERN`,
  `_run_git`, `_git_commit_all` must exist in `entity_repo.py` ✓ (already implemented)
- `entity_wiki_schema` chunk: wiki template stubs rendered by `create_entity_repo` ✓ (already implemented)
- `anthropic` package: already a project dependency (used in `entity_shutdown.py`)
- `shutil`: stdlib, no addition needed

## Risks and Open Questions

- **LLM grouping quality**: The `synthesize_knowledge_pages` prompt must cluster
  memories into coherent pages. With very few memories (1-3 domain memories), the
  LLM may produce just one page or empty output — the migration should handle this
  gracefully (empty list from `synthesize_knowledge_pages` is valid).

- **Anthropic not available**: The `anthropic` import guard handles this. When the
  package is absent, the stub wiki pages are kept rather than failing the whole
  migration. This matches the spirit of the non-destructive design constraint.

- **JSON parse failure from LLM**: `synthesize_knowledge_pages` must handle malformed
  JSON gracefully — fall back to an empty list and log a warning rather than crashing.

- **Large memory sets**: Entities with 50+ memories may produce prompts that exceed
  typical context windows. If `len(memories) > 30` in any bucket, truncate to the
  highest-salience entries (sort by `salience` descending, take top 30) and note
  the truncation in the migration summary.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
