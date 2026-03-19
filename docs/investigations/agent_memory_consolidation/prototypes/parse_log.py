"""
Parse a Claude Code JSONL conversation log and segment by day boundaries.

Outputs a structured representation of each day's conversation, filtered to
memory-relevant content (user messages, assistant text, system events).
Strips tool results and mechanical metadata to reduce noise.

Usage:
    uv run python prototypes/parse_log.py <logfile.jsonl> [--output-dir <dir>]

Writes one JSON file per day to the output directory.
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def parse_timestamp(ts_str: str) -> datetime:
    """Parse ISO timestamp from log entry."""
    # Handle both Z and +00:00 suffixes
    ts_str = ts_str.replace("Z", "+00:00")
    return datetime.fromisoformat(ts_str)


def extract_text_content(message: dict) -> str | None:
    """Extract human-readable text from a message's content blocks."""
    content = message.get("message", {}).get("content", [])
    if isinstance(content, str):
        return content

    texts = []
    for block in content:
        if isinstance(block, str):
            texts.append(block)
        elif isinstance(block, dict):
            if block.get("type") == "text":
                texts.append(block["text"])
            elif block.get("type") == "tool_result":
                # Skip tool results - they're mechanical noise
                pass
            elif block.get("type") == "tool_use":
                # Record that a tool was used, but not the full input
                tool_name = block.get("name", "unknown")
                texts.append(f"[tool_use: {tool_name}]")
    return "\n".join(texts) if texts else None


def is_memory_relevant(entry: dict) -> bool:
    """Filter to entries that could contain memory-worthy content."""
    entry_type = entry.get("type")

    # Always include user and assistant messages
    if entry_type in ("user", "assistant"):
        return True

    # Include system events (compaction, errors)
    if entry_type == "system":
        return True

    # Include queue operations (async coordination)
    if entry_type == "queue-operation":
        return True

    # Skip: progress, file-history-snapshot, pr-link, last-prompt, tool_result
    return False


def get_entry_timestamp(entry: dict) -> datetime | None:
    """Extract timestamp from any entry type."""
    ts = entry.get("timestamp")
    if ts:
        return parse_timestamp(ts)

    # Some entries have timestamp nested in message
    msg_ts = entry.get("message", {}).get("timestamp")
    if msg_ts:
        return parse_timestamp(msg_ts)

    return None


def segment_by_day(entries: list[dict]) -> dict[str, list[dict]]:
    """Group entries by calendar date, using UTC."""
    days = defaultdict(list)
    for entry in entries:
        ts = get_entry_timestamp(entry)
        if ts:
            day_key = ts.strftime("%Y-%m-%d")
            days[day_key].append(entry)
    return dict(sorted(days.items()))


def summarize_entry(entry: dict) -> dict | None:
    """Produce a compact summary of a memory-relevant entry."""
    entry_type = entry.get("type")
    ts = get_entry_timestamp(entry)
    ts_str = ts.isoformat() if ts else None

    if entry_type == "user":
        text = extract_text_content(entry)
        if not text or len(text.strip()) == 0:
            return None
        return {
            "type": "user",
            "timestamp": ts_str,
            "text": text,
        }

    elif entry_type == "assistant":
        text = extract_text_content(entry)
        if not text or len(text.strip()) == 0:
            return None
        return {
            "type": "assistant",
            "timestamp": ts_str,
            "text": text,
        }

    elif entry_type == "system":
        subtype = entry.get("subtype")
        # Skip turn_duration markers - they're just timing metadata
        if subtype == "turn_duration":
            return None
        return {
            "type": "system",
            "subtype": subtype,
            "timestamp": ts_str,
        }

    elif entry_type == "queue-operation":
        op = entry.get("operation")
        content = entry.get("content", "")
        return {
            "type": "queue",
            "operation": op,
            "timestamp": ts_str,
            "content": content[:200],  # Truncate long content
        }

    return None


def process_log(log_path: Path, output_dir: Path):
    """Parse log, segment by day, write filtered output."""
    print(f"Reading {log_path}...")

    entries = []
    parse_errors = 0
    with open(log_path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                parse_errors += 1

    print(f"Parsed {len(entries)} entries ({parse_errors} parse errors)")

    # Filter to memory-relevant entries
    relevant = [e for e in entries if is_memory_relevant(e)]
    print(f"Memory-relevant entries: {len(relevant)} / {len(entries)} ({100*len(relevant)/len(entries):.1f}%)")

    # Segment by day
    days = segment_by_day(relevant)
    print(f"Days found: {len(days)}")

    output_dir.mkdir(parents=True, exist_ok=True)

    for day_key, day_entries in days.items():
        # Summarize each entry
        summaries = []
        for entry in day_entries:
            summary = summarize_entry(entry)
            if summary:
                summaries.append(summary)

        # Compute stats
        user_msgs = sum(1 for s in summaries if s["type"] == "user")
        asst_msgs = sum(1 for s in summaries if s["type"] == "assistant")
        total_chars = sum(len(s.get("text", "")) for s in summaries)

        day_data = {
            "date": day_key,
            "stats": {
                "total_entries": len(summaries),
                "user_messages": user_msgs,
                "assistant_messages": asst_msgs,
                "total_characters": total_chars,
            },
            "entries": summaries,
        }

        out_path = output_dir / f"day_{day_key}.json"
        with open(out_path, "w") as f:
            json.dump(day_data, f, indent=2)

        print(f"  {day_key}: {len(summaries)} entries, {user_msgs} user, {asst_msgs} assistant, {total_chars:,} chars")

    print(f"\nOutput written to {output_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <logfile.jsonl> [--output-dir <dir>]")
        sys.exit(1)

    log_path = Path(sys.argv[1])

    output_dir = Path(__file__).parent / "parsed_days"
    if "--output-dir" in sys.argv:
        idx = sys.argv.index("--output-dir")
        output_dir = Path(sys.argv[idx + 1])

    process_log(log_path, output_dir)
