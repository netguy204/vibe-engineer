"""
Consolidate journal memories into higher tiers (the "dreaming" step).

Takes all journal entries (tier 0) and:
1. Groups related memories
2. Merges duplicates/near-duplicates into consolidated memories (tier 1)
3. Promotes highly recurring or high-salience patterns to core memories (tier 2)

The consolidation is LSTM-inspired:
- Tier 0 (journal): Raw daily memories, high volume, ephemeral
- Tier 1 (consolidated): Patterns seen across multiple days, merged and refined
- Tier 2 (core): Persistent skills and understanding, loaded at every startup

Usage:
    uv run python prototypes/consolidate.py <journal_dir/> [--output-dir <dir>]

Requires ANTHROPIC_API_KEY environment variable.
"""

import anthropic
import json
import sys
from pathlib import Path


CONSOLIDATION_PROMPT = """\
You are a memory consolidation system for a long-running AI agent. You are
performing the "dreaming" step — reviewing all raw journal memories and
consolidating them into higher-tier persistent memories.

You have two jobs:

## Job 1: Create CONSOLIDATED memories (tier 1)

Look for journal memories that are about the same topic, skill, or pattern.
Merge them into a single consolidated memory that captures the full picture.

Rules:
- If 2+ journal entries cover the same skill/correction, merge into one
  consolidated memory with richer content
- If a correction and a later confirmation cover the same behavior, the
  consolidated memory should reflect the RESOLVED understanding
- Increase salience when a pattern recurs (the agent kept needing this reminder)
- A consolidated memory should be self-contained — someone reading it with no
  other context should understand the full lesson

## Job 2: Create CORE memories (tier 2)

Promote to core when:
- A skill is referenced 3+ times across different days
- The operator explicitly marked something as critical (salience 5)
- The memory represents a fundamental operating principle, not a specific technique
- The memory captures the agent's role, identity, or relationship with the operator

Core memories should be CONCISE and PRINCIPLE-LEVEL:
- "Always verify state before acting on assumptions" not the specific steps
- "The operator prefers autonomous action within established workflows but
  wants to be consulted for novel situations"

## Output format

Return a JSON object with two arrays:

```json
{
  "consolidated": [
    {
      "title": "...",
      "content": "...",
      "valence": "positive|negative|neutral",
      "category": "...",
      "salience": 1-5,
      "tier": 1,
      "source_memories": ["title of source 1", "title of source 2"],
      "recurrence_count": 3
    }
  ],
  "core": [
    {
      "title": "...",
      "content": "...",
      "valence": "positive|negative|neutral",
      "category": "...",
      "salience": 5,
      "tier": 2,
      "source_memories": ["title of source 1", "..."],
      "recurrence_count": 5
    }
  ],
  "unconsolidated": [
    "title of journal memory that didn't merge with anything"
  ]
}
```

Guidelines:
- consolidated memories: aim for 30-60% fewer entries than input journal memories
- core memories: aim for 5-15 total (these load at every startup, must be compact)
- unconsolidated: journal memories that are standalone and don't merge with anything
  (these remain at tier 0)

Here are all the journal memories to consolidate:
"""


INCREMENTAL_PROMPT = """\
You are performing INCREMENTAL memory consolidation. You have existing
consolidated (tier 1) and core (tier 2) memories from previous consolidation
cycles. New journal memories have arrived from today's interactions.

Your job: integrate the new memories into the existing tier structure.

Rules:
- If a new journal memory matches an existing consolidated memory, UPDATE the
  existing one (increase recurrence_count, refine content if the new memory
  adds nuance)
- If a new journal memory doesn't match anything, create a new consolidated
  memory OR leave it unconsolidated
- If an existing consolidated memory now has enough recurrence (3+) or salience
  to be promoted to core, promote it
- NEVER remove existing core memories unless they directly contradict new evidence
- Core memories can be REFINED with new understanding but should remain stable

Output the COMPLETE updated tier structure (not just changes).

## Existing consolidated memories (tier 1):
{existing_consolidated}

## Existing core memories (tier 2):
{existing_core}

## New journal memories to integrate:
{new_journals}

Return the same JSON format as a full consolidation:
```json
{{
  "consolidated": [...],
  "core": [...],
  "unconsolidated": [...]
}}
```
"""


def load_journals(journal_dir: Path) -> list[dict]:
    """Load all journal files and combine."""
    all_memories = []
    for f in sorted(journal_dir.glob("journal_*.json")):
        if f.name == "journal_all.json":
            continue
        with open(f) as fh:
            memories = json.load(fh)
            all_memories.extend(memories)
    return all_memories


def load_existing_tiers(output_dir: Path) -> tuple[list[dict], list[dict]]:
    """Load existing consolidated and core memories if they exist."""
    consolidated = []
    core = []

    consolidated_path = output_dir / "tier1_consolidated.json"
    core_path = output_dir / "tier2_core.json"

    if consolidated_path.exists():
        with open(consolidated_path) as f:
            consolidated = json.load(f)
    if core_path.exists():
        with open(core_path) as f:
            core = json.load(f)

    return consolidated, core


def full_consolidation(journals: list[dict], client: anthropic.Anthropic) -> dict:
    """Perform full consolidation of all journal memories."""
    print(f"Full consolidation of {len(journals)} journal memories...")

    prompt = CONSOLIDATION_PROMPT + json.dumps(journals, indent=2)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text

    # Strip markdown code fences
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    return json.loads(text)


def incremental_consolidation(
    new_journals: list[dict],
    existing_consolidated: list[dict],
    existing_core: list[dict],
    client: anthropic.Anthropic,
) -> dict:
    """Perform incremental consolidation with existing tiers."""
    print(f"Incremental consolidation: {len(new_journals)} new + {len(existing_consolidated)} consolidated + {len(existing_core)} core...")

    prompt = INCREMENTAL_PROMPT.format(
        existing_consolidated=json.dumps(existing_consolidated, indent=2),
        existing_core=json.dumps(existing_core, indent=2),
        new_journals=json.dumps(new_journals, indent=2),
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    return json.loads(text)


def print_summary(result: dict):
    """Print a summary of consolidation results."""
    consolidated = result.get("consolidated", [])
    core = result.get("core", [])
    unconsolidated = result.get("unconsolidated", [])

    print(f"\n{'='*60}")
    print(f"CONSOLIDATION RESULTS")
    print(f"{'='*60}")
    print(f"  Tier 2 (core):          {len(core)} memories")
    print(f"  Tier 1 (consolidated):  {len(consolidated)} memories")
    print(f"  Tier 0 (unconsolidated): {len(unconsolidated)} memories")

    if core:
        print(f"\n--- Core Memories (tier 2) ---")
        for mem in core:
            print(f"  [{mem.get('salience', '?')}] {mem['title']}")
            print(f"      {mem['content'][:100]}...")
            print()

    if consolidated:
        print(f"--- Consolidated Memories (tier 1) ---")
        from collections import Counter
        cats = Counter(m.get("category", "unknown") for m in consolidated)
        for cat, count in cats.most_common():
            print(f"  {cat}: {count}")

    # Compute token estimate
    core_text = json.dumps(core, indent=2)
    consolidated_titles = [{"title": m["title"], "category": m.get("category")} for m in consolidated]
    index_text = json.dumps(consolidated_titles, indent=2)
    startup_chars = len(core_text) + len(index_text)
    # Rough estimate: 4 chars per token
    startup_tokens = startup_chars // 4

    print(f"\n--- Startup Payload Estimate ---")
    print(f"  Core memories (full):     {len(core_text):,} chars (~{len(core_text)//4:,} tokens)")
    print(f"  Consolidated index:       {len(index_text):,} chars (~{len(index_text)//4:,} tokens)")
    print(f"  Total startup context:    {startup_chars:,} chars (~{startup_tokens:,} tokens)")
    print(f"  Target: <4K tokens        {'PASS' if startup_tokens < 4000 else 'OVER BUDGET'}")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <journal_dir/> [--output-dir <dir>]")
        sys.exit(1)

    journal_dir = Path(sys.argv[1])
    output_dir = journal_dir.parent / "tiers"
    if "--output-dir" in sys.argv:
        idx = sys.argv.index("--output-dir")
        output_dir = Path(sys.argv[idx + 1])

    output_dir.mkdir(parents=True, exist_ok=True)

    client = anthropic.Anthropic()

    journals = load_journals(journal_dir)
    print(f"Loaded {len(journals)} journal memories")

    # Check for existing tiers (incremental mode)
    existing_consolidated, existing_core = load_existing_tiers(output_dir)

    if existing_consolidated or existing_core:
        print("Found existing tiers — running incremental consolidation")
        result = incremental_consolidation(journals, existing_consolidated, existing_core, client)
    else:
        print("No existing tiers — running full consolidation")
        result = full_consolidation(journals, client)

    # Write results
    consolidated_path = output_dir / "tier1_consolidated.json"
    core_path = output_dir / "tier2_core.json"
    unconsolidated_path = output_dir / "tier0_unconsolidated.json"

    with open(consolidated_path, "w") as f:
        json.dump(result.get("consolidated", []), f, indent=2)

    with open(core_path, "w") as f:
        json.dump(result.get("core", []), f, indent=2)

    with open(unconsolidated_path, "w") as f:
        json.dump(result.get("unconsolidated", []), f, indent=2)

    print_summary(result)
    print(f"\nResults written to {output_dir}")


if __name__ == "__main__":
    main()
