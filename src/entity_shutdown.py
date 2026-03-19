"""Entity shutdown (sleep cycle): extract journal memories and consolidate tiers.

# Chunk: docs/chunks/entity_shutdown_skill

The shutdown skill performs the "sleep" cycle for a named entity:
1. Parse extracted journal memories (from the agent's own session reflection)
2. Run incremental consolidation against existing memory tiers via the Anthropic API
3. Write all updated memories to the entity's memory directory

The extraction happens in the slash command (agent reflects on its own context).
The consolidation happens here via API call (structured data transform).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from models.entity import (
    MemoryCategory,
    MemoryFrontmatter,
    MemoryTier,
    MemoryValence,
)


# ---------------------------------------------------------------------------
# Prompts (adapted from investigation prototypes)
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """\
You are reflecting on your own conversation session to extract memory-worthy
events. Review the conversation you just had with the operator and identify
moments worth REMEMBERING across session boundaries.

Focus on things that would prevent the operator from having to retrain you.

Categories of memory-worthy events (in priority order):

1. **correction**: The operator corrected your behavior or approach.
   Extract WHAT you were doing wrong and WHAT you should do instead.

2. **skill**: You learned a workflow, procedure, or pattern through
   interaction. Extract the skill as a reusable instruction.

3. **domain**: The operator taught you something about the problem domain
   — how entities relate, what distinctions matter, invariant rules.

4. **confirmation**: The operator validated your approach. Extract what
   was confirmed so you don't drift away from it.

5. **coordination**: You learned something about how to coordinate with
   other agents or async processes.

6. **autonomy**: The operator calibrated when you should act vs ask,
   take initiative vs wait.

For each memory, provide:
- **title**: 3-8 word summary
- **content**: 1-3 sentences capturing what was learned (NOT what happened —
  frame as knowledge/skill, not narrative)
- **valence**: "positive" (something that worked), "negative" (something to avoid),
  or "neutral" (factual knowledge)
- **category**: one of the categories above
- **salience**: 1-5 (5 = critical skill you keep forgetting, 1 = minor detail)

IMPORTANT:
- Extract the LESSON, not the story. "Always check PR state before acting on it"
  not "On March 14th, the operator pointed out the PR was already merged."
- Be specific enough to be actionable. "Use exact-match keys instead of prefix
  matching" not "Be careful with matching."
- If the operator explicitly says "remember this" or "update your SOP", that's
  salience 5.
- Confirmation memories are important too — they anchor what's working.
- Aim for 5-20 memories per session. Not every message is memory-worthy.

Respond with a JSON array of memory objects. No other text.

Example output:
```json
[
  {
    "title": "Check PR state before acting",
    "content": "Before taking action on a PR (rebasing, updating, etc.), always verify its current state. PRs may have been merged or closed while working on something else.",
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
"""

INCREMENTAL_CONSOLIDATION_PROMPT = """\
You are performing INCREMENTAL memory consolidation. You have existing
consolidated (tier 1) and core (tier 2) memories from previous consolidation
cycles. New journal memories have arrived from today's interactions.

Your job: integrate the new memories into the existing tier structure.

Rules:
- If a new journal memory matches an existing consolidated memory, UPDATE the
  existing one (increase recurrence_count, refine content if the new memory
  adds nuance, update last_reinforced to now)
- If a new journal memory doesn't match anything, create a new consolidated
  memory OR leave it unconsolidated
- If an existing consolidated memory now has enough recurrence (3+) or salience
  to be promoted to core, promote it
- NEVER remove existing core memories unless they directly contradict new evidence
- Core memories can be REFINED with new understanding but should remain stable

Promotion to core when:
- A skill is referenced 3+ times across different sessions
- The operator explicitly marked something as critical (salience 5)
- The memory represents a fundamental operating principle, not a specific technique
- The memory captures the agent's role, identity, or relationship with the operator

Core memories should be CONCISE and PRINCIPLE-LEVEL:
- "Always verify state before acting on assumptions" not the specific steps
- Aim for 5-15 total core memories (these load at every startup, must be compact)

Output the COMPLETE updated tier structure (not just changes).

## Existing consolidated memories (tier 1):
{existing_consolidated}

## Existing core memories (tier 2):
{existing_core}

## New journal memories to integrate:
{new_journals}

Return a JSON object with this exact format:
```json
{{
  "consolidated": [
    {{
      "title": "...",
      "content": "...",
      "valence": "positive|negative|neutral",
      "category": "correction|skill|domain|confirmation|coordination|autonomy",
      "salience": 1-5,
      "tier": "consolidated",
      "source_memories": ["title of source 1", "title of source 2"],
      "recurrence_count": 3,
      "last_reinforced": "ISO 8601 timestamp"
    }}
  ],
  "core": [
    {{
      "title": "...",
      "content": "...",
      "valence": "positive|negative|neutral",
      "category": "...",
      "salience": 5,
      "tier": "core",
      "source_memories": ["title of source 1", "..."],
      "recurrence_count": 5,
      "last_reinforced": "ISO 8601 timestamp"
    }}
  ],
  "unconsolidated": [
    "title of journal memory that didn't merge with anything"
  ]
}}
```
"""


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def strip_code_fences(text: str) -> str:
    """Remove markdown code fences from LLM JSON output.

    Handles patterns like:
    - ```json\\n...\\n```
    - ```\\n...\\n```
    - Leading/trailing whitespace
    """
    text = text.strip()

    # Pattern: ```json\n...\n```  or ```\n...\n```
    match = re.match(r"^```(?:json)?\s*\n(.*?)\n\s*```\s*$", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return text


# ---------------------------------------------------------------------------
# Parsing functions
# ---------------------------------------------------------------------------

# Valid enum values for lenient validation
_VALID_CATEGORIES = {c.value for c in MemoryCategory}
_VALID_VALENCES = {v.value for v in MemoryValence}
_TIER_MAP = {0: "journal", 1: "consolidated", 2: "core"}


def parse_extracted_memories(
    raw_json: str,
) -> list[tuple[MemoryFrontmatter, str]]:
    """Parse the JSON array from the extraction step into validated memories.

    Each element should have title, content, category, valence, salience.
    This function adds defaults for tier (JOURNAL), last_reinforced (now),
    recurrence_count (0), source_memories (empty).

    Tolerant of extra fields and minor format variations (e.g., integer tiers).

    Returns:
        List of (MemoryFrontmatter, content_body) tuples.
        Invalid entries are silently skipped.
    """
    cleaned = strip_code_fences(raw_json)
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return []

    if not isinstance(data, list):
        return []

    now = datetime.now(timezone.utc)
    results: list[tuple[MemoryFrontmatter, str]] = []

    for entry in data:
        if not isinstance(entry, dict):
            continue

        # Extract content body (separate from frontmatter)
        content = entry.get("content", "")

        # Normalize tier: prototype used integers
        tier_raw = entry.get("tier", "journal")
        if isinstance(tier_raw, int):
            tier_raw = _TIER_MAP.get(tier_raw, "journal")

        # Validate category and valence
        category = entry.get("category", "")
        if category not in _VALID_CATEGORIES:
            continue
        valence = entry.get("valence", "")
        if valence not in _VALID_VALENCES:
            continue

        # Build frontmatter dict with defaults
        fm_dict = {
            "title": entry.get("title", "Untitled memory"),
            "category": category,
            "valence": valence,
            "salience": entry.get("salience", 3),
            "tier": tier_raw,
            "last_reinforced": entry.get("last_reinforced", now),
            "recurrence_count": entry.get("recurrence_count", 0),
            "source_memories": entry.get("source_memories", []),
        }

        try:
            fm = MemoryFrontmatter.model_validate(fm_dict)
            results.append((fm, content))
        except Exception:
            continue

    return results


def format_consolidation_prompt(
    new_journals: list[dict],
    existing_consolidated: list[dict],
    existing_core: list[dict],
) -> str:
    """Format the incremental consolidation prompt with the three memory sets.

    Args:
        new_journals: List of new journal memory dicts.
        existing_consolidated: List of existing tier-1 memory dicts.
        existing_core: List of existing tier-2 memory dicts.

    Returns:
        Formatted prompt string ready for the API call.
    """
    return INCREMENTAL_CONSOLIDATION_PROMPT.format(
        existing_consolidated=json.dumps(existing_consolidated, indent=2),
        existing_core=json.dumps(existing_core, indent=2),
        new_journals=json.dumps(new_journals, indent=2),
    )


def parse_consolidation_response(raw_json: str) -> dict:
    """Parse the consolidation LLM response.

    Returns:
        Dict with keys 'consolidated', 'core', 'unconsolidated'.
        Each consolidated/core entry is validated against MemoryFrontmatter.
        Returns empty structure on parse failure.
    """
    cleaned = strip_code_fences(raw_json)
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return {"consolidated": [], "core": [], "unconsolidated": []}

    if not isinstance(data, dict):
        return {"consolidated": [], "core": [], "unconsolidated": []}

    now = datetime.now(timezone.utc)
    result: dict = {"consolidated": [], "core": [], "unconsolidated": []}

    # Parse consolidated and core tiers
    for tier_key, expected_tier in [
        ("consolidated", "consolidated"),
        ("core", "core"),
    ]:
        for entry in data.get(tier_key, []):
            if not isinstance(entry, dict):
                continue

            # Normalize tier field
            tier_raw = entry.get("tier", expected_tier)
            if isinstance(tier_raw, int):
                tier_raw = _TIER_MAP.get(tier_raw, expected_tier)

            fm_dict = {
                "title": entry.get("title", "Untitled"),
                "category": entry.get("category", "domain"),
                "valence": entry.get("valence", "neutral"),
                "salience": entry.get("salience", 3),
                "tier": tier_raw,
                "last_reinforced": entry.get("last_reinforced", now),
                "recurrence_count": entry.get("recurrence_count", 0),
                "source_memories": entry.get("source_memories", []),
            }

            try:
                fm = MemoryFrontmatter.model_validate(fm_dict)
                result[tier_key].append({
                    "frontmatter": fm,
                    "content": entry.get("content", ""),
                })
            except Exception:
                continue

    # Unconsolidated is just a list of title strings
    unconsolidated = data.get("unconsolidated", [])
    if isinstance(unconsolidated, list):
        result["unconsolidated"] = [
            t for t in unconsolidated if isinstance(t, str)
        ]

    return result


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def run_consolidation(
    entity_name: str,
    extracted_memories_json: str,
    project_dir: Path,
    api_key: str | None = None,
) -> dict:
    """Run the full consolidation pipeline for an entity.

    1. Parse extracted memories
    2. Write each new journal memory to .entities/<name>/memories/journal/
    3. Load existing consolidated and core memories from disk
    4. If too few memories and no existing tiers, skip consolidation
    5. Format consolidation prompt and call Anthropic API
    6. Parse response and write updated tier structures
    7. Return summary

    Args:
        entity_name: Name of the entity.
        extracted_memories_json: JSON string of extracted memories array.
        project_dir: Project root directory.
        api_key: Optional Anthropic API key (uses env var if None).

    Returns:
        Summary dict: {"journals_added": N, "consolidated": M, "core": K}
    """
    from entities import Entities

    entities = Entities(project_dir)

    # Step 1: Parse extracted memories
    parsed = parse_extracted_memories(extracted_memories_json)

    if not parsed:
        return {"journals_added": 0, "consolidated": 0, "core": 0}

    # Step 2: Write journal memories to disk
    for fm, content in parsed:
        entities.write_memory(entity_name, fm, content)

    # Step 3: Load existing consolidated and core memories
    existing_consolidated_mems = []
    existing_core_mems = []

    consolidated_dir = (
        entities.entity_dir(entity_name) / "memories" / MemoryTier.CONSOLIDATED.value
    )
    core_dir = (
        entities.entity_dir(entity_name) / "memories" / MemoryTier.CORE.value
    )

    if consolidated_dir.exists():
        for f in sorted(consolidated_dir.glob("*.md")):
            fm, content = entities.parse_memory(f)
            if fm:
                d = fm.model_dump(mode="json")
                d["content"] = content
                existing_consolidated_mems.append(d)

    if core_dir.exists():
        for f in sorted(core_dir.glob("*.md")):
            fm, content = entities.parse_memory(f)
            if fm:
                d = fm.model_dump(mode="json")
                d["content"] = content
                existing_core_mems.append(d)

    # Step 4: Skip consolidation if too few memories and no existing tiers
    if (
        not existing_consolidated_mems
        and not existing_core_mems
        and len(parsed) < 3
    ):
        return {
            "journals_added": len(parsed),
            "consolidated": 0,
            "core": 0,
        }

    # Step 5: Format prompt and call API
    new_journals_dicts = []
    for fm, content in parsed:
        d = fm.model_dump(mode="json")
        d["content"] = content
        new_journals_dicts.append(d)

    prompt = format_consolidation_prompt(
        new_journals=new_journals_dicts,
        existing_consolidated=existing_consolidated_mems,
        existing_core=existing_core_mems,
    )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_response = response.content[0].text

    # Step 6: Parse response
    consolidation_result = parse_consolidation_response(raw_response)

    # Step 7: Write updated tiers (clear and rewrite)
    # Write new files first, then delete old ones for safety

    # -- Consolidated tier --
    new_consolidated_paths = []
    for entry in consolidation_result["consolidated"]:
        fm = entry["frontmatter"]
        content = entry["content"]
        path = entities.write_memory(entity_name, fm, content)
        new_consolidated_paths.append(path)

    # Remove old consolidated files (those not just written)
    if consolidated_dir.exists():
        for f in consolidated_dir.glob("*.md"):
            if f not in new_consolidated_paths:
                f.unlink()

    # -- Core tier --
    new_core_paths = []
    for entry in consolidation_result["core"]:
        fm = entry["frontmatter"]
        content = entry["content"]
        path = entities.write_memory(entity_name, fm, content)
        new_core_paths.append(path)

    # Remove old core files (those not just written)
    if core_dir.exists():
        for f in core_dir.glob("*.md"):
            if f not in new_core_paths:
                f.unlink()

    return {
        "journals_added": len(parsed),
        "consolidated": len(consolidation_result["consolidated"]),
        "core": len(consolidation_result["core"]),
    }
