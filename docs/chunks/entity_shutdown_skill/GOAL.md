---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/entity_shutdown.py
  - src/cli/entity.py
  - src/templates/commands/entity-shutdown.md.jinja2
  - tests/test_entity_shutdown.py
  - tests/test_entity_shutdown_cli.py
code_references:
  - ref: src/entity_shutdown.py#EXTRACTION_PROMPT
    implements: "Prompt template for agent self-reflection memory extraction"
  - ref: src/entity_shutdown.py#INCREMENTAL_CONSOLIDATION_PROMPT
    implements: "Prompt template for incremental memory tier consolidation"
  - ref: src/entity_shutdown.py#strip_code_fences
    implements: "Utility to remove markdown code fences from LLM JSON output"
  - ref: src/entity_shutdown.py#parse_extracted_memories
    implements: "Parses and validates extracted journal memories from agent reflection"
  - ref: src/entity_shutdown.py#format_consolidation_prompt
    implements: "Formats consolidation prompt with existing and new memory sets"
  - ref: src/entity_shutdown.py#parse_consolidation_response
    implements: "Parses LLM consolidation response into validated tier structures"
  - ref: src/entity_shutdown.py#run_consolidation
    implements: "Main orchestration: journal write, API consolidation, tier rewrite"
  - ref: src/cli/entity.py#shutdown
    implements: "CLI entry point for ve entity shutdown command"
  - ref: src/templates/commands/entity-shutdown.md.jinja2
    implements: "Slash command template instructing agent to extract and consolidate memories"
narrative: null
investigation: agent_memory_consolidation
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_memory_schema
created_after: []
---

# Chunk Goal

## Minor Goal

Create a skill that performs the "sleep" cycle for a named entity. When invoked (manually by the operator or by a future harness), it:

1. **Extracts journal memories** from the current session — the LLM reviews its own conversation transcript and identifies memory-worthy events: corrections, skills learned, domain knowledge, confirmations, coordination patterns, and autonomy calibrations.
2. **Runs incremental consolidation** against the entity's existing memory tiers:
   - New tier-0 memories that associate with existing tier-2 → reinforce the tier-2 (refine content, bump recurrence, update `last_reinforced`)
   - New tier-0 memories that associate with existing tier-1 → merge and evaluate for promotion to tier-2
   - New tier-0 memories that associate with other new tier-0s → consolidate into new tier-1
   - Unassociated tier-0 memories → stored as-is in journal tier
3. **Writes all updated memories** to the entity's memory directory

The extraction prompt is prototyped in `docs/investigations/agent_memory_consolidation/prototypes/extract_journal.py` (the EXTRACTION_PROMPT constant). The consolidation algorithm is prototyped in `prototypes/consolidate.py`.

## Success Criteria

- Skill is invocable as `/entity-shutdown` or `ve entity shutdown <name>`
- Extraction produces lesson-framed memories (not narrative), with category, valence, salience
- Incremental consolidation correctly associates new memories with existing tiers
- Existing tier-2 memories are refined (not duplicated) when reinforced
- Memory files are written to `.entities/<name>/memories/` per the schema from `entity_memory_schema`
- Running the skill against a real session produces comparable quality to the investigation prototype (5-20 journal memories per session, appropriate tier promotion)

## Rejected Ideas

### Continuous journaling during interaction

An ongoing skill that records memories in real-time throughout the session. Rejected because the investigation showed post-hoc extraction from the full session transcript is sufficient and simpler. The shutdown moment serves as the single memory-formation event.

### API-based extraction (external model call)

Using the Anthropic API directly to extract memories. Rejected because the real deployment is the agent itself reflecting on its own session — using the agent's own context produces more accurate salience judgments than a cold external model reading a transcript.