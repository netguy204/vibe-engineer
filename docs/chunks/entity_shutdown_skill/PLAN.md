

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The shutdown skill has two distinct phases that happen in sequence:

1. **Extraction** — The agent (the LLM itself, not an API call) reviews its own session transcript and identifies memory-worthy events, outputting structured journal memories. This is implemented as a slash command (`/entity-shutdown`) whose prompt instructs the agent to reflect on its conversation and produce memories.

2. **Incremental consolidation** — New journal memories are integrated into the entity's existing memory tiers. This is also LLM-driven: the prompt presents existing consolidated/core memories alongside new journals and asks for an updated tier structure. The consolidation logic lives in domain code (`src/entity_shutdown.py`) that formats the prompt, but the actual consolidation judgment is the LLM's.

**Key design decision: The agent IS the extractor.** The investigation's prototype used the Anthropic API to call Claude as a sub-agent. In production, the shutdown skill is invoked as the agent reflecting on its own session — the agent's own context IS the transcript. The extraction prompt (from `prototypes/extract_journal.py`) becomes the instruction in the slash command. This is explicitly called out in the GOAL.md's rejected ideas: "using the agent's own context produces more accurate salience judgments than a cold external model reading a transcript."

**However, consolidation requires an API call.** The agent has just extracted N new journal memories. To consolidate them against existing tiers, it needs to read existing memories from disk, format a consolidation prompt, and get a structured response. This could be done by the agent itself (reading files, reasoning about associations), but the investigation's incremental consolidation prompt is specifically designed for structured JSON input/output. We use the Anthropic API for this step — it's a deterministic transform on structured data, not a reflection on the agent's own experience.

**Two entry points, one pipeline:**
- `/entity-shutdown` slash command — The operator runs this manually (or a future harness calls it). The command template instructs the agent to: (1) extract memories from its session, (2) call `ve entity shutdown <name>` with the extracted memories as JSON input.
- `ve entity shutdown <name>` CLI command — Receives extracted memories (JSON on stdin or as a file argument), runs incremental consolidation via API, writes updated memory files.

This separation keeps the extraction (agent-reflective, needs full context) in the slash command and the consolidation (structured data transform, needs API) in the CLI.

**Testing strategy:** Per TESTING_PHILOSOPHY.md, TDD for the domain logic. The consolidation prompt formatting, memory reading/writing, and JSON parsing are all testable without API calls. The actual LLM consolidation is tested by mocking the API response. The slash command template is not unit-tested (it's prompt text), but its integration is validated by running the full pipeline against example data.

## Subsystem Considerations

- **docs/subsystems/template_system** (DOCUMENTED): This chunk USES the template system to create the `/entity-shutdown` slash command template in `src/templates/commands/`.

## Sequence

### Step 1: Define the shutdown domain module

Create `src/entity_shutdown.py` with the core logic for the consolidation phase:

- `EXTRACTION_PROMPT: str` — Adapted from `prototypes/extract_journal.py`. This constant is used by the slash command template. It is the same prompt, but with minor refinements: (a) output format matches `MemoryFrontmatter` schema (uses string tier names not integers), (b) includes `last_reinforced` and `recurrence_count` fields in output.

- `INCREMENTAL_CONSOLIDATION_PROMPT: str` — Adapted from `prototypes/consolidate.py`'s `INCREMENTAL_PROMPT`. Uses `{existing_consolidated}`, `{existing_core}`, `{new_journals}` placeholders. Output format matches the memory schema.

- `parse_extracted_memories(raw_json: str) -> list[tuple[MemoryFrontmatter, str]]` — Parses the JSON array from the extraction step. Each element has `title`, `content`, `category`, `valence`, `salience`. This function adds defaults for `tier` (JOURNAL), `last_reinforced` (now), `recurrence_count` (0), `source_memories` (empty). Returns list of (frontmatter, content) tuples. Validates each memory against `MemoryFrontmatter`.

- `format_consolidation_prompt(new_journals: list[dict], existing_consolidated: list[dict], existing_core: list[dict]) -> str` — Formats the incremental consolidation prompt with the three memory sets serialized as JSON.

- `parse_consolidation_response(raw_json: str) -> dict` — Parses the consolidation LLM response. Returns dict with keys `consolidated`, `core`, `unconsolidated`. Validates each memory object against the schema.

- `strip_code_fences(text: str) -> str` — Utility to remove markdown code fences from LLM JSON output (shared pattern from both prototypes).

Write **failing tests first** in `tests/test_entity_shutdown.py`:
- `parse_extracted_memories` correctly parses a valid JSON array of memories
- `parse_extracted_memories` handles missing optional fields (adds defaults)
- `parse_extracted_memories` rejects invalid JSON gracefully (returns empty list or raises)
- `parse_extracted_memories` rejects memories with invalid category/valence
- `format_consolidation_prompt` includes all three memory sets in the output string
- `parse_consolidation_response` correctly parses a valid consolidation result
- `strip_code_fences` strips `\`\`\`json ... \`\`\`` and bare `\`\`\` ... \`\`\``

Location: `src/entity_shutdown.py`, `tests/test_entity_shutdown.py`

### Step 2: Implement the shutdown orchestration function

Add to `src/entity_shutdown.py`:

- `run_consolidation(entity_name: str, extracted_memories_json: str, project_dir: Path, api_key: str | None = None) -> dict` — The main entry point for the CLI command:
  1. Parse extracted memories via `parse_extracted_memories`
  2. Write each new journal memory to `.entities/<name>/memories/journal/` via `Entities.write_memory`
  3. Load existing consolidated and core memories from disk via `Entities.list_memories` and `Entities.parse_memory`
  4. If no existing consolidated/core memories AND fewer than 3 new journals, skip consolidation (just store journals)
  5. Format the incremental consolidation prompt
  6. Call the Anthropic API with the prompt (using `anthropic.Anthropic(api_key=...)`)
  7. Parse the consolidation response
  8. **Clear and rewrite** consolidated and core tier directories with the updated memories. This is a full replacement, not an append — the LLM returns the complete updated tier structure.
  9. For `unconsolidated` titles in the response, leave the matching journal memories in place (they were already written in step 2). Journal memories whose titles appear in `consolidated` or `core` source_memories can be left as-is — they're the raw record.
  10. Return a summary dict: `{"journals_added": N, "consolidated": M, "core": K}`

Write **failing tests first** (mocking the Anthropic API):
- `run_consolidation` writes journal memories to the correct directory
- `run_consolidation` calls the API with a properly formatted prompt
- `run_consolidation` writes consolidated and core memories from the API response
- `run_consolidation` skips API call when too few memories and no existing tiers
- `run_consolidation` preserves existing core memories that the LLM doesn't remove

Location: `src/entity_shutdown.py`, `tests/test_entity_shutdown.py`

### Step 3: Implement the `ve entity shutdown` CLI command

Add to `src/cli/entity.py`:

```python
@entity.command("shutdown")
@click.argument("name")
@click.option("--memories-file", type=click.Path(exists=True, path_type=pathlib.Path),
              help="JSON file with extracted memories (alternative to stdin)")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def shutdown(name, memories_file, project_dir):
    """Run the sleep cycle: consolidate extracted memories for an entity.

    Reads extracted journal memories (JSON array) from --memories-file or stdin,
    then runs incremental consolidation against the entity's existing memory tiers.
    """
```

The command:
1. Validates the entity exists
2. Reads extracted memories JSON from `--memories-file` or stdin
3. Calls `run_consolidation()`
4. Prints a summary of what was consolidated

Write **failing tests first** in `tests/test_entity_cli.py` (or `tests/test_entity_shutdown_cli.py`):
- `ve entity shutdown myentity --memories-file memories.json` runs successfully with mock API
- `ve entity shutdown nonexistent` fails with "entity not found"
- `ve entity shutdown myentity` with empty stdin produces appropriate error
- Exit code 0 on success, non-zero on error

Location: `src/cli/entity.py`, `tests/test_entity_shutdown_cli.py`

### Step 4: Create the `/entity-shutdown` slash command template

Create `src/templates/commands/entity-shutdown.md.jinja2`:

This slash command instructs the agent to perform the extraction step (reflecting on its own session) and then invoke the CLI for consolidation. The template structure:

```
---
description: Run the sleep cycle for an entity — extract memories and consolidate
---
{% set source_template = "entity-shutdown.md.jinja2" %}
{% include "partials/auto-generated-header.md.jinja2" %}

## Tips

{% include "partials/common-tips.md.jinja2" %}

## Instructions

<extraction prompt adapted from EXTRACTION_PROMPT>

1. Ask the operator which entity to shut down (or accept as argument)
2. Review your conversation in this session
3. Extract memory-worthy events using the categories and format below
4. Write the memories as a JSON array to a temp file
5. Run `ve entity shutdown <name> --memories-file <temp_file>`
6. Report the consolidation summary to the operator
```

The extraction prompt section includes the full EXTRACTION_PROMPT constant (adapted from the prototype) directly in the command template, so the agent has the instructions in-context when reflecting.

Location: `src/templates/commands/entity-shutdown.md.jinja2`

### Step 5: Render the template and register the skill

Run `uv run ve init` to render the new command template to `.claude/commands/entity-shutdown.md`.

Verify:
- The rendered file exists at `.claude/commands/entity-shutdown.md`
- The skill appears in Claude's available commands
- The auto-generated header is present

Add the `/entity-shutdown` skill to the project's CLAUDE.md skill listing (via the source template if managed, or note that `ve init` handles it).

Location: `.claude/commands/entity-shutdown.md` (rendered, not manually created)

### Step 6: End-to-end integration test with example data

Create a test that exercises the full pipeline with realistic data:

1. Create an entity with `Entities.create_entity`
2. Write some pre-existing tier-1 and tier-2 memories (simulating a prior shutdown cycle)
3. Prepare a JSON array of new extracted memories (based on the investigation prototype's example output format)
4. Mock the Anthropic API to return a realistic consolidation response
5. Run `run_consolidation()`
6. Verify:
   - New journal memories exist in `memories/journal/`
   - Consolidated memories were updated (not just appended)
   - Core memories were refined (existing core memory with updated content, not a duplicate)
   - `last_reinforced` timestamps are current
   - The memory count is reasonable (not 1:1 with input)

This test validates the success criterion: "Running the skill against a real session produces comparable quality to the investigation prototype."

Location: `tests/test_entity_shutdown.py`

### Step 7: Update GOAL.md code_paths

Update the chunk's `code_paths` frontmatter to list all files created or modified:
- `src/entity_shutdown.py`
- `src/cli/entity.py`
- `src/templates/commands/entity-shutdown.md.jinja2`
- `tests/test_entity_shutdown.py`
- `tests/test_entity_shutdown_cli.py`

Backreference comments should be added to:
- `src/entity_shutdown.py` (module-level): `# Chunk: docs/chunks/entity_shutdown_skill`
- `src/cli/entity.py` (at the shutdown command): `# Chunk: docs/chunks/entity_shutdown_skill`

## Dependencies

- **entity_memory_schema** (ACTIVE): Provides `Entities` class, `MemoryFrontmatter` model, `MemoryTier` enum, `write_memory`/`parse_memory`/`list_memories`/`memory_index` methods. All memory read/write operations use this foundation.
- **anthropic** Python package: Required for the consolidation API call. Check if already in project dependencies; if not, add to `pyproject.toml`.

## Risks and Open Questions

- **Anthropic API availability in tests**: All consolidation tests must mock the API. The `anthropic` package may not be a current dependency — verify and add if needed.
- **Extracted memory format agreement**: The slash command instructs the agent to output a specific JSON format. If the agent produces slightly different JSON (e.g., extra fields, different casing), `parse_extracted_memories` must be tolerant. Use Pydantic's `model_validate` with `extra="ignore"` mode.
- **Consolidation replaces entire tiers**: The incremental consolidation returns the complete updated tier structure. This means we clear and rewrite consolidated/core directories. If the API call fails mid-write, we could lose existing memories. Mitigation: write new files first, then delete old ones (or write to temp dir and swap).
- **Large memory sets**: If an entity accumulates many memories over months, the consolidation prompt could exceed context limits. The investigation's design targets ~15 core + ~50 consolidated, which fits easily. For now, no chunking needed, but document the limit.
- **stdin vs file for memory input**: The CLI accepts memories via `--memories-file` or stdin. Stdin is convenient for piping from the slash command but may be tricky in some environments. Ensure both paths are tested.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->