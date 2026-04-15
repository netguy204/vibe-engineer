
<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Create a new module `src/entity_from_transcript.py` that orchestrates the
full from-transcript pipeline, and add a `from-transcript` CLI command to
`src/cli/entity.py`. The implementation reuses existing building blocks:

- `entity_transcript.parse_session_jsonl()` — parse JSONL → SessionTranscript
- `entity_repo.create_entity_repo()` — initialize the new entity git repo
- `entity_repo._run_git()` and `entity_repo._git_commit_all()` — git operations
- `entity_shutdown._run_consolidation_agent()` and `entity_shutdown._build_consolidation_prompt()` — Agent SDK consolidation pipeline
- `claude_agent_sdk.ClaudeSDKClient` (guarded import) — wiki construction sessions

**Why a new module instead of extending entity_migration.py**: `entity_migration.py`
reads structured legacy memories and synthesizes them via Messages API. The
from-transcript flow reads raw session transcripts and constructs wiki pages
agenically via Agent SDK. These are fundamentally different inputs and runtimes.

**Large transcript handling**: Rather than embedding transcript text directly
in a prompt, write the formatted transcript text to a temp file inside
`entity_dir` (e.g., `_transcript_incoming.txt`). The Agent SDK session runs
with `cwd=entity_dir`, so it can read this file naturally via its file tools.
The temp file is removed after the wiki agent completes.

**First transcript vs. subsequent**:

- *First*: `create_entity_repo()` → wiki-creation Agent SDK session (writes all
  wiki pages) → host code commits "Session 1: initial wiki from transcript" →
  archive JSONL to `episodic/`
- *Subsequent (N ≥ 2)*: wiki-update Agent SDK session (updates wiki pages in
  place, no commit) → host code stages wiki, captures diff, commits "Session N:
  wiki update from transcript" → consolidation Agent SDK session (writes
  memories/, commits "Session N: consolidated memories") → archive JSONL

This two-commit structure per subsequent session mirrors the GOAL's described
pipeline exactly. `run_wiki_consolidation()` from entity_shutdown is NOT reused
directly because it re-stages the wiki and then commits wiki+memories together;
instead we call `_build_consolidation_prompt()` and `_run_consolidation_agent()`
individually after capturing the diff ourselves.

**Agent SDK guard**: Follow the same try/except import pattern as
`entity_shutdown.py` — guard `claude_agent_sdk` import and raise RuntimeError
if missing when the user invokes the command.

## Subsystem Considerations

No subsystems documented in this chunk's frontmatter, and none of the existing
`docs/subsystems/` apply. Note: the `entity_*` cluster has 26 chunks and no
subsystem documentation — worth considering `/subsystem-discover` in future
work, but outside this chunk's scope.

## Sequence

### Step 1: Create `src/entity_from_transcript.py` with data models and helpers

Create the new module with:

**Imports and Agent SDK guard:**
```python
try:
    from claude_agent_sdk import ClaudeSDKClient
    from claude_agent_sdk.types import ClaudeAgentOptions, ResultMessage
except ModuleNotFoundError:
    ClaudeSDKClient = None
    ClaudeAgentOptions = None
    ResultMessage = None
```

**`FromTranscriptResult` dataclass:**
```python
@dataclass
class FromTranscriptResult:
    entity_name: str
    entity_path: Path
    transcripts_processed: int
    wiki_pages_written: int   # approximate from agent's output
    sessions_archived: int
```

**`format_transcript_text(transcript: SessionTranscript) -> str`:**
Convert a `SessionTranscript` into readable prose. Format each turn as
`[Role]\n<text>\n` with a blank line separator. Omit turns where
`is_substantive_turn()` returns False. Prepend a header with session_id and
turn count. This is what gets written to the temp file.

**`_wiki_creation_prompt(entity_name: str, role: str | None, project_context: str | None) -> str`:**
Prompt for the first-transcript Agent SDK session. Instructs the agent to:
- Read `_transcript_incoming.txt` (the formatted transcript in cwd)
- Read `wiki/wiki_schema.md` for page conventions
- Construct all wiki pages: `wiki/index.md`, `wiki/identity.md`, `wiki/log.md`,
  `wiki/domain/*.md`, `wiki/techniques/*.md`, `wiki/projects/*.md`,
  `wiki/relationships/*.md` — write as many as warranted
- Include `role` and `project_context` if provided (helps seed identity.md)
- **Do NOT commit** — host code will commit
- Output a one-line session summary as its final text response

**`_wiki_update_prompt(entity_name: str, session_n: int, project_context: str | None) -> str`:**
Prompt for subsequent-transcript Agent SDK sessions. Instructs the agent to:
- Read `_transcript_incoming.txt`
- Read `wiki/index.md` to understand existing wiki structure
- Read and update relevant wiki pages with new knowledge
- Append a log entry to `wiki/log.md`
- **Do NOT commit**
- Output a one-line session summary as its final text response

**`async _run_wiki_agent(entity_dir: Path, prompt: str) -> dict`:**
Mirror of `_run_consolidation_agent` in entity_shutdown.py:
```python
options = ClaudeAgentOptions(cwd=str(entity_dir), permission_mode="bypassPermissions", max_turns=80)
async with ClaudeSDKClient(options=options) as client:
    await client.query(prompt)
    async for message in client.receive_response():
        if isinstance(message, ResultMessage):
            return {"success": True, "summary": getattr(message, "content", ""), "error": None}
return {"success": False, "summary": "", "error": "No result message received"}
```

Location: `src/entity_from_transcript.py`

---

### Step 2: Implement `_process_first_transcript`

```python
def _process_first_transcript(
    entity_dir: Path,
    entity_name: str,
    jsonl_path: Path,
    role: str | None,
    project_context: str | None,
) -> None
```

Steps:
1. `transcript = parse_session_jsonl(jsonl_path)`
2. `text = format_transcript_text(transcript)` → write to `entity_dir / "_transcript_incoming.txt"`
3. `prompt = _wiki_creation_prompt(entity_name, role, project_context)`
4. `asyncio.run(_run_wiki_agent(entity_dir, prompt))` — raise RuntimeError on failure
5. Remove `entity_dir / "_transcript_incoming.txt"`
6. Copy `jsonl_path` → `entity_dir / "episodic" / jsonl_path.name`
7. `_run_git(entity_dir, "add", "-A")`
8. `_run_git(entity_dir, "commit", "-m", "Session 1: initial wiki from transcript")`

---

### Step 3: Implement `_process_subsequent_transcript`

```python
def _process_subsequent_transcript(
    entity_dir: Path,
    entity_name: str,
    jsonl_path: Path,
    session_n: int,
    project_context: str | None,
) -> None
```

Steps:
1. `transcript = parse_session_jsonl(jsonl_path)`
2. `text = format_transcript_text(transcript)` → write to `entity_dir / "_transcript_incoming.txt"`
3. `prompt = _wiki_update_prompt(entity_name, session_n, project_context)`
4. `asyncio.run(_run_wiki_agent(entity_dir, prompt))` — raise RuntimeError on failure
5. Remove `entity_dir / "_transcript_incoming.txt"`
6. Stage wiki: `subprocess.run(["git", "-C", str(entity_dir), "add", "wiki/"], check=True)`
7. Capture diff: `wiki_diff = subprocess.run(["git", "-C", str(entity_dir), "diff", "--cached", "HEAD", "--", "wiki/"], capture_output=True, text=True).stdout`
8. Commit wiki: `_run_git(entity_dir, "commit", "--allow-empty", "-m", f"Session {session_n}: wiki update from transcript")`
9. If `wiki_diff.strip()`:
   - `prompt = _build_consolidation_prompt(entity_name, wiki_diff)` (imported from entity_shutdown)
   - `asyncio.run(_run_consolidation_agent(entity_dir, prompt))` (imported from entity_shutdown)
10. Copy `jsonl_path` → `entity_dir / "episodic" / jsonl_path.name`
11. Stage and commit episodic: `_run_git(entity_dir, "add", "episodic/")` then `_run_git(entity_dir, "commit", "--allow-empty", "-m", f"Session {session_n}: transcript archived")`

Note: If `wiki_diff` is empty (entity wrote no wiki changes), skip consolidation
but still archive and commit.

---

### Step 4: Implement `create_entity_from_transcript` (main entry point)

```python
def create_entity_from_transcript(
    name: str,
    jsonl_paths: list[Path],
    output_dir: Path,
    role: str | None = None,
    project_context: str | None = None,
) -> FromTranscriptResult
```

Steps:
1. Validate `name` against `ENTITY_REPO_NAME_PATTERN` → raise ValueError if invalid
2. Validate all paths exist → raise FileNotFoundError for any missing file
3. Check `ClaudeSDKClient is not None` → raise RuntimeError if missing
4. `repo_path = create_entity_repo(output_dir, name, role=role)`
5. `_process_first_transcript(repo_path, name, jsonl_paths[0], role, project_context)`
6. For each subsequent path (enumerate starting at 2):
   `_process_subsequent_transcript(repo_path, name, path, session_n, project_context)`
7. Return `FromTranscriptResult(entity_name=name, entity_path=repo_path, transcripts_processed=len(jsonl_paths), ...)`

Add module-level backreference:
```python
# Chunk: docs/chunks/entity_from_transcript - Create entity from session transcripts
```

---

### Step 5: Add `from-transcript` CLI command to `src/cli/entity.py`

Add after the `migrate` command:

```python
# Chunk: docs/chunks/entity_from_transcript - from-transcript CLI command
@entity.command("from-transcript")
@click.argument("name")
@click.argument("jsonl_paths", nargs=-1, required=True, type=click.Path(path_type=pathlib.Path))
@click.option("--role", default=None, help="Seed the entity's role description")
@click.option("--project-context", default=None, help="Context about the project the transcripts came from")
@click.option("--output-dir", type=click.Path(path_type=pathlib.Path), default=None,
              help="Where to create the entity repo (default: current directory)")
def from_transcript(name, jsonl_paths, role, project_context, output_dir):
    """Create a new wiki-based entity from one or more Claude Code session transcripts.

    NAME is the entity identifier (lowercase letters, digits, underscores, or hyphens).
    JSONL_PATHS are one or more paths to Claude Code session JSONL files, processed in order.

    Examples:
        ve entity from-transcript my-specialist session.jsonl
        ve entity from-transcript my-specialist s1.jsonl s2.jsonl s3.jsonl --role "Infrastructure specialist"
    """
    import entity_from_transcript as _eft

    if output_dir is None:
        output_dir = pathlib.Path.cwd()

    try:
        result = _eft.create_entity_from_transcript(
            name=name,
            jsonl_paths=list(jsonl_paths),
            output_dir=output_dir,
            role=role,
            project_context=project_context,
        )
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        raise click.ClickException(str(e))

    click.echo(f"Created entity '{result.entity_name}' at {result.entity_path}")
    click.echo(f"  Transcripts processed: {result.transcripts_processed}")
    click.echo(f"  Sessions archived:     {result.sessions_archived}")
    click.echo("Entity repo ready for attach/push.")
```

---

### Step 6: Write failing unit tests in `tests/test_entity_from_transcript.py`

Following TDD: write these tests first, verify they fail, then implement until they pass.

**Tests for `format_transcript_text`:**

- `test_format_transcript_text_labels_turns`: given a SessionTranscript with one user turn and one assistant turn, output contains "User" and "Assistant" labels
- `test_format_transcript_text_skips_short_turns`: turns with fewer than 20 characters are omitted
- `test_format_transcript_text_header_contains_session_id`: output starts with the session_id from the transcript

**Tests for `create_entity_from_transcript` (unit, mocking Agent SDK + git):**

Mock `entity_from_transcript._run_wiki_agent` to return a success dict (it's async; use `AsyncMock`). Mock `create_entity_repo` to return a real temp directory with the expected structure. Use `tmp_path` fixtures.

- `test_create_entity_from_transcript_invalid_name_raises`: name="INVALID!" raises ValueError
- `test_create_entity_from_transcript_missing_file_raises`: non-existent jsonl_path raises FileNotFoundError
- `test_create_entity_from_transcript_no_sdk_raises`: with `ClaudeSDKClient = None`, call raises RuntimeError
- `test_create_entity_from_transcript_single_archives_jsonl`: after single-transcript run, the JSONL is in `entity_dir/episodic/`
- `test_create_entity_from_transcript_single_creates_session1_commit`: after single-transcript run, `git log` of entity_dir shows "Session 1: initial wiki from transcript"
- `test_create_entity_from_transcript_multi_makes_consolidation_call`: with 2 transcripts, `_run_consolidation_agent` is called once (for session 2)
- `test_create_entity_from_transcript_result_fields`: result has correct `transcripts_processed` count, `entity_name`, and `entity_path` pointing to the repo

For tests requiring a real entity repo structure (for git operations), use a real temp `entity_dir` with `git init`, initial commit, and an empty `wiki/` and `episodic/` directory.

---

### Step 7: Write failing CLI tests in `tests/test_entity_from_transcript_cli.py`

Mock `entity_from_transcript.create_entity_from_transcript` to return a stub `FromTranscriptResult`. Use `CliRunner` with real temp files for path validation.

- `test_from_transcript_cli_success`: invoke with valid name + existing JSONL path → exit code 0, output contains entity name and "Transcripts processed: 1"
- `test_from_transcript_cli_missing_jsonl`: invoke with nonexistent path → exit code nonzero, output contains error message
- `test_from_transcript_cli_invalid_name`: invoke with name containing invalid chars → exit code nonzero
- `test_from_transcript_cli_role_passed_to_orchestrator`: invoke with `--role "my role"` → mock called with `role="my role"`
- `test_from_transcript_cli_multiple_paths`: invoke with 3 JSONL paths → mock called with `jsonl_paths` of length 3
- `test_from_transcript_cli_output_dir_passed`: invoke with `--output-dir /tmp/foo` → mock called with that output_dir

---

### Step 8: Update `code_paths` in the chunk's GOAL.md

Add `src/entity_from_transcript.py` and `tests/test_entity_from_transcript.py` and `tests/test_entity_from_transcript_cli.py` to the `code_paths` frontmatter field.

---

### Step 9: Run tests and iterate

```bash
uv run pytest tests/test_entity_from_transcript.py tests/test_entity_from_transcript_cli.py -v
```

Fix failures, run full suite to guard against regressions:
```bash
uv run pytest tests/ -x
```

## Dependencies

- `entity_wiki_schema` chunk — done; `wiki/wiki_schema.md` template exists in the entity repo structure created by `create_entity_repo()`
- `entity_repo_structure` chunk — done; `create_entity_repo()` available in `entity_repo.py`
- `entity_shutdown_wiki` chunk — done; `_build_consolidation_prompt()` and `_run_consolidation_agent()` available in `entity_shutdown.py`
- `claude_agent_sdk` package — must be installed in the environment (same dependency as entity_shutdown_wiki)

## Risks and Open Questions

- **Transcript size**: `parse_session_jsonl()` cleans and compresses transcripts significantly, but a 10MB JSONL could still produce a large `.txt`. Writing to a temp file and having the agent read it avoids prompt-size issues, but if the file exceeds the agent's practical file-reading limit, the agent may truncate or miss content. Mitigation: `format_transcript_text` can optionally truncate very long transcripts at N turns with a note.

- **Agent SDK nondeterminism**: The wiki-creation agent writes files autonomously. It could produce badly-named files, skip required pages, or write malformed frontmatter. The GOAL's quality bar (matching the investigation prototypes) relies on the wiki schema prompt being effective. The investigation confirmed this works well — same quality across 3 different session types.

- **Async in CLI context**: `asyncio.run()` is called from synchronous CLI code. This matches the pattern in `entity_shutdown.py` and should work fine, but will fail if called inside an already-running event loop (e.g., in Jupyter). Not a concern for CLI use.

- **Git in temp directories for tests**: Tests that verify git commit history need a real git repo. Use `subprocess.run(["git", "init", ...])` in `tmp_path` fixtures. Check `conftest.py` first for existing git init helpers.

- **Consolidation when wiki diff is empty**: The first transcript has no consolidation (correct — no prior state to consolidate against). Subsequent transcripts where the agent writes no wiki changes skip consolidation. This is correct behavior — if the agent wrote nothing, there's nothing to consolidate.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?
-->
