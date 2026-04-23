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
    """List all entities in the current project.

    # Chunk: docs/chunks/entity_attach_detach - Enhanced list with submodule status
    """
    project_dir = resolve_entity_project_dir(project_dir)

    found_any = False

    # List submodule-based entities
    attached = entity_repo.list_attached_entities(project_dir)
    submodule_names: set[str] = set()
    for info in attached:
        submodule_names.add(info.name)
        specialization_str = f"  {info.specialization}" if info.specialization else ""
        remote_str = f"  {info.remote_url}" if info.remote_url else ""
        click.echo(f"  {info.name}  [{info.status}]{specialization_str}{remote_str}")
        found_any = True

    # Legacy plain-directory entities (not submodules)
    entities_dir = project_dir / ".entities"
    if entities_dir.exists():
        entities_obj = Entities(project_dir)
        for name in entities_obj.list_entities():
            if name in submodule_names:
                continue
            # Check it's not a submodule (no .git file)
            entity_path = entities_dir / name
            if (entity_path / ".git").is_file():
                continue
            identity = entities_obj.parse_identity(name)
            if identity and identity.role:
                click.echo(f"  {name}  ({identity.role})")
            else:
                click.echo(f"  {name}")
            found_any = True

    if not found_any:
        click.echo("No entities found")


# Chunk: docs/chunks/entity_attach_detach - CLI attach command
@entity.command("attach")
@click.argument("repo_url")
@click.option("--name", default=None, help="Override derived entity name")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
def attach(repo_url: str, name: str | None, project_dir: pathlib.Path | None) -> None:
    """Attach an entity repository to this project as a git submodule.

    REPO_URL is the URL or path to the entity's git repository.
    The entity is cloned into .entities/<name>/.
    """
    project_dir = resolve_entity_project_dir(project_dir)
    if name is None:
        name = entity_repo.derive_entity_name_from_url(repo_url)
    try:
        entity_repo.attach_entity(project_dir, repo_url, name)
        metadata = entity_repo.read_entity_metadata(project_dir / ".entities" / name)
        click.echo(f"Attached entity '{name}' from {repo_url}")
        if metadata.specialization:
            click.echo(f"  Specialization: {metadata.specialization}")
        click.echo("Review changes with git status, then commit when ready.")
    except (ValueError, RuntimeError) as e:
        raise click.ClickException(str(e))


# Chunk: docs/chunks/entity_attach_detach - CLI detach command
@entity.command("detach")
@click.argument("name")
@click.option("--force", is_flag=True, default=False, help="Remove even if entity has uncommitted changes")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
def detach(name: str, force: bool, project_dir: pathlib.Path | None) -> None:
    """Detach an entity repository from this project.

    NAME is the entity identifier (subdirectory under .entities/).
    Removes the git submodule cleanly. Refuses if the entity has
    uncommitted changes unless --force is given.
    """
    project_dir = resolve_entity_project_dir(project_dir)
    try:
        entity_repo.detach_entity(project_dir, name, force=force)
        click.echo(f"Detached entity '{name}'")
    except (ValueError, RuntimeError) as e:
        raise click.ClickException(str(e))


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
# Chunk: docs/chunks/entity_shutdown_wiki - Wiki-aware shutdown routing
@entity.command("shutdown")
@click.argument("name")
@click.option(
    "--memories-file",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
    help="JSON file with extracted memories (for legacy entities without wiki/)",
)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
def shutdown(name: str, memories_file: pathlib.Path | None, project_dir: pathlib.Path) -> None:
    """Run the sleep cycle: consolidate extracted memories for an entity.

    For wiki-based entities (have wiki/ directory), automatically diffs the wiki
    and runs Agent SDK consolidation — no --memories-file needed.

    For legacy entities, reads extracted journal memories (JSON array) from
    --memories-file or stdin.

    # Chunk: docs/chunks/entity_shutdown_wiki - Wiki-aware shutdown routing

    NAME is the entity identifier.
    """
    from entity_shutdown import run_shutdown

    project_dir = resolve_entity_project_dir(project_dir)
    entities = Entities(project_dir)

    # Validate entity exists
    if not entities.entity_exists(name):
        raise click.ClickException(f"Entity '{name}' not found")

    # For legacy entities, read memories JSON from file or stdin
    memories_json: str | None = None
    if not entities.has_wiki(name):
        if memories_file is not None:
            memories_json = memories_file.read_text()
        elif not sys.stdin.isatty():
            memories_json = sys.stdin.read()
        else:
            memories_json = None  # run_shutdown will raise ValueError

        if memories_json is not None and not memories_json.strip():
            memories_json = "[]"

    try:
        result = run_shutdown(
            entity_name=name,
            project_dir=project_dir,
            extracted_memories_json=memories_json,
        )
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Shutdown failed: {e}")

    # Print summary
    click.echo(f"Shutdown complete for entity '{name}':")
    click.echo(f"  Journals added:  {result.get('journals_added', 0)}")
    if "journals_consolidated" in result:
        click.echo(f"  Journals processed: {result['journals_consolidated']}")
    click.echo(f"  Consolidated:    {result.get('consolidated', 0)}")
    click.echo(f"  Core:            {result.get('core', 0)}")
    if "skipped" in result:
        click.echo(f"  Note: {result['skipped']}")
    if "error" in result:
        click.echo(f"  Warning: consolidation error: {result['error']}", err=True)


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
    # Chunk: docs/chunks/transcript_dot_encoding_fix - Claude Code encodes both '/' and '.' as '-'
    encoded = "-" + project_path.strip("/").replace("/", "-").replace(".", "-")
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
            # Strategy B: wiki entities use run_shutdown (wiki diff + Agent SDK);
            # legacy entities fall back to transcript extraction via Anthropic API.
            from entity_shutdown import run_shutdown, shutdown_from_transcript

            if entities.has_wiki(entity_name):
                try:
                    click.echo("Running wiki-based shutdown...")
                    shutdown_result = run_shutdown(
                        entity_name=entity_name,
                        project_dir=project_dir,
                    )
                    shutdown_method = "wiki consolidation"
                except Exception as e:
                    click.echo(f"Warning: wiki shutdown failed: {e}", err=True)
            else:
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


# Chunk: docs/chunks/entity_memory_migration - Migration CLI command
@entity.command("migrate")
@click.argument("entity_name")
@click.option("--name", default=None, help="Override entity name for the migrated repo (default: use existing name)")
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
def migrate(
    entity_name: str,
    name: str | None,
    role: str | None,
    entity_dir: pathlib.Path | None,
    output_dir: pathlib.Path | None,
) -> None:
    """Migrate a legacy entity to the wiki-based git repo structure.

    ENTITY_NAME is the existing entity name (e.g. palette, steward, creator).
    The migrated repo uses the same name by default.

    Examples:
        ve entity migrate palette
        ve entity migrate palette --name palette-v2
    """
    import entity_migration

    # Resolve entity_dir
    if entity_dir is None:
        project_dir = resolve_entity_project_dir(None)
        entity_dir = project_dir / ".entities" / entity_name

    # Default to existing entity name
    repo_name = name if name is not None else entity_name

    # Resolve output_dir
    if output_dir is None:
        output_dir = pathlib.Path.cwd()

    try:
        result = entity_migration.migrate_entity(entity_dir, output_dir, repo_name, role=role)
    except (ValueError, RuntimeError) as e:
        raise click.ClickException(str(e))

    click.echo(f"Migrated entity '{entity_name}' \u2192 '{repo_name}'")
    click.echo(f"  New repo:           {result.dest_dir}")
    click.echo(f"  Wiki pages created: {len(result.wiki_pages_created)}")
    click.echo(f"  Memories preserved: {result.memories_preserved}")
    click.echo(f"  Sessions migrated:  {result.sessions_migrated}")
    click.echo(f"  Unclassified:       {result.unclassified_count} (review manually)")


# Chunk: docs/chunks/entity_ingest_transcript - Wiki-aware transcript ingest CLI
@entity.command("ingest-transcript")
@click.argument("name")
@click.argument("jsonl_paths", nargs=-1, required=True, type=click.Path(path_type=pathlib.Path))
@click.option(
    "--project-context",
    default=None,
    help="Context about the project the transcripts came from",
)
@click.option(
    "--skip-consolidation",
    is_flag=True,
    default=False,
    help="Update wiki only, skip memory consolidation (useful for batch imports)",
)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
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


# Chunk: docs/chunks/entity_from_transcript - from-transcript CLI command
@entity.command("from-transcript")
@click.argument("name")
@click.argument("jsonl_paths", nargs=-1, required=True, type=click.Path(path_type=pathlib.Path))
@click.option("--role", default=None, help="Seed the entity's role description")
@click.option(
    "--project-context",
    default=None,
    help="Context about the project the transcripts came from",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=pathlib.Path),
    default=None,
    help="Where to create the entity repo (default: current directory)",
)
def from_transcript(
    name: str,
    jsonl_paths: tuple[pathlib.Path, ...],
    role: str | None,
    project_context: str | None,
    output_dir: pathlib.Path | None,
) -> None:
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


# Chunk: docs/chunks/entity_push_pull - CLI push command
@entity.command("push")
@click.argument("name")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
def push(name: str, project_dir: pathlib.Path | None) -> None:
    """Push entity commits to remote origin.

    NAME is the entity identifier (subdirectory under .entities/).
    Pushes committed changes in the entity's repo to its remote origin.
    Warns if uncommitted changes are present (these are NOT pushed).
    """
    project_dir = resolve_entity_project_dir(project_dir)
    entity_path = project_dir / ".entities" / name
    try:
        result = entity_repo.push_entity(entity_path)
    except (ValueError, RuntimeError) as e:
        raise click.ClickException(str(e))

    if result.has_uncommitted:
        click.echo(
            f"Warning: entity '{name}' has uncommitted changes — these will not be pushed"
        )
    if result.commits_pushed == 0:
        click.echo("Already up to date")
    else:
        click.echo(f"Pushed {result.commits_pushed} commit(s) to origin")


# Chunk: docs/chunks/entity_push_pull - CLI pull command
@entity.command("pull")
@click.argument("name")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
def pull(name: str, project_dir: pathlib.Path | None) -> None:
    """Fetch and merge entity commits from remote origin.

    NAME is the entity identifier (subdirectory under .entities/).
    Fast-forwards the local entity branch when possible. If histories
    have diverged, warns and suggests 've entity merge'.
    """
    project_dir = resolve_entity_project_dir(project_dir)
    entity_path = project_dir / ".entities" / name
    try:
        result = entity_repo.pull_entity(entity_path)
    except entity_repo.MergeNeededError as e:
        raise click.ClickException(
            f"Histories have diverged. Use 've entity merge' to resolve.\n{e}"
        )
    except (ValueError, RuntimeError) as e:
        raise click.ClickException(str(e))

    if result.up_to_date:
        click.echo("Already up to date")
    else:
        click.echo(f"Merged {result.commits_merged} new commit(s) from origin")


# Chunk: docs/chunks/entity_push_pull - CLI set-origin command
@entity.command("set-origin")
@click.argument("name")
@click.argument("url")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
def set_origin(name: str, url: str, project_dir: pathlib.Path | None) -> None:
    """Set or update the remote origin URL for an entity.

    NAME is the entity identifier (subdirectory under .entities/).
    URL is the remote repository URL (GitHub HTTPS/SSH or local path).
    """
    project_dir = resolve_entity_project_dir(project_dir)
    entity_path = project_dir / ".entities" / name
    try:
        entity_repo.set_entity_origin(entity_path, url)
    except (ValueError, RuntimeError) as e:
        raise click.ClickException(str(e))
    click.echo(f"Set origin for '{name}' to {url}")


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


# Chunk: docs/chunks/entity_fork_merge - Fork entity CLI command
@entity.command("fork")
@click.argument("name")
@click.argument("new_name")
@click.option(
    "--output-dir",
    type=click.Path(path_type=pathlib.Path),
    default=None,
    help="Directory to create fork in (default: same parent as source entity)",
)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
def fork(
    name: str,
    new_name: str,
    output_dir: pathlib.Path | None,
    project_dir: pathlib.Path | None,
) -> None:
    """Fork an entity to create an independent specialist clone.

    NAME is the source entity identifier (subdirectory under .entities/).
    NEW_NAME is the name for the new fork.

    The fork is a fully independent entity with its own history going forward.
    Original remote origin is preserved — use 've entity set-origin' to point
    the fork at a new remote.
    """
    project_dir = resolve_entity_project_dir(project_dir)
    entity_path = project_dir / ".entities" / name

    if not entity_path.exists():
        raise click.ClickException(f"Entity '{name}' not found at '{entity_path}'")

    if output_dir is None:
        output_dir = entity_path.parent

    try:
        result = entity_repo.fork_entity(entity_path, output_dir, new_name)
    except (ValueError, RuntimeError) as e:
        raise click.ClickException(str(e))

    click.echo(f"Forked '{result.source_name}' → '{result.new_name}' at {result.dest_path}")

    # Show original origin (if any) so operator knows to update it
    import subprocess as _subprocess
    origin_check = _subprocess.run(
        ["git", "-C", str(result.dest_path), "remote", "get-url", "origin"],
        capture_output=True, text=True,
    )
    if origin_check.returncode == 0 and origin_check.stdout.strip():
        click.echo(
            f"Original origin: {origin_check.stdout.strip()} "
            f"(use 've entity set-origin' to point fork at a new remote)"
        )


# Chunk: docs/chunks/entity_fork_merge - Merge entity CLI command
@entity.command("merge")
@click.argument("name")
@click.argument("source")
@click.option(
    "--yes", "-y",
    is_flag=True,
    default=False,
    help="Auto-approve all LLM conflict resolutions without prompting",
)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
def merge(
    name: str,
    source: str,
    yes: bool,
    project_dir: pathlib.Path | None,
) -> None:
    """Merge learnings from a source entity into a target entity.

    NAME is the target entity identifier (subdirectory under .entities/).
    SOURCE can be a repo URL, local path, or the name of another attached entity.

    Clean merges complete automatically with a summary. Conflicting wiki pages
    trigger LLM-assisted resolution with operator approval (use --yes to skip
    prompts and approve all resolutions automatically).
    """
    project_dir = resolve_entity_project_dir(project_dir)
    entity_path = project_dir / ".entities" / name

    if not entity_path.exists():
        raise click.ClickException(f"Entity '{name}' not found at '{entity_path}'")

    # Resolve source: check if it's an attached entity name first
    candidate = project_dir / ".entities" / source
    resolved_source = str(candidate) if candidate.exists() else source

    try:
        result = entity_repo.merge_entity(entity_path, resolved_source)
    except (ValueError, RuntimeError) as e:
        raise click.ClickException(str(e))

    if isinstance(result, entity_repo.MergeResult):
        if result.commits_merged == 0:
            click.echo("Already up to date")
        else:
            click.echo(
                f"Merged {result.commits_merged} commit(s) — "
                f"{result.new_pages} new page(s), {result.updated_pages} updated page(s)"
            )
        return

    # MergeConflictsPending: show resolutions and prompt
    assert isinstance(result, entity_repo.MergeConflictsPending)

    if result.unresolvable:
        click.echo(
            f"Warning: {len(result.unresolvable)} file(s) could not be auto-resolved "
            f"(resolve manually): {', '.join(result.unresolvable)}",
            err=True,
        )

    if not result.resolutions:
        click.echo(
            "No resolvable conflicts found. Aborting merge. "
            "Resolve unresolvable conflicts manually and commit.",
            err=True,
        )
        try:
            entity_repo.abort_merge(entity_path)
        except RuntimeError:
            pass
        raise click.ClickException("Merge aborted — manual resolution required")

    all_approved = True
    for resolution in result.resolutions:
        click.echo(f"\n--- Resolution for: {resolution.relative_path} ---")
        click.echo(resolution.synthesized)
        click.echo("---")

        if not yes:
            response = click.prompt(
                "Approve this resolution? [y/N]",
                default="N",
                show_default=False,
            )
            if response.strip().lower() != "y":
                all_approved = False
                break

    if all_approved:
        try:
            entity_repo.commit_resolved_merge(
                entity_path, result.resolutions, result.source
            )
        except (RuntimeError, Exception) as e:
            raise click.ClickException(f"Failed to commit resolved merge: {e}")
        click.echo(
            f"Merge committed — {len(result.resolutions)} conflict(s) resolved"
        )
        if result.unresolvable:
            click.echo(
                f"Note: {len(result.unresolvable)} file(s) still need manual resolution: "
                f"{', '.join(result.unresolvable)}"
            )
    else:
        try:
            entity_repo.abort_merge(entity_path)
        except RuntimeError as e:
            click.echo(f"Warning: could not abort merge cleanly: {e}", err=True)
        raise click.ClickException("Merge aborted — resolution rejected by operator")
