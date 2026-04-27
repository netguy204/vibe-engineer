---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/entity_shutdown.py
- tests/test_entity_shutdown.py
code_references:
- ref: src/entity_shutdown.py#_format_transcript_text
  implements: "Renders SessionTranscript turns as [USER]/[ASSISTANT] blocks with truncation"
- ref: src/entity_shutdown.py#extract_memories_from_transcript
  implements: "Calls Anthropic API with EXTRACTION_PROMPT + formatted transcript; returns raw JSON"
- ref: src/entity_shutdown.py#shutdown_from_transcript
  implements: "Full fallback shutdown pipeline: extract memories via API then run consolidation"
- ref: tests/test_entity_shutdown.py
  implements: "Tests for _format_transcript_text, extract_memories_from_transcript, and shutdown_from_transcript; module also covers strip_code_fences, parse_extracted_memories, format_consolidation_prompt, parse_consolidation_response, run_consolidation, wiki diff/consolidation, and timezone normalization regression tests (TestTimezoneNormalization, added by shutdown_tz_normalization)"
narrative: null
investigation: entity_session_harness
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_transcript_extractor
created_after:
- entity_session_tracking
---

# Chunk Goal

## Minor Goal

Add an API-driven memory extraction function to `src/entity_shutdown.py` that accepts
a `SessionTranscript` (from `entity_transcript.py`) and extracts memory-worthy events
via the Anthropic API, without requiring a live Claude Code session.

### Context

The primary entity shutdown flow works like this:
1. Inside a live Claude Code session, the agent reflects on its conversation
2. The agent writes extracted memories as JSON to a temp file
3. `ve entity shutdown <name> --memories-file <file>` runs consolidation

A **fallback path** handles cases when the agent can't self-reflect (e.g., the
user hit Ctrl+C). Instead of relying on the agent, the fallback:
1. Reads the archived JSONL transcript
2. Parses it into a SessionTranscript via entity_transcript.py
3. Formats it as a readable conversation
4. Calls the Anthropic API with the existing `EXTRACTION_PROMPT` + conversation text
5. Parses the result into memory JSON compatible with `run_consolidation()`

### What to build

Add to `src/entity_shutdown.py`:

```python
def extract_memories_from_transcript(
    transcript: SessionTranscript,
    api_key: str | None = None,
) -> str:
    """Extract memories from a session transcript via Anthropic API.

    Formats the transcript as a readable conversation, sends it with
    EXTRACTION_PROMPT to the API, and returns raw JSON string of
    extracted memories (compatible with run_consolidation's
    extracted_memories_json parameter).
    """
```

The function should:
1. Format the transcript turns as `[USER]: ...\n[ASSISTANT]: ...` blocks
2. Prepend the existing `EXTRACTION_PROMPT` as a system message
3. Send the formatted conversation as a user message asking the model to extract memories
4. Return the raw JSON response text (the same format that `parse_extracted_memories` expects)

Also add a convenience function that does the full pipeline:

```python
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
```

This calls `extract_memories_from_transcript()` then passes the result to the
existing `run_consolidation()`.

### Design decisions

- **Reuse EXTRACTION_PROMPT**: The same prompt used by `/entity-shutdown` works here.
  It's designed to review a conversation and extract lessons — it doesn't matter
  whether the conversation is in the model's context or presented as text.
- **Model choice**: Use the same model as consolidation (`claude-sonnet-4-20250514`).
  The extraction is a structured task, not creative work.
- **Token limits**: Session transcripts can be large (15K+ words for long sessions).
  The function should truncate to a reasonable limit if needed (e.g., last 100K chars).

## Success Criteria

- `extract_memories_from_transcript` accepts a SessionTranscript and returns valid memory JSON
- The returned JSON is parseable by the existing `parse_extracted_memories` function
- `shutdown_from_transcript` runs the full pipeline: extract → consolidate → decay
- The function handles empty transcripts gracefully (returns empty memory list)
- The function truncates very large transcripts rather than exceeding API limits
- Tests mock the Anthropic API call and verify the formatting + parsing pipeline