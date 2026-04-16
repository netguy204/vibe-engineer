"""Create a wiki-based entity from one or more Claude Code session transcripts.

# Chunk: docs/chunks/entity_from_transcript - Create entity from session transcripts

Provides the `create_entity_from_transcript` function and supporting pipeline
that constructs a full wiki-based entity repo by processing JSONL session
transcripts with Agent SDK sessions.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from entities import Entities
from entity_repo import ENTITY_REPO_NAME_PATTERN, _run_git, create_entity_repo
from entity_shutdown import _build_consolidation_prompt, _run_consolidation_agent
from entity_transcript import SessionTranscript, is_substantive_turn, parse_session_jsonl

try:
    from claude_agent_sdk import ClaudeSDKClient
    from claude_agent_sdk.types import ClaudeAgentOptions, ResultMessage
except ModuleNotFoundError:
    ClaudeSDKClient = None
    ClaudeAgentOptions = None
    ResultMessage = None


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class FromTranscriptResult:
    """Result of a create_entity_from_transcript call."""

    entity_name: str
    entity_path: Path
    transcripts_processed: int
    wiki_pages_written: int   # approximate: count of *.md files under wiki/
    sessions_archived: int


# Chunk: docs/chunks/entity_ingest_transcript - Ingest transcripts into existing entity
@dataclass
class IngestTranscriptResult:
    """Result of an ingest_transcripts_into_entity call."""

    entity_name: str
    entity_path: Path
    transcripts_processed: int
    sessions_archived: int
    wiki_pages_total: int   # count of *.md files under wiki/ after processing


# ---------------------------------------------------------------------------
# Transcript formatting
# ---------------------------------------------------------------------------


def format_transcript_text(transcript: SessionTranscript) -> str:
    """Convert a SessionTranscript into readable prose for the wiki agent.

    Formats each substantive turn as::

        [Role]
        <text>

    with a blank line between turns.  Non-substantive turns (< 20 chars) are
    omitted.  A header with session_id and turn count is prepended.
    """
    substantive = [t for t in transcript.turns if is_substantive_turn(t)]
    lines: list[str] = [
        f"Session: {transcript.session_id}",
        f"Turns: {len(substantive)}",
        "",
    ]
    for turn in substantive:
        label = "User" if turn.role == "user" else "Assistant"
        lines.append(f"[{label}]")
        lines.append(turn.text)
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent SDK prompts
# ---------------------------------------------------------------------------


def _wiki_creation_prompt(
    entity_name: str,
    role: str | None,
    project_context: str | None,
) -> str:
    """Prompt for the first-transcript Agent SDK wiki-construction session."""
    role_section = f"\n**Entity role**: {role}" if role else ""
    context_section = (
        f"\n**Project context**: {project_context}" if project_context else ""
    )
    return f"""\
You are constructing a wiki-based knowledge base for a new entity named '{entity_name}'.{role_section}{context_section}

## Your task

A Claude Code session transcript has been written to `_transcript_incoming.txt`
in this directory. Read it to understand the conversation, then construct a
comprehensive wiki from the knowledge and patterns you discover.

## Instructions

1. Read `_transcript_incoming.txt` — the full session transcript.
2. Read `wiki/wiki_schema.md` — the wiki page conventions and structure.
3. Construct the wiki by writing these pages (write as many as warranted):
   - `wiki/index.md` — catalog of all wiki pages
   - `wiki/identity.md` — entity identity: role, working style, values, lessons learned
   - `wiki/log.md` — session log with this session as the first entry
   - `wiki/domain/` — domain knowledge pages (one file per concept/area)
   - `wiki/techniques/` — technique and procedure pages
   - `wiki/projects/` — project-specific knowledge pages
   - `wiki/relationships/` — relationship and collaboration pages

## Quality bar

- **Rich identity page**: capture role, working style, values, and lessons from this session
- **Domain pages**: extract substantive knowledge, NOT just conversation summaries
- **Technique pages**: concrete procedures and patterns that could be reused
- **Cross-references**: link related pages using relative paths
- **Follow wiki_schema.md conventions**: consistent frontmatter, headings, and structure

## Important

- Write all files under `wiki/` — you can overwrite the placeholder identity.md/index.md/log.md
- Do NOT commit — the host process will commit after you finish
- End your response with a one-line summary of what you built (e.g. "Built 12 wiki pages covering Python async patterns and debugging techniques")
"""


def _wiki_update_prompt(
    entity_name: str,
    session_n: int,
    project_context: str | None,
) -> str:
    """Prompt for subsequent-transcript Agent SDK wiki-update sessions."""
    context_section = (
        f"\n**Project context**: {project_context}" if project_context else ""
    )
    return f"""\
You are updating the wiki for entity '{entity_name}' with learnings from session {session_n}.{context_section}

## Your task

A new session transcript has been written to `_transcript_incoming.txt`.
Read it, then update the wiki with new knowledge gained in this session.

## Instructions

1. Read `_transcript_incoming.txt` — the new session transcript.
2. Read `wiki/index.md` — understand the existing wiki structure.
3. Read and update relevant wiki pages with new knowledge:
   - Update `wiki/identity.md` if new values/styles/lessons emerged
   - Update or create domain pages for new concepts covered
   - Update or create technique pages for new procedures learned
   - Append a new entry to `wiki/log.md` for session {session_n}
   - Update `wiki/index.md` — add any new pages you created

## Quality bar

- **Integrate, don't just append**: update existing pages with refined understanding
- **New pages only when genuinely new**: don't fragment knowledge across too many pages
- **Session log entry**: a concise 2-4 sentence summary of what was covered

## Important

- Do NOT commit — the host process will commit after you finish
- End your response with a one-line summary of changes made (e.g. "Added 2 domain pages, updated identity.md with new debugging principles")
"""


# ---------------------------------------------------------------------------
# Agent SDK runner
# ---------------------------------------------------------------------------


async def _run_wiki_agent(entity_dir: Path, prompt: str) -> dict:
    """Run the wiki construction/update agent via Agent SDK.

    Mirror of _run_consolidation_agent in entity_shutdown.py, adapted for
    wiki creation with a larger max_turns budget.
    """
    options = ClaudeAgentOptions(
        cwd=str(entity_dir),
        permission_mode="bypassPermissions",
        max_turns=80,
    )
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            if isinstance(message, ResultMessage):
                return {
                    "success": True,
                    "summary": getattr(message, "content", ""),
                    "error": None,
                }
    return {"success": False, "summary": "", "error": "No result message received"}


# ---------------------------------------------------------------------------
# Per-transcript processing
# ---------------------------------------------------------------------------


def _process_first_transcript(
    entity_dir: Path,
    entity_name: str,
    jsonl_path: Path,
    role: str | None,
    project_context: str | None,
) -> None:
    """Process the first transcript: construct wiki and make initial commit.

    Steps:
    1. Parse and format transcript → _transcript_incoming.txt
    2. Run wiki-creation Agent SDK session
    3. Remove temp file
    4. Archive JSONL to episodic/
    5. Commit everything as "Session 1: initial wiki from transcript"
    """
    # 1. Parse + format
    transcript = parse_session_jsonl(jsonl_path)
    text = format_transcript_text(transcript)

    # 2. Write to temp file
    incoming = entity_dir / "_transcript_incoming.txt"
    incoming.write_text(text, encoding="utf-8")

    # 3. Run wiki agent
    prompt = _wiki_creation_prompt(entity_name, role, project_context)
    result = asyncio.run(_run_wiki_agent(entity_dir, prompt))
    if not result.get("success"):
        raise RuntimeError(
            f"Wiki creation agent failed: {result.get('error', 'unknown error')}"
        )

    # 4. Remove temp file
    incoming.unlink(missing_ok=True)

    # 5. Archive transcript
    episodic_dir = entity_dir / "episodic"
    episodic_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(jsonl_path, episodic_dir / jsonl_path.name)

    # 6. Stage + commit everything
    _run_git(entity_dir, "add", "-A")
    _run_git(entity_dir, "commit", "-m", "Session 1: initial wiki from transcript")


def _process_subsequent_transcript(
    entity_dir: Path,
    entity_name: str,
    jsonl_path: Path,
    session_n: int,
    project_context: str | None,
    skip_consolidation: bool = False,
) -> None:
    """Process a subsequent transcript: update wiki, consolidate, archive.

    Steps:
    1. Parse + format transcript → _transcript_incoming.txt
    2. Run wiki-update Agent SDK session
    3. Remove temp file
    4. Stage wiki, capture diff
    5. Commit wiki changes (allow-empty)
    6. If diff non-empty: run consolidation agent (agent commits memories)
    7. Archive JSONL to episodic/
    8. Commit episodic archive (allow-empty)
    """
    # 1. Parse + format
    transcript = parse_session_jsonl(jsonl_path)
    text = format_transcript_text(transcript)

    # 2. Write to temp file
    incoming = entity_dir / "_transcript_incoming.txt"
    incoming.write_text(text, encoding="utf-8")

    # 3. Run wiki update agent
    prompt = _wiki_update_prompt(entity_name, session_n, project_context)
    result = asyncio.run(_run_wiki_agent(entity_dir, prompt))
    if not result.get("success"):
        raise RuntimeError(
            f"Wiki update agent failed for session {session_n}: "
            f"{result.get('error', 'unknown error')}"
        )

    # 4. Remove temp file
    incoming.unlink(missing_ok=True)

    # 5. Stage wiki + capture diff
    subprocess.run(
        ["git", "-C", str(entity_dir), "add", "wiki/"],
        check=True,
    )
    diff_result = subprocess.run(
        ["git", "-C", str(entity_dir), "diff", "--cached", "HEAD", "--", "wiki/"],
        capture_output=True,
        text=True,
    )
    wiki_diff = diff_result.stdout

    # 6. Commit wiki
    _run_git(
        entity_dir,
        "commit",
        "--allow-empty",
        "-m",
        f"Session {session_n}: wiki update from transcript",
    )

    # 7. Consolidation (if wiki changed and not skipped)
    if wiki_diff.strip() and not skip_consolidation:
        consolidation_prompt = _build_consolidation_prompt(entity_name, wiki_diff)
        asyncio.run(_run_consolidation_agent(entity_dir, consolidation_prompt))

    # 8. Archive transcript
    episodic_dir = entity_dir / "episodic"
    episodic_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(jsonl_path, episodic_dir / jsonl_path.name)

    # 9. Commit episodic archive
    _run_git(entity_dir, "add", "episodic/")
    _run_git(
        entity_dir,
        "commit",
        "--allow-empty",
        "-m",
        f"Session {session_n}: transcript archived",
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def create_entity_from_transcript(
    name: str,
    jsonl_paths: list[Path],
    output_dir: Path,
    role: str | None = None,
    project_context: str | None = None,
) -> FromTranscriptResult:
    """Create a wiki-based entity from one or more Claude Code session transcripts.

    Processes transcripts in order:
    - **First transcript**: creates entity repo, runs wiki-creation agent, commits.
    - **Each subsequent transcript**: runs wiki-update agent, commits wiki changes,
      runs consolidation agent (if wiki changed), archives transcript, commits.

    Args:
        name: Entity name (must match ENTITY_REPO_NAME_PATTERN).
        jsonl_paths: One or more paths to Claude Code session JSONL files,
            processed in order.
        output_dir: Parent directory where the entity repo will be created.
        role: Optional brief description of the entity's role (seeds identity.md).
        project_context: Optional context about the project the transcripts came
            from (helps the agent build better wiki pages).

    Returns:
        FromTranscriptResult with entity details.

    Raises:
        ValueError: If name does not match ENTITY_REPO_NAME_PATTERN.
        FileNotFoundError: If any path in jsonl_paths does not exist.
        RuntimeError: If claude_agent_sdk is not installed, or if an Agent SDK
            session fails.
    """
    # Validate name
    if not ENTITY_REPO_NAME_PATTERN.match(name):
        raise ValueError(
            f"Invalid entity name '{name}'. "
            "Name must start with a lowercase letter and contain only "
            "lowercase letters, digits, underscores, or hyphens."
        )

    # Validate all paths exist
    for path in jsonl_paths:
        if not path.exists():
            raise FileNotFoundError(f"Transcript file not found: {path}")

    # Check Agent SDK is available
    if ClaudeSDKClient is None:
        raise RuntimeError(
            "The 'claude_agent_sdk' package is required for entity creation from "
            "transcripts. Install it with: pip install claude-agent-sdk"
        )

    # Create entity repo (initial commit, empty wiki structure)
    repo_path = create_entity_repo(output_dir, name, role=role)

    # Process first transcript
    _process_first_transcript(repo_path, name, jsonl_paths[0], role, project_context)

    # Process subsequent transcripts
    for session_n, jsonl_path in enumerate(jsonl_paths[1:], start=2):
        _process_subsequent_transcript(
            repo_path, name, jsonl_path, session_n, project_context
        )

    # Count wiki pages (approximate)
    wiki_dir = repo_path / "wiki"
    wiki_pages = len(list(wiki_dir.glob("**/*.md"))) if wiki_dir.exists() else 0

    return FromTranscriptResult(
        entity_name=name,
        entity_path=repo_path,
        transcripts_processed=len(jsonl_paths),
        wiki_pages_written=wiki_pages,
        sessions_archived=len(jsonl_paths),
    )


# Chunk: docs/chunks/entity_ingest_transcript - Ingest transcripts into existing entity
def ingest_transcripts_into_entity(
    name: str,
    jsonl_paths: list[Path],
    project_dir: Path,
    project_context: str | None = None,
    skip_consolidation: bool = False,
) -> IngestTranscriptResult:
    """Ingest session transcripts into an existing wiki-based entity.

    Processes each transcript through the incremental update pipeline:
    wiki update → diff → consolidation (unless skipped) → archive → commit.

    This is the wiki-aware counterpart to `ve entity ingest` (which only
    archives transcripts for episodic search).  Use this command to
    retroactively import productive sessions into an entity that already exists.

    Args:
        name: Entity identifier (must already exist under project_dir/.entities/).
        jsonl_paths: One or more Claude Code session JSONL files, processed in order.
        project_dir: Project root containing .entities/<name>/.
        project_context: Optional description of the project these transcripts came from.
        skip_consolidation: If True, update wiki only, skip memory consolidation.
            Useful when batch-importing many transcripts; run `ve entity shutdown`
            afterwards to consolidate once.

    Returns:
        IngestTranscriptResult with summary of what was processed.

    Raises:
        FileNotFoundError: If any path in jsonl_paths does not exist.
        RuntimeError: If claude_agent_sdk is not installed or an Agent SDK session fails.
        ValueError: If the entity does not exist or is not wiki-based.
    """
    # 1. Validate all JSONL paths exist
    for path in jsonl_paths:
        if not path.exists():
            raise FileNotFoundError(f"Transcript file not found: {path}")

    # 2. Validate Agent SDK is available
    if ClaudeSDKClient is None:
        raise RuntimeError(
            "The 'claude_agent_sdk' package is required for transcript ingestion. "
            "Install it with: pip install claude-agent-sdk"
        )

    # 3. Resolve entity directory
    entities = Entities(project_dir)

    # 4. Validate entity exists
    if not entities.entity_exists(name):
        raise ValueError(f"Entity '{name}' not found")

    # 5. Validate wiki-based format
    if not entities.has_wiki(name):
        raise ValueError(
            f"Entity '{name}' has no wiki/ directory (legacy format). "
            "Run 've entity migrate' to convert it to the wiki-based format first."
        )

    entity_dir = entities.entity_dir(name)

    # 6. Determine starting session_n by counting existing archived JSONL files
    episodic_dir = entity_dir / "episodic"
    existing_count = len(list(episodic_dir.glob("*.jsonl"))) if episodic_dir.exists() else 0
    session_n = existing_count + 1

    # 7. Process each transcript
    for jsonl_path in jsonl_paths:
        _process_subsequent_transcript(
            entity_dir,
            name,
            jsonl_path,
            session_n,
            project_context,
            skip_consolidation,
        )
        session_n += 1

    # 8. Compute wiki page count
    wiki_dir = entity_dir / "wiki"
    wiki_pages_total = len(list(wiki_dir.glob("**/*.md"))) if wiki_dir.exists() else 0

    # 9. Return result
    return IngestTranscriptResult(
        entity_name=name,
        entity_path=entity_dir,
        transcripts_processed=len(jsonl_paths),
        sessions_archived=len(jsonl_paths),
        wiki_pages_total=wiki_pages_total,
    )
