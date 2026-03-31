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
import shutil
from datetime import datetime, timezone
from pathlib import Path

# Chunk: docs/chunks/entity_anthropic_dependency - Guard anthropic import
try:
    import anthropic
except ModuleNotFoundError:
    anthropic = None

from entity_decay import apply_decay
from entity_transcript import SessionTranscript
from models.entity import (
    DecayConfig,
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
# Pre-consolidation snapshot (defense in depth)
# Chunk: docs/chunks/entity_shutdown_memory_wipe - Merge tiers instead of replace
# ---------------------------------------------------------------------------


def _snapshot_tiers(entity_dir: Path) -> None:
    """Create a pre-consolidation snapshot of consolidated and core tiers.

    Overwrites any previous snapshot. Provides single-step recovery for the
    most recent consolidation pass.
    """
    memories_dir = entity_dir / "memories"
    snapshot_dir = memories_dir / ".snapshot_pre_consolidation"

    # Remove previous snapshot
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    for tier_name in ("consolidated", "core"):
        tier_dir = memories_dir / tier_name
        if tier_dir.exists():
            shutil.copytree(tier_dir, snapshot_dir / tier_name)


# ---------------------------------------------------------------------------
# Transcript-based memory extraction (API fallback)
# Chunk: docs/chunks/entity_api_memory_extraction - API fallback extraction
# ---------------------------------------------------------------------------

_MAX_TRANSCRIPT_CHARS = 100_000


def _format_transcript_text(
    transcript: SessionTranscript,
    max_chars: int = _MAX_TRANSCRIPT_CHARS,
) -> str:
    """Render transcript turns as readable [USER]/[ASSISTANT] blocks.

    Truncates to the last max_chars characters so long sessions don't
    exceed API context limits.
    """
    blocks = []
    for turn in transcript.turns:
        label = "[USER]" if turn.role == "user" else "[ASSISTANT]"
        blocks.append(f"{label}: {turn.text}")
    text = "\n\n".join(blocks)
    if len(text) > max_chars:
        text = text[-max_chars:]
    return text


# Chunk: docs/chunks/entity_api_memory_extraction - API fallback extraction
def extract_memories_from_transcript(
    transcript: SessionTranscript,
    api_key: str | None = None,
) -> str:
    """Extract memories from a session transcript via Anthropic API.

    Formats the transcript as a readable conversation, sends it with
    EXTRACTION_PROMPT to the API, and returns raw JSON string of
    extracted memories (compatible with run_consolidation's
    extracted_memories_json parameter).

    Returns "[]" immediately for empty transcripts (no API call).
    """
    if not transcript.turns:
        return "[]"

    if anthropic is None:
        raise RuntimeError(
            "The 'anthropic' package is required for transcript-based memory "
            "extraction. Install it with: pip install anthropic"
        )

    formatted = _format_transcript_text(transcript)
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": formatted}],
    )
    return response.content[0].text


# Chunk: docs/chunks/entity_api_memory_extraction - Full fallback shutdown pipeline
def shutdown_from_transcript(
    entity_name: str,
    transcript: SessionTranscript,
    project_dir: Path,
    api_key: str | None = None,
    decay_config: DecayConfig | None = None,
) -> dict:
    """Full shutdown pipeline using a transcript instead of agent-provided memories.

    1. Extract memories from transcript via API
    2. Run consolidation (journals → consolidated → core)
    3. Apply decay
    4. Return summary dict
    """
    extracted_json = extract_memories_from_transcript(transcript, api_key=api_key)
    return run_consolidation(
        entity_name=entity_name,
        extracted_memories_json=extracted_json,
        project_dir=project_dir,
        api_key=api_key,
        decay_config=decay_config,
    )


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def run_consolidation(
    entity_name: str,
    extracted_memories_json: str,
    project_dir: Path,
    api_key: str | None = None,
    decay_config: DecayConfig | None = None,
) -> dict:
    """Run the full consolidation pipeline for an entity.

    1. Parse extracted memories
    2. Write each new journal memory to .entities/<name>/memories/journal/
    3. Load existing consolidated and core memories from disk
    4. If too few memories and no existing tiers, skip consolidation
    5. Format consolidation prompt and call Anthropic API
    6. Parse response and write updated tier structures
    7. Apply decay to bound memory growth
    8. Return summary

    # Chunk: docs/chunks/entity_memory_decay — decay integration

    Args:
        entity_name: Name of the entity.
        extracted_memories_json: JSON string of extracted memories array.
        project_dir: Project root directory.
        api_key: Optional Anthropic API key (uses env var if None).
        decay_config: Optional decay configuration. If None, uses default DecayConfig.

    Returns:
        Summary dict: {"journals_added": N, "journals_consolidated": J,
                        "consolidated": M, "core": K, "expired": E, "demoted": D}
    """
    from entities import Entities

    entities = Entities(project_dir)

    # Step 1: Parse extracted memories
    parsed = parse_extracted_memories(extracted_memories_json)

    # Step 2: Write new journal memories to disk
    for fm, content in parsed:
        entities.write_memory(entity_name, fm, content)

    # Chunk: docs/chunks/entity_consolidate_existing - Read existing journals from disk
    # Step 2b: Read ALL journal entries from disk (includes just-written + pre-existing)
    journal_dir = entities.entity_dir(entity_name) / "memories" / MemoryTier.JOURNAL.value
    existing_journal_entries = []
    journal_file_map = {}  # title -> path, for cleanup later
    if journal_dir.exists():
        for f in sorted(journal_dir.glob("*.md")):
            fm, content = entities.parse_memory(f)
            if fm:
                d = fm.model_dump(mode="json")
                d["content"] = content
                existing_journal_entries.append(d)
                journal_file_map[fm.title] = f

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

    # Step 4: Skip consolidation if no journals on disk and no existing tiers
    if not existing_journal_entries and not existing_consolidated_mems and not existing_core_mems:
        return {
            "journals_added": len(parsed),
            "journals_consolidated": 0,
            "consolidated": 0,
            "core": 0,
            "expired": 0,
            "demoted": 0,
        }

    if (
        not existing_consolidated_mems
        and not existing_core_mems
        and len(existing_journal_entries) < 3
    ):
        return {
            "journals_added": len(parsed),
            "journals_consolidated": len(existing_journal_entries),
            "consolidated": 0,
            "core": 0,
            "expired": 0,
            "demoted": 0,
        }

    # Step 5: Format prompt and call API
    if anthropic is None:
        raise RuntimeError(
            "The 'anthropic' package is required for memory consolidation. "
            "Install it with: pip install anthropic"
        )

    # Use all journal entries from disk (existing + just-written) for consolidation
    prompt = format_consolidation_prompt(
        new_journals=existing_journal_entries,
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

    # Snapshot tiers before any modifications (defense in depth)
    # Chunk: docs/chunks/entity_shutdown_memory_wipe - Merge tiers instead of replace
    _snapshot_tiers(entities.entity_dir(entity_name))

    # Step 7: Merge updated tiers (preserve existing, add/update from LLM response)
    # Chunk: docs/chunks/entity_shutdown_memory_wipe - Merge tiers instead of replace

    for tier_key, tier_dir in [
        ("consolidated", consolidated_dir),
        ("core", core_dir),
    ]:
        # Build lookup of existing memory files on disk: {title: Path}
        existing_by_title: dict[str, Path] = {}
        if tier_dir.exists():
            for f in sorted(tier_dir.glob("*.md")):
                fm_existing, _ = entities.parse_memory(f)
                if fm_existing:
                    existing_by_title[fm_existing.title] = f

        for entry in consolidation_result[tier_key]:
            fm = entry["frontmatter"]
            content = entry["content"]
            # If title matches an existing file, overwrite it (delete old, write new)
            if fm.title in existing_by_title:
                existing_by_title[fm.title].unlink()
            entities.write_memory(entity_name, fm, content)

    # Chunk: docs/chunks/entity_consolidate_existing - Remove consolidated journal files
    # Journal files that were consolidated (not in unconsolidated list) are deleted
    unconsolidated_titles = set(consolidation_result["unconsolidated"])
    for title, path in journal_file_map.items():
        if title not in unconsolidated_titles and path.exists():
            path.unlink()

    # Step 8: Apply decay to bound memory growth
    # Chunk: docs/chunks/entity_memory_decay — decay integration
    if decay_config is None:
        decay_config = DecayConfig()

    now = datetime.now(timezone.utc)

    # Collect all memories from disk for decay analysis
    all_memories_for_decay = []

    # Journal tier: check unconsolidated journals for tier-0 expiry
    if journal_dir.exists():
        for f in sorted(journal_dir.glob("*.md")):
            fm, content = entities.parse_memory(f)
            if fm:
                all_memories_for_decay.append((fm, content, f))

    # Consolidated tier: all files (existing preserved + newly written)
    if consolidated_dir.exists():
        for f in sorted(consolidated_dir.glob("*.md")):
            fm, content = entities.parse_memory(f)
            if fm:
                all_memories_for_decay.append((fm, content, f))

    # Core tier: all files (existing preserved + newly written)
    if core_dir.exists():
        for f in sorted(core_dir.glob("*.md")):
            fm, content = entities.parse_memory(f)
            if fm:
                all_memories_for_decay.append((fm, content, f))

    decay_result = apply_decay(all_memories_for_decay, now, decay_config)

    # Apply decay decisions
    expired_count = 0
    demoted_count = 0

    # Expirations: remove files from disk
    for fm, content, path in decay_result.expirations:
        if path.exists():
            path.unlink()
        expired_count += 1

    # Demotions: rewrite memory with new tier
    for fm, content, path, new_tier in decay_result.demotions:
        # Write to new tier directory
        entities.write_memory(entity_name, fm, content)
        # Remove from old location
        if path.exists():
            path.unlink()
        demoted_count += 1

    # Log decay events
    if decay_result.events:
        entities.append_decay_events(entity_name, decay_result.events)

    return {
        "journals_added": len(parsed),
        "journals_consolidated": len(existing_journal_entries),
        "consolidated": len(consolidation_result["consolidated"]),
        "core": len(consolidation_result["core"]),
        "expired": expired_count,
        "demoted": demoted_count,
    }
