"""Entity command group.

# Chunk: docs/chunks/entity_memory_schema
# Chunk: docs/chunks/entity_startup_skill - Startup and recall CLI commands
# Chunk: docs/chunks/entity_shutdown_skill
# Chunk: docs/chunks/entity_shutdown_silent_failure - Entity CLI root resolution

Commands for managing entities - long-running agent personas with persistent memory.
"""

import json
import os
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

import click

import entity_repo
from entities import Entities


# Chunk: docs/chunks/entity_shutdown_silent_failure - Entity CLI root resolution
def resolve_entity_project_dir(explicit_dir: pathlib.Path | None) -> pathlib.Path:
    """Resolve the project directory for entity commands.

    When --project-dir is not provided (None), walks up from CWD to find
    the project root using the same chain as board/orch commands:
    .ve-task.yaml → .git → CWD fallback.
    """
    from board.storage import resolve_project_root
    return resolve_project_root(explicit_dir)


@click.group()
def entity():
    """Manage entities - long-running agent personas with persistent memory."""
    pass


@entity.command("create")
@click.argument("name")
@click.option("--role", default=None, help="Brief description of entity's purpose")
@click.option(
    "--output-dir",
    type=click.Path(path_type=pathlib.Path),
    default=None,
    help="Directory to create entity repo in (default: current directory)",
)
def create(name: str, role: str | None, output_dir: pathlib.Path | None) -> None:
    """Create a new entity as a standalone git repository.

    # Chunk: docs/chunks/entity_repo_structure - Standalone entity repo creation command

    NAME is the entity identifier (lowercase letters, digits, underscores, or hyphens).

    The entity repo is created as a subdirectory of --output-dir (or the current
    working directory if not specified). The repo contains ENTITY.md, a wiki/
    directory with rendered templates, memories/, and episodic/ directories.
    """
    if output_dir is None:
        output_dir = pathlib.Path.cwd()
    try:
        repo_path = entity_repo.create_entity_repo(output_dir, name, role=role)
        click.echo(f"Created entity '{name}' at {repo_path}")
    except ValueError as e:
        raise click.ClickException(str(e))


@entity.command("list")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
def list_entities(project_dir: pathlib.Path) -> None:
    """List all entities in the current project."""
    project_dir = resolve_entity_project_dir(project_dir)
    entities = Entities(project_dir)
    names = entities.list_entities()

    if not names:
        click.echo("No entities found")
        return

    for name in names:
        identity = entities.parse_identity(name)
        if identity and identity.role:
            click.echo(f"  {name}  ({identity.role})")
        else:
            click.echo(f"  {name}")


@entity.command("startup")
@click.argument("name")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
def startup(name: str, project_dir: pathlib.Path) -> None:
    """Render the startup payload for a named entity.

    NAME is the entity to wake up. Outputs the full startup context
    including identity, core memories, consolidated memory index,
    and touch protocol instructions.
    """
    project_dir = resolve_entity_project_dir(project_dir)
    entities = Entities(project_dir)
    try:
        payload = entities.startup_payload(name)
        click.echo(payload)
    except ValueError as e:
        raise click.ClickException(str(e))


@entity.command("recall")
@click.argument("name")
@click.argument("query")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
def recall(name: str, query: str, project_dir: pathlib.Path) -> None:
    """Recall memories matching a query for a named entity.

    NAME is the entity to search. QUERY is a case-insensitive
    substring to match against memory titles.
    """
    project_dir = resolve_entity_project_dir(project_dir)
    entities = Entities(project_dir)
    try:
        results = entities.recall_memory(name, query)
    except ValueError as e:
        raise click.ClickException(str(e))

    if not results:
        click.echo(f"No memories matching '{query}'")
        return

    for result in results:
        fm = result["frontmatter"]
        click.echo(f"## {fm['title']}")
        click.echo(f"*Tier: {result['tier']} | Category: {fm['category']}*")
        click.echo("")
        click.echo(result["content"])
        click.echo("")


# Chunk: docs/chunks/entity_touch_command
@entity.command("touch")
@click.argument("name")
@click.argument("memory_id")
@click.argument("reason", required=False, default=None)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
def touch(name: str, memory_id: str, reason: str | None, project_dir: pathlib.Path) -> None:
    """Touch a memory to record runtime reinforcement.

    NAME is the entity identifier.
    MEMORY_ID is the filename stem (without .md) of the memory to touch.
    REASON is an optional description of why the memory was useful.
    """
    project_dir = resolve_entity_project_dir(project_dir)
    entities = Entities(project_dir)
    try:
        event = entities.touch_memory(name, memory_id, reason)
        click.echo(f"Touched '{event.memory_title}' (last_reinforced updated)")
    except ValueError as e:
        raise click.ClickException(str(e))


# Chunk: docs/chunks/entity_shutdown_skill
@entity.command("shutdown")
@click.argument("name")
@click.option(
    "--memories-file",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
    help="JSON file with extracted memories (alternative to stdin)",
)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
def shutdown(name: str, memories_file: pathlib.Path | None, project_dir: pathlib.Path) -> None:
    """Run the sleep cycle: consolidate extracted memories for an entity.

    Reads extracted journal memories (JSON array) from --memories-file or stdin,
    then runs incremental consolidation against the entity's existing memory tiers.

    NAME is the entity identifier.
    """
    from entity_shutdown import run_consolidation

    project_dir = resolve_entity_project_dir(project_dir)
    entities = Entities(project_dir)

    # Validate entity exists
    if not entities.entity_exists(name):
        raise click.ClickException(f"Entity '{name}' not found")

    # Read memories JSON
    if memories_file is not None:
        memories_json = memories_file.read_text()
    elif not sys.stdin.isatty():
        memories_json = sys.stdin.read()
    else:
        raise click.ClickException(
            "No memories provided. Use --memories-file or pipe JSON to stdin."
        )

    if not memories_json.strip():
        memories_json = "[]"  # Treat truly empty input as empty array

    try:
        result = run_consolidation(
            entity_name=name,
            extracted_memories_json=memories_json,
            project_dir=project_dir,
        )
    except Exception as e:
        raise click.ClickException(f"Consolidation failed: {e}")

    # Print summary
    click.echo(f"Shutdown complete for entity '{name}':")
    click.echo(f"  Journals added:  {result['journals_added']}")
    click.echo(f"  Journals processed: {result['journals_consolidated']}")
    click.echo(f"  Consolidated:    {result['consolidated']}")
    click.echo(f"  Core:            {result['core']}")


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
    if claude_home is None:
        claude_home = pathlib.Path.home() / ".claude"
    pid_file = claude_home / "sessions" / f"{pid}.json"
    try:
        data = json.loads(pid_file.read_text())
        return data.get("sessionId") or None
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _find_most_recent_session(
    project_path: str,
    after_timestamp: float,
    claude_home: pathlib.Path | None = None,
) -> str | None:
    """Find the most recently modified session JSONL for a project.

    Claude Code cleans up PID files on exit, so this is a fallback for
    extracting the session ID by finding the JSONL that was modified
    after a given timestamp (the session start time).

    Returns the sessionId string, or None if no matching session is found.
    """
    if claude_home is None:
        claude_home = pathlib.Path.home() / ".claude"
    encoded = "-" + project_path.strip("/").replace("/", "-")
    sessions_dir = claude_home / "projects" / encoded
    if not sessions_dir.exists():
        return None

    best_session: str | None = None
    best_mtime: float = 0.0
    for jsonl_file in sessions_dir.glob("*.jsonl"):
        mtime = jsonl_file.stat().st_mtime
        if mtime > after_timestamp and mtime > best_mtime:
            best_mtime = mtime
            best_session = jsonl_file.stem
    return best_session


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
@click.option(
    "--megaclaude",
    is_flag=True,
    default=False,
    help="Launch with agent teams and skip-permissions (CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=true --dangerously-skip-permissions)",
)
def claude_cmd(entity_name: str, project_dir: pathlib.Path | None, resume_timeout: int, megaclaude: bool) -> None:
    """Launch Claude Code with entity lifecycle management."""
    project_dir = resolve_entity_project_dir(project_dir)
    entities = Entities(project_dir)

    if not entities.entity_exists(entity_name):
        raise click.ClickException(f"Entity '{entity_name}' not found")

    started_at = datetime.now(timezone.utc)
    launch_timestamp = started_at.timestamp()

    # --- Megaclaude environment ---
    mega_env = {**os.environ, "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "true"} if megaclaude else None

    # --- Phase 1: Launch Claude Code interactively ---
    cmd = ["claude", "--name", f"entity:{entity_name}"]
    if megaclaude:
        cmd.append("--dangerously-skip-permissions")
    cmd.append(f"/entity-startup {entity_name}")

    proc = subprocess.Popen(
        cmd,
        stdin=None,
        stdout=None,
        stderr=None,
        env=mega_env,
    )
    pid = proc.pid
    proc.wait()

    ended_at = datetime.now(timezone.utc)

    # --- Phase 2: Extract session ID ---
    # Try PID file first (may be cleaned up on exit), then fall back to
    # finding the most recently modified JSONL for this project.
    session_id = _read_session_id_from_pid_file(pid)
    if session_id is None:
        session_id = _find_most_recent_session(
            str(project_dir.resolve()), launch_timestamp
        )
    if session_id is None:
        click.echo(
            "Warning: session ID not found; skipping transcript archive",
            err=True,
        )

    # --- Phase 3: Archive transcript ---
    archived = False
    if session_id is not None:
        archived = entities.archive_transcript(
            entity_name,
            session_id,
            str(project_dir.resolve()),
        )
        if not archived:
            click.echo(
                "Warning: transcript not found in Claude Code storage; skipping archive",
                err=True,
            )

    # --- Phase 4: Shutdown (resume first, then transcript fallback) ---
    shutdown_method = "none"
    shutdown_result: dict = {}

    if session_id is not None:
        click.echo("Running shutdown via session resume...")
        resume_cmd = ["claude", "--resume", session_id, "-p"]
        if megaclaude:
            resume_cmd.append("--dangerously-skip-permissions")
        resume_cmd.append(f"/entity-shutdown {entity_name}")

        resume_proc = subprocess.Popen(
            resume_cmd,
            stdin=None,
            stdout=None,
            stderr=None,
            env=mega_env,
        )
        try:
            resume_exit = resume_proc.wait(timeout=resume_timeout)
            if resume_exit == 0:
                shutdown_method = "resume"
                shutdown_result = {
                    "journals_added": 0,
                    "journals_consolidated": 0,
                    "consolidated": 0,
                    "core": 0,
                }
        except subprocess.TimeoutExpired:
            resume_proc.kill()
            resume_proc.wait()
            click.echo(
                "Warning: resume shutdown timed out; falling back to transcript extraction",
                err=True,
            )

        if shutdown_method == "none":
            # Strategy B: extract from archived transcript via API
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
                click.echo(
                    "Warning: transcript not found; skipping memory extraction",
                    err=True,
                )

    # --- Phase 5: Log session and print summary ---
    if session_id is not None:
        from models.entity import SessionRecord

        record = SessionRecord(
            session_id=session_id,
            started_at=started_at,
            ended_at=ended_at,
            summary=None,
        )
        entities.append_session(entity_name, record)

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
        click.echo(
            f"  Memories extracted:  {shutdown_result.get('journals_added', 0)} journals, "
            f"{shutdown_result.get('consolidated', 0)} consolidated, "
            f"{shutdown_result.get('core', 0)} core"
        )


# Chunk: docs/chunks/episodic_ingest_external - External transcript ingest CLI
@entity.command("ingest")
@click.argument("name")
@click.argument("path", nargs=-1, required=True)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
def ingest(name: str, path: tuple[str, ...], project_dir: pathlib.Path | None) -> None:
    """Ingest external Claude Code session transcripts into an entity's sessions.

    NAME is the entity identifier.
    PATH is one or more file paths or glob patterns pointing to JSONL session files.
    """
    import glob as globmod

    from entity_episodic import EpisodicStore

    project_dir = resolve_entity_project_dir(project_dir)
    entities = Entities(project_dir)

    if not entities.entity_exists(name):
        raise click.ClickException(f"Entity '{name}' not found")

    # Expand globs and collect all resolved paths
    resolved: list[pathlib.Path] = []
    for p in path:
        expanded = globmod.glob(p)
        if expanded:
            resolved.extend(pathlib.Path(e) for e in expanded)
        else:
            # No glob match — pass through as-is so ingest_files reports the error
            resolved.append(pathlib.Path(p))

    store = EpisodicStore(entities.entity_dir(name))
    result = store.ingest_files(resolved)

    # Print summary
    n_ingested = len(result.ingested)
    n_skipped = len(result.skipped)

    if n_ingested == 0 and n_skipped == 0:
        click.echo("No files matched the provided path(s).")
        return

    click.echo(f"Ingested {n_ingested}, skipped {n_skipped}.")

    for stem in result.ingested:
        click.echo(f"  ✓ {stem}")

    for msg in result.errors:
        click.echo(f"  ⚠ {msg}", err=True)


# Chunk: docs/chunks/entity_episodic_search
@entity.command("episodic")
@click.option("--entity", "entity_name", required=True, help="Entity name")
@click.option("--query", default=None, help="Search query (search mode)")
@click.option(
    "--expand",
    "expand_session",
    default=None,
    metavar="SESSION_ID",
    help="Session ID to expand around (expand mode)",
)
@click.option(
    "--chunk",
    "expand_chunk_id",
    type=int,
    default=None,
    help="Chunk ID to expand (required with --expand)",
)
@click.option(
    "--radius",
    default=10,
    show_default=True,
    help="Number of turns to include before/after in expand mode",
)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
def episodic(
    entity_name: str,
    query: str | None,
    expand_session: str | None,
    expand_chunk_id: int | None,
    radius: int,
    project_dir: pathlib.Path | None,
) -> None:
    """Search or expand episodic memory from archived session transcripts.

    Search mode: --entity <name> --query "..."
    Expand mode: --entity <name> --expand <session_id> --chunk <id>
    """
    from entity_episodic import EpisodicStore

    # Validate mutual exclusion
    if query is None and expand_session is None:
        raise click.ClickException(
            "Provide either --query (search mode) or --expand (expand mode)"
        )

    project_dir = resolve_entity_project_dir(project_dir)
    entities = Entities(project_dir)

    if not entities.entity_exists(entity_name):
        raise click.ClickException(f"Entity '{entity_name}' not found")

    store = EpisodicStore(entities.entity_dir(entity_name))

    if query is not None:
        # Search mode
        store.build_or_update(entity_name)
        results = store.search(query, entity_name=entity_name)
        if not results:
            click.echo(f'No results for "{query}"')
            return

        # Count unique sessions
        unique_sessions = len({r.session_id for r in results})
        click.echo(
            f'Results for "{query}" ({len(results)} matches across {unique_sessions} sessions):\n'
        )
        for r in results:
            click.echo(
                f"[{r.rank}] score={r.score:.2f} session={r.session_id[:8]} date={r.timestamp}"
            )
            click.echo(f"    {r.preview}")
            click.echo(f"    → expand: {r.expand_cmd}")
            click.echo("")

    else:
        # Expand mode
        if expand_chunk_id is None:
            raise click.ClickException("--chunk is required with --expand")

        expanded = store.expand(expand_session, expand_chunk_id, radius)
        if expanded is None:
            raise click.ClickException(
                f"Session '{expand_session}' chunk {expand_chunk_id} not found"
            )
        click.echo(expanded)
