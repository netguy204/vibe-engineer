

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add `ve entity ingest-transcript <name> <jsonl-paths...>` by creating a thin
public function `ingest_transcripts_into_entity()` in the existing
`entity_from_transcript.py` module (where the core pipeline already lives), then
wiring a new CLI command into `src/cli/entity.py`.

The core processing function `_process_subsequent_transcript()` already does
exactly what we need — wiki update → diff → consolidation → archive → commit.
This chunk reuses it unchanged except for a new `skip_consolidation` parameter.
The new public function wraps it with entity-existence / wiki-format validation
and the session-count bookkeeping that `from-transcript` handles internally.

Key design decisions:
- **Session numbering**: count existing files under `episodic/` before we start,
  then increment for each transcript we process.  This makes commit messages
  like "Session 7: wiki update from transcript" accurate for entities that
  already have history.
- **`--skip-consolidation`**: threaded as a boolean parameter from the CLI
  option down to `_process_subsequent_transcript()`.  Useful for batch-importing
  many transcripts before a single manual `ve entity shutdown`.
- **Legacy entity guard**: if `entities.has_wiki(name)` is False, raise
  `ValueError` with a message pointing the operator to `ve entity migrate`.

TDD workflow: write failing tests first, then implement.

## Subsystem Considerations

No new subsystem involvement.  This chunk USES the existing entity pipeline
(wiki update → consolidation) without adding cross-cutting concerns.

## Sequence

### Step 1: Write failing tests — `tests/test_entity_ingest_transcript.py`

Create the test file before any implementation.  Tests must fail (ImportError
or NameError are acceptable failure modes in the red phase).

Test cases to cover each success criterion:

**`TestIngestTranscriptsIntoEntity` (unit tests, mocking the Agent SDK)**

- `test_single_transcript_calls_wiki_update_agent` — ingest one JSONL; verify
  `_process_subsequent_transcript` is called once with the correct entity_dir
  and jsonl_path.
- `test_multiple_transcripts_processed_in_order` — ingest three JSONLs; verify
  they are processed in submission order and session numbers are sequential.
- `test_legacy_entity_raises_value_error` — entity exists but has no `wiki/`
  dir; assert `ValueError` with "migrate" in the message.
- `test_nonexistent_entity_raises_value_error` — entity does not exist at all;
  assert `ValueError`.
- `test_transcripts_archived_in_episodic` — after ingest, verify each JSONL
  appears under `episodic/` in the entity repo.
- `test_skip_consolidation_flag` — ingest with `skip_consolidation=True`; verify
  the consolidation agent (`_run_consolidation_agent`) is NOT called.
- `test_session_numbering_continues_from_existing_episodic` — entity already has
  2 files in `episodic/`; first ingest should use session_n=3.

**`TestIngestTranscriptCLI` (CLI integration tests with `CliRunner`)**

- `test_cli_single_transcript_exits_zero` — happy path; stub Agent SDK; assert
  exit code 0 and output contains entity name.
- `test_cli_legacy_entity_exits_nonzero` — entity exists without wiki/; assert
  non-zero exit and error message mentions "migrate".
- `test_cli_skip_consolidation_flag` — `--skip-consolidation` passed; verify
  consolidation agent not called.
- `test_cli_missing_file_exits_nonzero` — JSONL path doesn't exist; assert
  non-zero exit.

Tests that require Agent SDK calls should use `unittest.mock.patch` on
`entity_from_transcript._run_wiki_agent` (already used in
`test_entity_from_transcript.py`).  Check `conftest.py` for any existing agent
mock fixtures before writing new ones.

Location: `tests/test_entity_ingest_transcript.py`

---

### Step 2: Add `skip_consolidation` parameter to `_process_subsequent_transcript()`

In `src/entity_from_transcript.py`, update the signature of
`_process_subsequent_transcript()`:

```python
def _process_subsequent_transcript(
    entity_dir: Path,
    entity_name: str,
    jsonl_path: Path,
    session_n: int,
    project_context: str | None,
    skip_consolidation: bool = False,   # ← new
) -> None:
```

In the body, guard the consolidation block:

```python
# Step 7. Consolidation (if wiki changed and not skipped)
if wiki_diff.strip() and not skip_consolidation:
    consolidation_prompt = _build_consolidation_prompt(entity_name, wiki_diff)
    asyncio.run(_run_consolidation_agent(entity_dir, consolidation_prompt))
```

No other changes to this function.

---

### Step 3: Add `IngestTranscriptResult` dataclass

In `src/entity_from_transcript.py`, add a result type alongside the existing
`FromTranscriptResult`:

```python
@dataclass
class IngestTranscriptResult:
    """Result of an ingest_transcripts_into_entity call."""
    entity_name: str
    entity_path: Path
    transcripts_processed: int
    sessions_archived: int
    wiki_pages_total: int   # count of *.md files under wiki/ after processing
```

---

### Step 4: Implement `ingest_transcripts_into_entity()`

In `src/entity_from_transcript.py`, add the public function:

```python
# Chunk: docs/chunks/entity_ingest_transcript - Ingest transcripts into existing entity
def ingest_transcripts_into_entity(
    name: str,
    jsonl_paths: list[Path],
    project_dir: Path,
    project_context: str | None = None,
    skip_consolidation: bool = False,
) -> IngestTranscriptResult:
```

Implementation steps inside the function:

1. **Validate paths**: each path in `jsonl_paths` must exist; raise
   `FileNotFoundError` if not.
2. **Validate Agent SDK** (same pattern as `create_entity_from_transcript`):
   if `ClaudeSDKClient is None`, raise `RuntimeError` with install hint.
3. **Resolve entity directory**: use `Entities(project_dir).entity_dir(name)`.
4. **Validate entity exists**: `entities.entity_exists(name)`; raise
   `ValueError(f"Entity '{name}' not found")` if missing.
5. **Validate wiki-based**: `entities.has_wiki(name)`; raise `ValueError` with
   message suggesting `ve entity migrate` if legacy.
6. **Determine starting session_n**: count `*.jsonl` files under `episodic/` in
   the entity repo (these represent existing archived sessions).  First new
   session is `existing_count + 1`.
7. **Process each transcript**: call `_process_subsequent_transcript(entity_dir,
   name, path, session_n, project_context, skip_consolidation)`, incrementing
   `session_n` after each.
8. **Compute wiki page count**: `len(list((entity_dir / "wiki").glob("**/*.md")))`.
9. **Return** `IngestTranscriptResult(...)`.

---

### Step 5: Add the CLI command `ingest-transcript`

In `src/cli/entity.py`, add a new command after the existing `ingest` command:

```python
# Chunk: docs/chunks/entity_ingest_transcript - Wiki-aware transcript ingest CLI
@entity.command("ingest-transcript")
@click.argument("name")
@click.argument("jsonl_paths", nargs=-1, required=True, type=click.Path(path_type=pathlib.Path))
@click.option("--project-context", default=None, help="Context about the project the transcripts came from")
@click.option("--skip-consolidation", is_flag=True, default=False,
              help="Update wiki only, skip memory consolidation (useful for batch imports)")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=None)
def ingest_transcript(
    name: str,
    jsonl_paths: tuple[pathlib.Path, ...],
    project_context: str | None,
    skip_consolidation: bool,
    project_dir: pathlib.Path | None,
) -> None:
    """Ingest session transcripts into an existing wiki-based entity.

    NAME is the entity identifier.
    JSONL_PATHS are Claude Code session transcript files, processed in order.

    Unlike 've entity ingest' (episodic-only), this command updates the entity's
    wiki and runs the full consolidation pipeline for each transcript — as if the
    entity had been active during those sessions.

    Use --skip-consolidation to update the wiki without running memory
    consolidation (useful when batch-importing many transcripts; run
    've entity shutdown' afterwards to consolidate once).
    """
    import entity_from_transcript as _eft

    project_dir = resolve_entity_project_dir(project_dir)

    try:
        result = _eft.ingest_transcripts_into_entity(
            name=name,
            jsonl_paths=list(jsonl_paths),
            project_dir=project_dir,
            project_context=project_context,
            skip_consolidation=skip_consolidation,
        )
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        raise click.ClickException(str(e))

    click.echo(f"Ingested {result.transcripts_processed} transcript(s) into entity '{result.entity_name}':")
    click.echo(f"  Sessions archived: {result.sessions_archived}")
    click.echo(f"  Wiki pages total:  {result.wiki_pages_total}")
    if skip_consolidation:
        click.echo("  Note: consolidation skipped — run 've entity shutdown' to consolidate.")
```

---

### Step 6: Update `GOAL.md` code_paths

Update `docs/chunks/entity_ingest_transcript/GOAL.md` frontmatter to include
any additional source files touched:

```yaml
code_paths:
- src/cli/entity.py
- src/entity_from_transcript.py
```

These were already listed; no change needed unless other files are touched
during implementation.

---

### Step 7: Run tests and verify green

```bash
uv run pytest tests/test_entity_ingest_transcript.py -v
uv run pytest tests/test_entity_from_transcript.py -v   # regression check
uv run pytest tests/ -v                                   # full suite
```

All tests should pass.  Fix any failures before proceeding to chunk completion.

---

## Dependencies

- `entity_from_transcript` chunk must be complete (it is — listed as
  `depends_on` in GOAL.md).
- `entity_shutdown_wiki` chunk must be complete (it is — `_run_consolidation_agent`
  and `_build_consolidation_prompt` are already present in `entity_shutdown.py`).
- `claude_agent_sdk` package must be available at runtime (same requirement as
  `from-transcript`; existing guard pattern handles missing SDK).

## Risks and Open Questions

- **Session numbering accuracy**: counting `episodic/*.jsonl` files assumes each
  archived session corresponds to one file (the same assumption `from-transcript`
  makes).  If an entity was created with legacy ingest (copies files without JSONL
  extension), the count may be off.  This is cosmetic — commit message labels are
  not semantically load-bearing.
- **Entity in submodule vs. standalone**: `Entities.entity_dir()` resolves the
  entity under `.entities/<name>/` in the project.  Entities created via
  `from-transcript` and not yet attached to a project will not be found this way.
  The `--project-dir` option works only for attached entities.  This is
  consistent with how `shutdown` and `startup` work — document in the command's
  help text if needed.
- **Large transcript sets**: each transcript spawns an Agent SDK session with
  `max_turns=80`.  For large batches this may take a long time.  No buffering
  or parallelism is needed for v1.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
