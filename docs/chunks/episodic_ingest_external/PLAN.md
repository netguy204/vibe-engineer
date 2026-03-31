

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add a new `ve entity ingest` CLI subcommand that copies externally-sourced Claude
Code JSONL session transcripts into an entity's `sessions/` directory. The command
validates each file is parseable by the existing `parse_session_jsonl()` from
`entity_transcript.py`, copies valid files with an `ingested_` prefix (to avoid
collision with `ve entity claude`-archived sessions), and reports results.

The existing `EpisodicStore.build_or_update()` already discovers all `*.jsonl`
files in the sessions directory and indexes any it hasn't seen before, so no
changes to the indexing pipeline are needed — ingested files are automatically
picked up on the next `--query`.

**Patterns used:**
- Follow the existing Click subcommand pattern in `src/cli/entity.py` (argument
  for entity name, `--project-dir` option, `resolve_entity_project_dir()`)
- Use `parse_session_jsonl()` for validation — if it returns a `SessionTranscript`
  with at least one turn, the file is valid
- Use `shutil.copy2` for file copying (same as `archive_transcript()`)
- Accept glob expansion via Python's `glob.glob()` since shell glob expansion may
  not happen when the argument is quoted

**Testing strategy (per TESTING_PHILOSOPHY.md):**
- TDD: write failing tests first, then implement
- Test meaningful behavior: file actually copied, invalid file skipped with warning,
  glob expansion works, duplicate handling
- CLI integration tests via Click's `CliRunner`

## Subsystem Considerations

No documented subsystems exist yet. No subsystem-level patterns are relevant.

## Sequence

### Step 1: Write failing tests for the ingest command

Location: `tests/test_entity_ingest.py`

Create CLI integration tests using Click's `CliRunner` following the pattern in
`tests/test_entity_episodic_cli.py`. Use the existing `_make_session_jsonl` helper
pattern (copy it or extract to conftest if it already exists there).

Tests to write:

1. **Single file ingest** — `ve entity ingest steward /path/to/session.jsonl`
   copies the file into `.entities/steward/sessions/ingested_<stem>.jsonl` and
   prints a success message. Verify the file exists and has the same content.

2. **Glob ingest** — `ve entity ingest steward "/path/to/*.jsonl"` ingests
   multiple files. Verify all valid files are copied.

3. **Invalid file rejection** — A file with non-JSON content or missing required
   fields is skipped with a warning on stderr, and the exit code is still 0
   (partial success).

4. **Duplicate ingest** — Ingesting the same file twice should either skip with
   a message ("already ingested") or overwrite silently. Choose skip-with-warning
   since it's more informative.

5. **Nonexistent entity** — Returns an error if the entity doesn't exist.

6. **Nonexistent file** — Returns an error/warning if the path matches no files.

7. **Episodic search picks up ingested files** — After ingesting, running
   `EpisodicStore.build_or_update()` and then `.search()` returns hits from the
   ingested content. This is the end-to-end success criterion.

### Step 2: Implement the `ingest_files` function on `EpisodicStore`

Location: `src/entity_episodic.py`

Add a method to `EpisodicStore` that handles the core logic (separate from CLI
concerns for testability):

```python
# Chunk: docs/chunks/episodic_ingest_external - External transcript ingest
def ingest_files(self, paths: list[Path]) -> IngestResult:
```

Where `IngestResult` is a simple dataclass:

```python
@dataclass
class IngestResult:
    ingested: list[str]   # stems of successfully ingested files
    skipped: list[str]    # stems skipped (invalid or duplicate)
    errors: list[str]     # human-readable error messages
```

Logic:
1. Ensure `self.sessions_dir` exists (create if needed)
2. For each path:
   a. Check it exists and is a file
   b. Try `parse_session_jsonl(path)` — if it raises or returns 0 turns, skip
   c. Compute destination: `sessions_dir / f"ingested_{path.stem}.jsonl"`
   d. If destination already exists, skip with "already ingested" message
   e. Copy with `shutil.copy2`
   f. Record in `ingested` list
3. Return `IngestResult`

### Step 3: Implement the `ve entity ingest` CLI command

Location: `src/cli/entity.py`

Add a new Click subcommand on the `entity` group:

```python
# Chunk: docs/chunks/episodic_ingest_external - External transcript ingest CLI
@entity.command("ingest")
@click.argument("name")
@click.argument("path", nargs=-1, required=True)
@click.option("--project-dir", ...)
def ingest(name, path, project_dir):
```

- Use `nargs=-1` so the user can pass multiple paths or a glob
- Expand globs with `glob.glob()` for each argument (handles quoted globs that
  the shell didn't expand)
- Resolve entity existence via `Entities`
- Delegate to `EpisodicStore.ingest_files()`
- Print summary: "Ingested N files, skipped M" and list details
- Print warnings for skipped files to stderr
- Exit 0 on partial success, exit 1 only if the entity doesn't exist or no
  paths were provided

### Step 4: Run tests and iterate

Run `uv run pytest tests/test_entity_ingest.py -v` and fix until all tests pass.

### Step 5: Update code_paths in GOAL.md

Add `tests/test_entity_ingest.py` to the `code_paths` frontmatter.

### Step 6: Add backreference comments

Ensure the new code has chunk backreferences:
- Module-level in `tests/test_entity_ingest.py`
- Method-level on `EpisodicStore.ingest_files` in `src/entity_episodic.py`
- Method-level on the `ingest` command in `src/cli/entity.py`

## Dependencies

All dependencies are already in the codebase:
- `entity_transcript.py` — `parse_session_jsonl()` for validation
- `entity_episodic.py` — `EpisodicStore` for sessions directory and indexing
- `entities.py` — `Entities` for entity existence checks
- `src/cli/entity.py` — entity command group to add the new subcommand to
- `shutil` — stdlib, for file copying
- `glob` — stdlib, for glob expansion

## Risks and Open Questions

- **Glob expansion in Click**: When the user quotes the glob (`"*.jsonl"`), the
  shell won't expand it. We need `glob.glob()` as a fallback. If the user doesn't
  quote it, the shell expands and Click receives multiple individual paths via
  `nargs=-1`. Both paths must work.
- **Large files**: `parse_session_jsonl()` reads the entire file. For very large
  transcripts this may be slow during validation. Acceptable for now since this
  is a manual operator command, not an automated pipeline.
- **`ingested_` prefix collision**: If the user ingests two files with the same
  stem from different directories, they'll collide. The skip-if-exists behavior
  handles this safely (warns rather than overwrites). If this becomes a real
  problem, a hash suffix could be added later.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->