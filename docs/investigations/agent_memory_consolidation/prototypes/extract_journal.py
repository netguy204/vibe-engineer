"""
Extract memory-worthy journal entries from a parsed day segment using Claude.

Takes a day's parsed conversation and asks the LLM to identify memories worth
keeping — behavioral corrections, skills learned, domain insights, confirmations,
and autonomy calibration moments.

Each memory gets:
- A short title
- The memory content (what was learned, not what happened)
- A valence (positive/negative/neutral)
- A category (correction, confirmation, skill, domain, coordination, autonomy)
- A salience score (1-5, how important this is for future sessions)

Usage:
    uv run python prototypes/extract_journal.py <day_file.json> [--output <file>]
    uv run python prototypes/extract_journal.py parsed_days/  # process all days

Requires ANTHROPIC_API_KEY environment variable.
"""

import anthropic
import json
import sys
from pathlib import Path

EXTRACTION_PROMPT = """\
You are a memory extraction system for a long-running AI agent. You are reading
a transcript of one day's interactions between the agent and its operator.

Your job: identify moments in this conversation that the agent should REMEMBER
across session boundaries. Focus on things that would prevent the operator from
having to retrain the agent.

Categories of memory-worthy events (in priority order):

1. **correction**: The operator corrected the agent's behavior or approach.
   Extract WHAT the agent was doing wrong and WHAT it should do instead.

2. **skill**: The agent learned a workflow, procedure, or pattern through
   interaction. Extract the skill as a reusable instruction.

3. **domain**: The operator taught the agent something about the problem domain
   — how entities relate, what distinctions matter, invariant rules.

4. **confirmation**: The operator validated the agent's approach. Extract what
   was confirmed so the agent doesn't drift away from it.

5. **coordination**: The agent learned something about how to coordinate with
   other agents or async processes.

6. **autonomy**: The operator calibrated when the agent should act vs ask,
   take initiative vs wait.

For each memory, provide:
- **title**: 3-8 word summary
- **content**: 1-3 sentences capturing what was learned (NOT what happened —
  frame as knowledge/skill, not narrative)
- **valence**: "positive" (something that worked), "negative" (something to avoid),
  or "neutral" (factual knowledge)
- **category**: one of the categories above
- **salience**: 1-5 (5 = critical skill the agent keeps forgetting, 1 = minor detail)

IMPORTANT:
- Extract the LESSON, not the story. "Always check PR state before acting on it"
  not "On March 14th, the operator pointed out the PR was already merged."
- Be specific enough to be actionable. "Use exact-match keys instead of prefix
  matching" not "Be careful with matching."
- If the operator explicitly says "remember this" or "update your SOP", that's
  salience 5.
- Confirmation memories are important too — they anchor what's working.
- Aim for 5-20 memories per day. Not every message is memory-worthy.

Respond with a JSON array of memory objects. No other text.

Example output:
```json
[
  {
    "title": "Check PR state before acting",
    "content": "Before taking action on a PR (rebasing, updating, etc.), always verify its current state. PRs may have been merged or closed while the agent was working on something else.",
    "valence": "negative",
    "category": "correction",
    "salience": 4
  },
  {
    "title": "Verification query after data reload",
    "content": "After triggering a data reload, always run the verification query to confirm the new data looks correct before proceeding to the next task.",
    "valence": "positive",
    "category": "skill",
    "salience": 3
  }
]
```

Here is today's conversation transcript:
"""


def load_day(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def format_transcript(day_data: dict) -> str:
    """Format a day's entries into a readable transcript for the LLM."""
    lines = []
    for entry in day_data["entries"]:
        ts = entry.get("timestamp", "")
        # Truncate to HH:MM for readability
        time_str = ts[11:16] if len(ts) > 16 else ""

        if entry["type"] == "user":
            lines.append(f"[{time_str}] OPERATOR: {entry['text']}")
        elif entry["type"] == "assistant":
            lines.append(f"[{time_str}] AGENT: {entry['text']}")
        elif entry["type"] == "system":
            lines.append(f"[{time_str}] SYSTEM: {entry.get('subtype', 'event')}")
        elif entry["type"] == "queue":
            lines.append(f"[{time_str}] QUEUE ({entry.get('operation', '')}): {entry.get('content', '')}")

    return "\n\n".join(lines)


def extract_memories(day_data: dict, client: anthropic.Anthropic) -> list[dict]:
    """Use Claude to extract memory-worthy events from a day's transcript."""
    transcript = format_transcript(day_data)
    char_count = len(transcript)

    print(f"  Transcript: {char_count:,} characters")

    # For very long transcripts, we may need to chunk. For now, send as-is
    # and let the model handle it. Claude's context window is large enough.
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": EXTRACTION_PROMPT + transcript,
            }
        ],
    )

    # Parse the response
    text = response.content[0].text

    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("\n", 1)[0]
    if text.startswith("json\n"):
        text = text[5:]

    try:
        memories = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  WARNING: Failed to parse LLM response as JSON: {e}")
        print(f"  Raw response (first 500 chars): {text[:500]}")
        return []

    return memories


def process_day(day_path: Path, client: anthropic.Anthropic, output_path: Path | None = None):
    """Process a single day file and extract journal memories."""
    day_data = load_day(day_path)
    date = day_data["date"]
    stats = day_data["stats"]

    print(f"\nProcessing {date}: {stats['user_messages']} user msgs, {stats['assistant_messages']} agent msgs")

    if stats["total_entries"] < 3:
        print("  Skipping — too few entries")
        return []

    memories = extract_memories(day_data, client)

    print(f"  Extracted {len(memories)} memories")

    # Add metadata
    for mem in memories:
        mem["source_date"] = date
        mem["tier"] = 0  # Journal tier

    # Summarize by category
    from collections import Counter
    cats = Counter(m.get("category", "unknown") for m in memories)
    for cat, count in cats.most_common():
        print(f"    {cat}: {count}")

    # Write output
    if output_path is None:
        output_path = day_path.parent / f"journal_{date}.json"
    with open(output_path, "w") as f:
        json.dump(memories, f, indent=2)
    print(f"  Written to {output_path}")

    return memories


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <day_file.json|parsed_days_dir/> [--output <file>]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var

    output_path = None
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        output_path = Path(sys.argv[idx + 1])

    if input_path.is_dir():
        # Process all day files in directory
        all_memories = []
        day_files = sorted(input_path.glob("day_*.json"))
        print(f"Found {len(day_files)} day files in {input_path}")

        output_dir = input_path.parent / "journal"
        output_dir.mkdir(exist_ok=True)

        for day_file in day_files:
            date = day_file.stem.replace("day_", "")
            day_output = output_dir / f"journal_{date}.json"
            memories = process_day(day_file, client, day_output)
            all_memories.extend(memories)

        # Write combined journal
        combined_path = output_dir / "journal_all.json"
        with open(combined_path, "w") as f:
            json.dump(all_memories, f, indent=2)
        print(f"\nCombined journal: {len(all_memories)} memories written to {combined_path}")

    else:
        # Process single day file
        process_day(input_path, client, output_path)


if __name__ == "__main__":
    main()
