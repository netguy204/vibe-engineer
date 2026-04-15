"""LLM-assisted wiki conflict resolution for entity merge operations.

# Chunk: docs/chunks/entity_fork_merge - LLM-assisted wiki conflict resolution

When two entity repos are merged and wiki pages have conflicting edits,
the conflicts are knowledge synthesis problems — not code conflicts. This
module parses git conflict markers from wiki markdown files and uses the
Anthropic API to synthesize both versions into a single coherent page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Chunk: docs/chunks/entity_anthropic_dependency - Guard anthropic import
try:
    import anthropic
except ModuleNotFoundError:
    anthropic = None


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


def resolve_wiki_conflict(
    filename: str,
    conflicted_content: str,
    entity_name: str,
) -> str:
    """Use the Anthropic API to synthesize conflicting wiki page versions.

    Args:
        filename: Relative path of the file (for context in prompt).
        conflicted_content: Full file content including git conflict markers.
        entity_name: Name of the entity being merged (for prompt context).

    Returns:
        Synthesized content with all conflict markers resolved.

    Raises:
        RuntimeError: If anthropic is not installed or the API call fails.
    """
    if anthropic is None:
        raise RuntimeError(
            "The 'anthropic' package is not installed. "
            "Install it with: pip install anthropic"
        )

    hunks = parse_conflict_markers(conflicted_content)
    n = len(hunks)

    prompt = (
        f"You are {entity_name}, an AI specialist with persistent knowledge across projects.\n"
        f"You are merging two versions of your wiki page: {filename}.\n\n"
        f"The file has {n} conflict(s) where your knowledge diverged. For each conflict,\n"
        f"Version A reflects knowledge from one context and Version B reflects knowledge\n"
        f"from another context.\n\n"
        f"Your task: synthesize these conflicts into a single coherent version that preserves\n"
        f"ALL valuable knowledge from both contexts. Do not discard either side — find the\n"
        f"synthesis that a single expert would write having had both experiences.\n\n"
        f"Return the COMPLETE file content with all conflict markers resolved.\n"
        f"Output only the file content, no commentary.\n\n"
        f"--- File with conflict markers ---\n"
        f"{conflicted_content}"
    )

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-3-5-haiku-latest",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text
