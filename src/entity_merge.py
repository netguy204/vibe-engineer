"""LLM-assisted wiki conflict resolution for entity merge operations.

# Chunk: docs/chunks/entity_fork_merge - LLM-assisted wiki conflict resolution

When two entity repos are merged and wiki pages have conflicting edits,
the conflicts are knowledge synthesis problems — not code conflicts. This
module parses git conflict markers from wiki markdown files and uses the
Claude Code agent SDK (or Anthropic API as fallback) to synthesize both
versions into a single coherent page.
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass

# Chunk: docs/chunks/entity_anthropic_dependency - Guard anthropic import
try:
    import anthropic
except ModuleNotFoundError:
    anthropic = None

# Chunk: docs/chunks/entity_sync_ergonomics - Guard claude_agent_sdk import for wiki resolver
try:
    from claude_agent_sdk import ClaudeSDKClient
    from claude_agent_sdk.types import ClaudeAgentOptions, ResultMessage
except ModuleNotFoundError:
    ClaudeSDKClient = None
    ClaudeAgentOptions = None
    ResultMessage = None

# Chunk: docs/chunks/entity_sync_ergonomics - Centralized model for Anthropic SDK fallback
_RESOLVER_MODEL = "claude-haiku-4-20250514"


@dataclass
class ConflictHunk:
    """A single conflict region parsed from a file with git conflict markers."""

    ours: str    # content between <<<<<<< and =======
    theirs: str  # content between ======= and >>>>>>>


# Pattern matching standard git conflict markers
_CONFLICT_PATTERN = re.compile(
    r"<<<<<<<[^\n]*\n(.*?)\n=======\n(.*?)\n>>>>>>>[^\n]*",
    re.DOTALL,
)


def parse_conflict_markers(content: str) -> list[ConflictHunk]:
    """Parse all conflict hunks from a file with git conflict markers.

    Args:
        content: Full file content that may contain git conflict markers.

    Returns:
        List of ConflictHunk instances. Empty list if no conflicts are present.
    """
    hunks = []
    for match in _CONFLICT_PATTERN.finditer(content):
        hunks.append(ConflictHunk(ours=match.group(1), theirs=match.group(2)))
    return hunks


def _build_resolver_prompt(
    entity_name: str,
    filename: str,
    n: int,
    conflicted_content: str,
) -> str:
    """Build the conflict-resolution prompt used by both SDK paths."""
    return (
        f"You are {entity_name}, an AI specialist with persistent knowledge across projects.\n"
        f"You are merging two versions of your knowledge file: {filename}.\n\n"
        f"The file has {n} conflict(s) where your knowledge diverged. For each conflict,\n"
        f"the content between <<<<<<< HEAD and ======= is Version A, and the content\n"
        f"between ======= and >>>>>>> is Version B.\n\n"
        f"Your task: synthesize these conflicts into a single coherent version that preserves\n"
        f"ALL valuable knowledge from both contexts. Do not discard either side — find the\n"
        f"synthesis that a single expert would write having had both experiences. For\n"
        f"structured content like tables, take the more-progressed status of each row.\n\n"
        f"The complete file body is included below. You do NOT need to read any files or\n"
        f"call any tools — respond directly with the synthesized file content.\n\n"
        f"Return the COMPLETE file content with EVERY conflict marker (<<<<<<<, =======,\n"
        f">>>>>>>) removed. Output only the file content, no commentary, no code fence.\n\n"
        f"--- File with conflict markers ---\n"
        f"{conflicted_content}"
    )


# Chunk: docs/chunks/entity_sync_ergonomics - Agent SDK async resolver for wiki conflicts
async def _resolve_with_agent_sdk(prompt: str, cwd: pathlib.Path) -> str:
    """Run the conflict-resolution prompt via Claude Code agent SDK.

    Uses the operator's claude CLI subscription — no ANTHROPIC_API_KEY needed.
    """
    options = ClaudeAgentOptions(
        cwd=str(cwd),
        permission_mode="bypassPermissions",
        max_turns=5,
    )
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            if isinstance(message, ResultMessage):
                if message.is_error or not message.result:
                    raise RuntimeError(
                        f"Agent SDK conflict resolver returned an error: {message.result}"
                    )
                return message.result
    raise RuntimeError("Agent SDK conflict resolver did not return a result")


def resolve_wiki_conflict(
    filename: str,
    conflicted_content: str,
    entity_name: str,
    entity_dir: pathlib.Path | None = None,
) -> str:
    """Use the Claude Code agent SDK (or Anthropic API fallback) to synthesize
    conflicting wiki page versions.

    Args:
        filename: Relative path of the file (for context in prompt).
        conflicted_content: Full file content including git conflict markers.
        entity_name: Name of the entity being merged (for prompt context).
        entity_dir: Path to the entity directory (used as cwd for agent SDK).
            Defaults to the current working directory when not provided.

    Returns:
        Synthesized content with all conflict markers resolved.

    Raises:
        RuntimeError: If neither SDK is available, or the API call fails.
    """
    import asyncio

    hunks = parse_conflict_markers(conflicted_content)
    n = len(hunks)
    prompt = _build_resolver_prompt(entity_name, filename, n, conflicted_content)

    cwd = entity_dir if entity_dir is not None else pathlib.Path.cwd()

    # Primary: Claude Code agent SDK (uses operator's Max subscription)
    if ClaudeSDKClient is not None:
        return asyncio.run(_resolve_with_agent_sdk(prompt, cwd))

    # Fallback: Anthropic SDK (requires ANTHROPIC_API_KEY)
    if anthropic is None:
        raise RuntimeError(
            "Wiki conflict resolution requires either the 'claude_agent_sdk' package "
            "(install with: pip install claude-agent-sdk) or the 'anthropic' package "
            "with ANTHROPIC_API_KEY set."
        )

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=_RESOLVER_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
