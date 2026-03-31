

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add `ve entity claude --entity <name>` as a new subcommand in `src/cli/entity.py`.
The command orchestrates five phases using pieces already built in prior chunks:

1. **Launch** – `subprocess.Popen` with inherited stdio, capture PID and start time.
2. **Capture session ID** – read `~/.claude/sessions/<pid>.json` after exit.
3. **Archive** – `entities.archive_transcript(entity_name, session_id, project_path)`
4. **Shutdown** – try `claude --resume <sessionId> --prompt "/entity-shutdown <name>"`;
   if that exits non-zero or times out, fall back to `shutdown_from_transcript()`.
5. **Log + summarise** – `entities.append_session()` and print human-readable output.

All logic lives in a single new Click command plus a couple of small private helpers.
No new modules are needed: the entity CLI file is the right home for this command.

Following TDD: write failing tests first for each phase of the orchestration, then
implement until green.

## Subsystem Considerations

No documented subsystems are directly in scope. This chunk USES the entity memory
pipeline but does not modify it.

## Sequence

### Step 1: Read tests for existing entity CLI to understand patterns

Before writing any code, skim `tests/test_entity_cli.py` and
`tests/test_entity_shutdown_cli.py` to understand how the CliRunner is used and
what helpers exist in conftest. This informs test design for the new command.

### Step 2: Write failing tests in `tests/test_entity_claude_cli.py`

Create `tests/test_entity_claude_cli.py`. Each test uses `CliRunner` with
`mix_stderr=False`. Subprocess calls are patched so tests are fast and deterministic.

Key test cases to cover each success criterion:

**Launch / entity validation:**
- `test_errors_if_entity_missing` — `--entity nonexistent` → non-zero exit, message
  contains "not found"

**Session ID extraction:**
- `test_reads_session_id_from_pid_file` — unit test (no Click) for the helper
  `_read_session_id_from_pid_file(pid, claude_home)`: given a temp dir with
  a `sessions/<pid>.json` file containing `{"sessionId": "some-uuid", ...}`, asserts
  the helper returns `"some-uuid"`.
- `test_warns_when_pid_file_missing` — full command test; pid file absent → exit 0
  (graceful), stderr contains "session ID not found" warning.

**Full lifecycle (happy path):**
- `test_happy_path_resume_shutdown` — patches:
  - `subprocess.Popen` returns mock process with `.pid = 1234` and `.wait()` → 0
  - PID file written to temp claude home: `{sessionId: "abc-123", ...}`
  - `entities.archive_transcript` returns `True`
  - second `subprocess.Popen` (resume) returns mock with `.wait()` → 0
  - `entities.append_session` called once
  - Output contains `"Session ID: abc-123"`, `"Shutdown method: resume"`,
    `"Transcript archived:"`.

**Transcript fallback:**
- `test_falls_back_to_transcript_extraction_on_resume_failure` — second Popen
  returns exit code 1; asserts `shutdown_from_transcript` is called and output
  contains `"Shutdown method: transcript fallback"`.

**Timeout:**
- `test_resume_timeout_triggers_fallback` — second Popen's `.wait(timeout=...)` raises
  `subprocess.TimeoutExpired`; asserts `shutdown_from_transcript` is called and the
  resume process is killed.

Run `uv run pytest tests/test_entity_claude_cli.py` — all tests should fail (no
implementation yet).

### Step 3: Implement `_read_session_id_from_pid_file` helper

Add a private helper in `src/cli/entity.py`:

```python
# Chunk: docs/chunks/entity_claude_wrapper - Session ID extraction from PID registry
def _read_session_id_from_pid_file(
    pid: int,
    claude_home: pathlib.Path | None = None,
) -> str | None:
    """Read the session ID that Claude Code recorded for a given PID.

    Claude Code writes ~/.claude/sessions/<pid>.json on startup with at least:
        {"pid": 1234, "sessionId": "uuid", "cwd": "/...", "startedAt": "..."}

    Returns the sessionId string, or None if the file doesn't exist or is malformed.
    """
```

The implementation:
- Defaults `claude_home` to `pathlib.Path.home() / ".claude"`.
- Reads `claude_home / "sessions" / f"{pid}.json"`.
- Parses JSON and returns `data.get("sessionId")`.
- Returns `None` on any `FileNotFoundError` or `json.JSONDecodeError`.

### Step 4: Implement the `claude` command — launch phase

Add the Click command below the existing `shutdown` command in `src/cli/entity.py`:

```python
# Chunk: docs/chunks/entity_claude_wrapper - Full entity session lifecycle
@entity.command("claude")
@click.option("--entity", "entity_name", required=True, help="Entity name")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
@click.option(
    "--resume-timeout",
    type=int,
    default=300,
    help="Seconds to wait for resume-based shutdown (default: 300)",
)
def claude_cmd(entity_name: str, project_dir: pathlib.Path, resume_timeout: int) -> None:
    """Launch Claude Code with entity lifecycle management."""
```

Inside the command:

1. Resolve `project_dir` via `resolve_entity_project_dir`.
2. Instantiate `entities = Entities(project_dir)`.
3. Check `entities.entity_exists(entity_name)` → `ClickException` if missing.
4. Record `started_at = datetime.now(timezone.utc)`.
5. Launch Claude:
   ```python
   import subprocess
   proc = subprocess.Popen(
       ["claude", "--prompt", f"/entity-startup {entity_name}"],
       stdin=None, stdout=None, stderr=None,   # inherit — user gets normal session
   )
   pid = proc.pid
   proc.wait()  # blocks until user exits (any exit path)
   ```
6. Record `ended_at = datetime.now(timezone.utc)`.

### Step 5: Implement session ID extraction and transcript archiving

After `proc.wait()` returns:

```python
session_id = _read_session_id_from_pid_file(pid)
if session_id is None:
    click.echo("Warning: session ID not found (PID file missing); skipping transcript archive", err=True)

archived = False
if session_id is not None:
    archived = entities.archive_transcript(
        entity_name,
        session_id,
        str(project_dir.resolve()),
    )
    if not archived:
        click.echo("Warning: transcript not found in Claude Code storage; skipping archive", err=True)
```

The transcript must be archived **before** shutdown so it exists for the fallback path.

### Step 6: Implement resume-based shutdown with timeout fallback

```python
shutdown_method = "none"
shutdown_result: dict = {}

if session_id is not None:
    # Strategy A: resume the session so the agent reflects on its own context
    resume_proc = subprocess.Popen(
        ["claude", "--resume", session_id, "--prompt", f"/entity-shutdown {entity_name}"],
        stdin=None, stdout=None, stderr=None,
    )
    try:
        resume_exit = resume_proc.wait(timeout=resume_timeout)
        if resume_exit == 0:
            shutdown_method = "resume"
            shutdown_result = {"journals_added": 0, "journals_consolidated": 0,
                               "consolidated": 0, "core": 0}
        else:
            # Non-zero exit — fall through to transcript fallback
            pass
    except subprocess.TimeoutExpired:
        resume_proc.kill()
        resume_proc.wait()
        click.echo("Warning: resume shutdown timed out; falling back to transcript extraction", err=True)
```

If `shutdown_method` is still `"none"` after the resume attempt (failed or timed out):

```python
# Strategy B: extract from archived transcript via API
if shutdown_method == "none":
    from entity_shutdown import shutdown_from_transcript
    from entity_transcript import parse_session_jsonl, resolve_session_jsonl_path

    jsonl_path = resolve_session_jsonl_path(str(project_dir.resolve()), session_id)
    if jsonl_path is not None:
        transcript = parse_session_jsonl(jsonl_path)
        try:
            shutdown_result = shutdown_from_transcript(
                entity_name=entity_name,
                transcript=transcript,
                project_dir=project_dir,
            )
            shutdown_method = "transcript fallback"
        except Exception as e:
            click.echo(f"Warning: transcript extraction failed: {e}", err=True)
    else:
        click.echo("Warning: transcript not found; skipping memory extraction", err=True)
```

If `session_id is None`, set `shutdown_method = "none"` and skip all shutdown.

### Step 7: Log session and print summary

```python
if session_id is not None:
    from models.entity import SessionRecord
    record = SessionRecord(
        session_id=session_id,
        started_at=started_at,
        ended_at=ended_at,
        summary=None,
    )
    entities.append_session(entity_name, record)

# Print summary
click.echo("")
click.echo("Entity session complete:")
click.echo(f"  Session ID:          {session_id or '(unknown)'}")
if archived and session_id:
    sessions_dir = entities.entity_dir(entity_name) / "sessions"
    click.echo(f"  Transcript archived: {sessions_dir / session_id}.jsonl")
else:
    click.echo("  Transcript archived: (skipped)")
click.echo(f"  Shutdown method:     {shutdown_method}")
if shutdown_result:
    click.echo(f"  Memories extracted:  {shutdown_result.get('journals_added', 0)} journals, "
               f"{shutdown_result.get('consolidated', 0)} consolidated, "
               f"{shutdown_result.get('core', 0)} core")
```

### Step 8: Update `GOAL.md` code_paths

Add to `docs/chunks/entity_claude_wrapper/GOAL.md` frontmatter:
```yaml
code_paths:
  - src/cli/entity.py
  - tests/test_entity_claude_cli.py
```

### Step 9: Run full test suite and fix any issues

```bash
uv run pytest tests/
```

All tests including the new ones must pass. Fix any import issues or test
fixture gaps.

### Step 10: Add backreference comment

At the top of the `claude_cmd` function, add:
```python
# Chunk: docs/chunks/entity_claude_wrapper - Full entity session lifecycle
```

This marks the primary implementation site for future traceability.

## Dependencies

- `entity_session_tracking` — `entities.archive_transcript()`, `entities.append_session()`,
  `SessionRecord`. All present in current codebase ✓
- `entity_transcript_extractor` — `parse_session_jsonl()`, `resolve_session_jsonl_path()`,
  `SessionTranscript`. All present ✓
- `entity_api_memory_extraction` — `shutdown_from_transcript()`. Present ✓
- `claude` binary on PATH — documented as prerequisite in GOAL.md.

## Risks and Open Questions

- **PID file schema**: The investigation confirmed `~/.claude/sessions/<pid>.json`
  contains `sessionId`, but this should be verified at implementation time on an
  actual Claude Code installation. The helper is isolated enough that schema
  variations can be handled locally.

- **Resume pass-through**: Resume shutdown launches Claude Code interactively.
  The user's terminal will briefly show a new Claude Code session running the
  `/entity-shutdown` command. This is expected behaviour but may surprise first-time
  users. A `click.echo("Running shutdown via session resume...")` before the resume
  launch would help.

- **`claude` binary name**: Claude Code is invoked as `claude`. If the installed
  binary has a different name on some platforms, this will fail. Document in the
  error message: "Ensure `claude` is on your PATH."

- **Anthropic API key for fallback**: `shutdown_from_transcript` calls the API.
  The key is read from `ANTHROPIC_API_KEY` env var (anthropic SDK default). No
  special handling needed in the wrapper — the existing error message from
  `entity_shutdown.py` is clear enough if the key is absent.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
