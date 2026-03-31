"""Prototype: Extract searchable text from Claude Code JSONL session transcripts.

Explores different extraction and chunking strategies for episodic search indexing.
"""

import json
import sys
from pathlib import Path
from dataclasses import dataclass, field


CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


@dataclass
class Turn:
    """A single conversational turn (user prompt or assistant response)."""
    role: str  # "user" or "assistant"
    text: str
    timestamp: str
    uuid: str
    tool_uses: list[str] = field(default_factory=list)  # tool names used
    has_code: bool = False


@dataclass
class SessionTranscript:
    """Extracted transcript from a Claude Code session."""
    session_id: str
    turns: list[Turn]

    @property
    def user_turns(self) -> list[Turn]:
        return [t for t in self.turns if t.role == "user"]

    @property
    def assistant_turns(self) -> list[Turn]:
        return [t for t in self.turns if t.role == "assistant"]

    def full_text(self) -> str:
        """All text concatenated, for baseline search."""
        return "\n\n".join(
            f"[{t.role.upper()}]: {t.text}" for t in self.turns if t.text.strip()
        )

    def user_text_only(self) -> str:
        """Just user prompts — the 'intent' signal."""
        return "\n\n".join(t.text for t in self.user_turns if t.text.strip())

    def dialogue_pairs(self) -> list[str]:
        """User prompt + assistant response paired together as chunks."""
        chunks = []
        for i, turn in enumerate(self.turns):
            if turn.role == "user" and turn.text.strip():
                # Find the next assistant response
                response = ""
                for j in range(i + 1, len(self.turns)):
                    if self.turns[j].role == "assistant" and self.turns[j].text.strip():
                        response = self.turns[j].text
                        break
                    elif self.turns[j].role == "user":
                        break
                chunks.append(f"Q: {turn.text}\nA: {response}" if response else f"Q: {turn.text}")
        return chunks


def extract_text_from_message(message: dict) -> str:
    """Extract human-readable text from a Claude Code message object."""
    if not message:
        return ""

    content = message.get("content", "")

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                block_type = block.get("type", "")
                if block_type == "text":
                    parts.append(block.get("text", ""))
                elif block_type == "tool_use":
                    # Skip tool input (noisy), but note the tool name
                    pass
                elif block_type == "tool_result":
                    # Skip tool results by default (very noisy)
                    pass
        return "\n".join(parts)

    return ""


def get_tool_names(message: dict) -> list[str]:
    """Extract tool names used in a message."""
    if not message:
        return []
    content = message.get("content", [])
    if not isinstance(content, list):
        return []
    return [
        block.get("name", "unknown")
        for block in content
        if isinstance(block, dict) and block.get("type") == "tool_use"
    ]


def parse_session_jsonl(jsonl_path: Path) -> SessionTranscript:
    """Parse a Claude Code session JSONL file into a SessionTranscript."""
    session_id = jsonl_path.stem
    turns = []

    # Accumulate text per assistant response (multiple JSONL lines per response)
    current_assistant_text = []
    current_assistant_tools = []
    current_assistant_ts = None
    current_assistant_uuid = None
    current_request_id = None

    def flush_assistant():
        nonlocal current_assistant_text, current_assistant_tools
        nonlocal current_assistant_ts, current_assistant_uuid, current_request_id
        if current_assistant_text or current_assistant_tools:
            text = "\n".join(current_assistant_text)
            turns.append(Turn(
                role="assistant",
                text=text,
                timestamp=current_assistant_ts or "",
                uuid=current_assistant_uuid or "",
                tool_uses=current_assistant_tools,
                has_code="```" in text,
            ))
        current_assistant_text = []
        current_assistant_tools = []
        current_assistant_ts = None
        current_assistant_uuid = None
        current_request_id = None

    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type", "")

            # Skip non-message entries
            if entry_type in ("file-history-snapshot",):
                continue

            # Skip meta/system messages
            if entry.get("isMeta"):
                continue

            if entry_type == "user":
                flush_assistant()
                message = entry.get("message", {})
                text = extract_text_from_message(message)
                if text.strip():
                    turns.append(Turn(
                        role="user",
                        text=text,
                        timestamp=entry.get("timestamp", ""),
                        uuid=entry.get("uuid", ""),
                    ))

            elif entry_type == "assistant":
                request_id = entry.get("requestId", "")
                # New assistant response vs continuation
                if request_id != current_request_id:
                    flush_assistant()
                    current_request_id = request_id
                    current_assistant_ts = entry.get("timestamp", "")
                    current_assistant_uuid = entry.get("uuid", "")

                message = entry.get("message", {})
                text = extract_text_from_message(message)
                tools = get_tool_names(message)
                if text.strip():
                    current_assistant_text.append(text)
                if tools:
                    current_assistant_tools.extend(tools)

    flush_assistant()
    return SessionTranscript(session_id=session_id, turns=turns)


def find_project_sessions_dir(project_path: str) -> Path:
    """Find the Claude Code sessions directory for a project path."""
    encoded = "-" + project_path.strip("/").replace("/", "-")
    return CLAUDE_PROJECTS_DIR / encoded


# --- Analysis utilities ---

def print_extraction_stats(transcript: SessionTranscript):
    """Print stats about what was extracted."""
    full = transcript.full_text()
    user_only = transcript.user_text_only()
    pairs = transcript.dialogue_pairs()

    print(f"Session: {transcript.session_id}")
    print(f"  Turns: {len(transcript.turns)} ({len(transcript.user_turns)} user, {len(transcript.assistant_turns)} assistant)")
    print(f"  Full text: {len(full):,} chars / {len(full.split()):,} words")
    print(f"  User text only: {len(user_only):,} chars / {len(user_only.split()):,} words")
    print(f"  Dialogue pairs: {len(pairs)} chunks")

    # Tool usage distribution
    all_tools = []
    for t in transcript.assistant_turns:
        all_tools.extend(t.tool_uses)
    if all_tools:
        from collections import Counter
        top_tools = Counter(all_tools).most_common(5)
        print(f"  Top tools: {', '.join(f'{name}({n})' for name, n in top_tools)}")

    # Code presence
    code_turns = sum(1 for t in transcript.assistant_turns if t.has_code)
    print(f"  Turns with code: {code_turns}/{len(transcript.assistant_turns)}")
    print()


if __name__ == "__main__":
    project_dir = "/Users/btaylor/Projects/vibe-engineer"
    sessions_dir = find_project_sessions_dir(project_dir)

    # Work directly with JSONL files on disk (index may be stale)
    jsonl_files = sorted(sessions_dir.glob("*.jsonl"), key=lambda p: p.stat().st_size, reverse=True)

    print(f"=== Extraction Stats for {len(jsonl_files)} Sessions (top 5 by size) ===\n")

    transcripts = []
    for jsonl_path in jsonl_files[:5]:
        transcript = parse_session_jsonl(jsonl_path)
        print_extraction_stats(transcript)
        transcripts.append(transcript)

    # Show sample dialogue pairs from the largest session
    if transcripts:
        transcript = transcripts[0]
        pairs = transcript.dialogue_pairs()
        print(f"\n=== Sample Dialogue Pairs (session {transcript.session_id[:8]}) ===\n")
        for i, pair in enumerate(pairs[:5]):
            print(f"--- Pair {i+1} ---")
            # Truncate long pairs
            if len(pair) > 500:
                print(pair[:500] + "...[truncated]")
            else:
                print(pair)
            print()
