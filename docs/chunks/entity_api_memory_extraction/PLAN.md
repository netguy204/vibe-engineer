
<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add two functions to `src/entity_shutdown.py`:

1. **`extract_memories_from_transcript(transcript, api_key)`** — a pure extraction
   function that formats a `SessionTranscript` as readable conversation text and
   calls the Anthropic API with the existing `EXTRACTION_PROMPT` as the system
   message. Returns the raw JSON string the API produces (already compatible with
   `parse_extracted_memories`).

2. **`shutdown_from_transcript(entity_name, transcript, project_dir, api_key,
   decay_config)`** — the full fallback pipeline: call `extract_memories_from_transcript`,
   then hand the result straight to the existing `run_consolidation()`.

A private helper `_format_transcript_text(transcript, max_chars)` handles:
- Rendering each `Turn` as a `[USER]: ...` / `[ASSISTANT]: ...` block with double-newline
  separation
- Truncating the formatted string to the last `max_chars` characters (default 100 000)
  so very long sessions don't exceed API limits

The API call mirrors the pattern already used in `run_consolidation()`:
```python
client = anthropic.Anthropic(api_key=api_key)
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    system=EXTRACTION_PROMPT,
    messages=[{"role": "user", "content": formatted_text}],
)
```

Empty transcripts (`turns == []`) are handled without an API call — the function
returns `"[]"` immediately, which `parse_extracted_memories` correctly parses as an
empty list.

Following the project's TDD philosophy: tests are written first (failing), then
the implementation is written to make them pass.

## Subsystem Considerations

No existing entity subsystem is documented. The entity shutdown / memory pipeline
is a cluster of related `entity_*` chunks but has not yet been captured as a
subsystem. This chunk is not the right place to formalize that — it's a focused
addition to an existing module.

## Sequence

### Step 1: Write failing tests for `_format_transcript_text`

In `tests/test_entity_shutdown.py`, add a `TestFormatTranscriptText` class that
imports and tests the private helper (tests can access private functions directly).

Tests to write:
- `test_formats_user_and_assistant_turns` — two turns produce the expected
  `[USER]: ...\n\n[ASSISTANT]: ...` string.
- `test_empty_transcript_returns_empty_string` — zero turns → empty string.
- `test_truncates_to_max_chars` — a transcript that would exceed `max_chars` is
  truncated to that length (i.e. `len(result) <= max_chars`).
- `test_truncation_cuts_from_front` — truncation keeps the *last* `max_chars`
  characters (most recent context is preserved).

All tests must fail at this point (`_format_transcript_text` doesn't exist yet).

### Step 2: Implement `_format_transcript_text`

Add the private helper to `src/entity_shutdown.py`, just before
`extract_memories_from_transcript`:

```python
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
```

Run the Step 1 tests — they should now pass.

### Step 3: Write failing tests for `extract_memories_from_transcript`

In `tests/test_entity_shutdown.py`, add `TestExtractMemoriesFromTranscript`:

- `test_returns_empty_json_for_empty_transcript` — `SessionTranscript` with no
  turns → function returns `"[]"` without making any API call (assert the
  anthropic mock is NOT called).
- `test_calls_api_with_extraction_prompt_as_system` — non-empty transcript →
  the mocked `client.messages.create` is called with `system=EXTRACTION_PROMPT`.
- `test_calls_api_with_formatted_transcript_as_user_message` — the `messages`
  kwarg contains a user message whose content includes `"[USER]:"` (verifying
  the formatter was used).
- `test_returns_raw_api_response_text` — the function returns exactly the text
  from `response.content[0].text`, not a parsed form.
- `test_truncates_large_transcript` — build a transcript where each turn has 10K
  chars of text; assert the user message sent to the API is ≤ 100 000 chars.
- `test_uses_claude_sonnet_model` — assert `model="claude-sonnet-4-20250514"`.

Use `unittest.mock.patch("entity_shutdown.anthropic")` as done in existing
shutdown tests.

All tests must fail before implementation.

### Step 4: Implement `extract_memories_from_transcript`

Add the function to `src/entity_shutdown.py` immediately after
`_format_transcript_text`:

```python
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
```

Add `SessionTranscript` to the import from `entity_transcript`:
```python
from entity_transcript import SessionTranscript
```

Run Step 3 tests — all should pass.

### Step 5: Write failing tests for `shutdown_from_transcript`

In `tests/test_entity_shutdown.py`, add `TestShutdownFromTranscript`:

- `test_calls_extract_then_consolidation` — patch both
  `entity_shutdown.extract_memories_from_transcript` and
  `entity_shutdown.run_consolidation`; assert both are called in order, and that
  `run_consolidation` receives the output of the extract call as
  `extracted_memories_json`.
- `test_passes_api_key_through` — assert `extract_memories_from_transcript` is
  called with the provided `api_key`.
- `test_passes_decay_config_through` — assert `run_consolidation` is called with
  the provided `decay_config`.
- `test_returns_consolidation_summary` — assert the return value of
  `shutdown_from_transcript` matches the mock return value from `run_consolidation`.
- `test_empty_transcript_completes_without_api_call` — empty transcript: extract
  returns `"[]"`, `run_consolidation` is still called (so journals/decay run), but
  no Anthropic client is instantiated.

All tests must fail before implementation.

### Step 6: Implement `shutdown_from_transcript`

Add immediately after `extract_memories_from_transcript`:

```python
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
```

Run Step 5 tests — all should pass.

### Step 7: Update GOAL.md code_paths

Update the `code_paths` field in `docs/chunks/entity_api_memory_extraction/GOAL.md`:

```yaml
code_paths:
  - src/entity_shutdown.py
  - tests/test_entity_shutdown.py
```

### Step 8: Run the full test suite

```bash
uv run pytest tests/
```

All tests must pass, including the existing shutdown tests. If any pre-existing
tests break (e.g., import changes), fix them before completing the chunk.

## Dependencies

- `entity_transcript_extractor` chunk must be complete — this chunk imports
  `SessionTranscript` from `src/entity_transcript.py`.
- The `anthropic` Python package must be available (it's already a project
  dependency — existing consolidation code uses it).

## Risks and Open Questions

- **`SessionTranscript` import placement**: `entity_shutdown.py` currently has no
  import from `entity_transcript`. Adding it at module top-level is clean, but we
  must verify there are no circular imports (both live in `src/` alongside
  `entities.py`, `entity_decay.py`, etc.).
- **`max_tokens` for extraction**: The EXTRACTION_PROMPT asks for 5–20 memories as
  a JSON array. 4096 tokens should be more than sufficient, but if sessions are
  pathologically long and the model tries to extract many memories, we may need to
  bump to 8192. Start at 4096 and note the risk.
- **Very large transcripts**: The 100K char truncation keeps the *tail* of the
  session. For most workflows this is right (the most recent interactions are most
  memory-worthy). But it may miss important early-session corrections. If this
  becomes a problem, a future chunk can implement smarter summarization or chunked
  extraction.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?
-->
