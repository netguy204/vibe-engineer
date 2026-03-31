---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/entities.py
  - src/cli/entity.py
  - src/templates/commands/entity-startup.md.jinja2
  - tests/test_entities.py
  - tests/test_entity_cli.py
code_references:
  - ref: src/entities.py#Entities::startup_payload
    implements: "Core startup/wake payload assembly — loads identity, core memories, consolidated index, touch protocol, and active state"
  - ref: src/entities.py#Entities::_read_body
    implements: "Helper to extract markdown body content after frontmatter for identity loading"
  - ref: src/entities.py#Entities::recall_memory
    implements: "On-demand memory retrieval by case-insensitive title substring search across core and consolidated tiers"
  - ref: src/cli/entity.py#startup
    implements: "CLI command 've entity startup <name>' — renders startup payload to stdout"
  - ref: src/cli/entity.py#recall
    implements: "CLI command 've entity recall <name> <query>' — retrieves memories matching a title query"
  - ref: src/templates/commands/entity-startup.md.jinja2
    implements: "/entity-startup slash command template — instructs agent to run startup CLI, adopt entity identity, internalize core memories, note consolidated index, follow touch protocol, use episodic search (Step 7), and restore active state (Step 8)"
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

Create a skill that performs the "wake" cycle for a named entity. When invoked at the start of a new session (after a context clear), it restores the entity's accumulated understanding by:

1. **Loading the entity identity** from `.entities/<name>/identity.md` — role description, responsibilities, startup instructions
2. **Loading all core memories (tier 2) in full** — these are the entity's internalized principles and skills, injected directly into context
3. **Building an index of consolidated memories (tier 1)** — titles and categories only, so the agent knows what's available for on-demand retrieval
4. **Including the touch protocol** — instructs the agent to run `ve entity touch <memory_id> <reason>` when it notices itself applying a core memory, enabling retrieval-as-reinforcement
5. **Restoring active state** — if the entity was watching channels or had pending async operations, remind it to restart those

The startup payload budget is ~4K tokens (validated by the investigation at ~2,400 tokens for 11 core + 19 consolidated index).

## Success Criteria

- Skill is invocable as `/entity-startup` or `ve entity startup <name>`
- All tier-2 memories are loaded in full into the session context
- Tier-1 memories are presented as a searchable index (title + category)
- The agent can retrieve a specific tier-1 memory by referencing its title (e.g., `ve entity recall <memory_title>`)
- Total startup payload stays under 4K tokens
- The touch protocol instruction is included in the startup context
- Entity identity is loaded and shapes the agent's behavior