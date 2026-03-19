
<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Build the entity startup ("wake") cycle as two complementary surfaces:

1. **`ve entity startup <name>` CLI command** — Renders the startup payload to stdout. This is the programmatic entry point that produces the context payload an agent needs to resume as a named entity.

2. **`/entity-startup` slash command** — A Jinja2 command template (rendered to `.claude/commands/entity-startup.md`) that instructs the agent to run the CLI command, interpret the payload, and adopt the entity's identity and memories.

The implementation builds on the foundation from `entity_memory_schema` (DEC-008, DEC-009):
- `Entities.memory_index()` already produces the core/consolidated memory dict
- `Entities.parse_identity()` already parses identity frontmatter
- `MemoryFrontmatter`, `EntityIdentity` models are defined and tested

The startup payload is a structured text document (not JSON) designed for agent consumption — human-readable sections for identity, core memories (full content), consolidated memory index (titles + categories), and the touch protocol instruction. The investigation validated this payload at ~2,400 tokens for 11 core + 19 consolidated memories, well under the 4K budget.

A `ve entity recall <memory_id>` command is also needed so agents can retrieve consolidated memories by title reference from the startup index.

Tests follow TDD per `docs/trunk/TESTING_PHILOSOPHY.md`: write failing tests for each domain method and CLI command before implementation, focusing on semantic assertions (payload contains expected sections, memories render correctly, errors handled).

## Subsystem Considerations

- **docs/subsystems/template_system**: This chunk USES the template system to render the `/entity-startup` command template and to register it with `ve init`. Follows the existing pattern: Jinja2 source in `src/templates/commands/`, rendered to `.claude/commands/`.

## Sequence

### Step 1: Add `Entities.startup_payload()` domain method

Create a method on the `Entities` class that assembles the complete startup text payload for a named entity. This is the core logic — the CLI and skill both consume it.

**Inputs:** entity name (str)
**Output:** formatted text string containing all startup sections

The method:
1. Validates the entity exists (raise `ValueError` if not)
2. Reads `identity.md` — parses frontmatter for name/role, reads the full body content (which includes Startup Instructions and any operator-written prose)
3. Calls `self.memory_index(name)` to get core memories (full) and consolidated titles
4. Assembles sections:
   - **Identity**: Entity name, role, and the full body of `identity.md`
   - **Core Memories**: Each core memory rendered with its title, category, and full content body. Numbered for touch-protocol reference (CM1, CM2, ...)
   - **Consolidated Memory Index**: A compact list of titles with categories, for on-demand retrieval via `ve entity recall`
   - **Touch Protocol**: Instruction text telling the agent to run `ve entity touch <memory_id> <reason>` when it notices itself applying a core memory
   - **Active State Reminders**: Placeholder section noting that if the entity was watching channels or had pending async operations, it should restart them

**Location:** `src/entities.py`

Write failing tests first in `tests/test_entities.py`:
- `test_startup_payload_includes_identity` — payload contains entity name and role
- `test_startup_payload_includes_identity_body` — payload contains the full body text from identity.md (startup instructions, role prose)
- `test_startup_payload_includes_core_memories` — each core memory title and content appears in output
- `test_startup_payload_core_memories_numbered` — core memories are numbered (CM1, CM2, ...)
- `test_startup_payload_includes_consolidated_index` — consolidated titles appear as an index
- `test_startup_payload_includes_touch_protocol` — text includes `ve entity touch` instruction
- `test_startup_payload_excludes_journal` — journal memories do not appear
- `test_startup_payload_empty_memories` — entity with no memories still produces valid payload with identity and protocol sections
- `test_startup_payload_nonexistent_entity` — raises ValueError

### Step 2: Add `Entities.recall_memory()` domain method

Create a method that retrieves a specific consolidated or core memory by searching for a title match (case-insensitive substring match). This supports the agent's ability to retrieve details on a consolidated memory it sees in its index.

**Inputs:** entity name (str), query (str)
**Output:** list of dicts with `{frontmatter, content, tier, memory_id}` for matching memories

The method:
1. Scans consolidated and core tier directories
2. Parses each memory file
3. Returns matches where the query is a case-insensitive substring of the title
4. Returns full frontmatter + content for each match (since the agent wants the details)

**Location:** `src/entities.py`

Write failing tests first in `tests/test_entities.py`:
- `test_recall_finds_by_exact_title` — exact title match returns the memory
- `test_recall_finds_by_substring` — partial title match works
- `test_recall_case_insensitive` — case-insensitive matching
- `test_recall_returns_content` — returned dict includes full content body
- `test_recall_no_match_returns_empty` — no match returns empty list
- `test_recall_excludes_journal` — journal memories are not searchable

### Step 3: Add `ve entity startup` CLI command

Add a `startup` subcommand to the `entity` Click group that invokes `Entities.startup_payload()` and prints the result to stdout.

```
ve entity startup <name> [--project-dir .]
```

**Behavior:**
- Calls `Entities(project_dir).startup_payload(name)`
- Prints the payload to stdout via `click.echo()`
- Exits with error if entity doesn't exist

**Location:** `src/cli/entity.py`

Write failing tests first in `tests/test_entity_cli.py`:
- `test_startup_outputs_payload` — exit code 0, output contains entity name and "Core Memories" section header
- `test_startup_nonexistent_entity_fails` — exit code != 0, error message mentions entity name
- `test_startup_with_memories` — create entity with core + consolidated memories, verify output contains memory titles

### Step 4: Add `ve entity recall` CLI command

Add a `recall` subcommand to the `entity` Click group.

```
ve entity recall <name> <query> [--project-dir .]
```

**Behavior:**
- Calls `Entities(project_dir).recall_memory(name, query)`
- For each match, prints the memory title, tier, category, and full content
- If no matches, prints "No memories matching '<query>'" and exits with code 0 (not an error — absence of match is informational)

**Location:** `src/cli/entity.py`

Write failing tests first in `tests/test_entity_cli.py`:
- `test_recall_outputs_matching_memory` — creates memory, recalls by title, output contains content
- `test_recall_no_match` — outputs "No memories matching" message
- `test_recall_nonexistent_entity_fails` — error when entity doesn't exist

### Step 5: Create `/entity-startup` command template

Create the Jinja2 template that becomes the `/entity-startup` slash command. This is the agent-facing skill that wraps the CLI.

**Location:** `src/templates/commands/entity-startup.md.jinja2`

The template instructs the agent to:

1. Accept the entity name (argument or prompt the operator)
2. Run `ve entity startup <name>` (under `uv run` if in the VE source repo)
3. Adopt the identity described in the output
4. Internalize core memories as operational principles
5. Note the consolidated memory index for on-demand recall (via `ve entity recall <name> <query>`)
6. Follow the touch protocol: when applying a core memory (CM1, CM2, ...), run `ve entity touch <memory_id> <reason>`
7. If active state reminders are present, restart watches/subscriptions

The template follows the pattern established by other command templates (frontmatter with description, auto-generated header partial, common tips partial, numbered instruction steps).

### Step 6: Register the template in `ve init` rendering

Ensure that running `ve init` renders `entity-startup.md.jinja2` to `.claude/commands/entity-startup.md`. Check how existing command templates are discovered and rendered — if the template system auto-discovers all `.jinja2` files in `src/templates/commands/`, no registration is needed. If explicit registration is required, add the entry.

**Location:** `src/template_system.py` or `src/cli/init.py` (depending on discovery mechanism)

Verify by running `uv run ve init` and checking that `.claude/commands/entity-startup.md` is rendered.

### Step 7: Verify existing tests pass and run full suite

Run `uv run pytest tests/` to ensure:
- All new tests pass
- No existing tests broken
- Startup payload stays under 4K tokens for the test fixtures

---

**BACKREFERENCE COMMENTS**

When implementing code, add backreference comments:

- Module-level on new methods in `src/entities.py`:
  `# Chunk: docs/chunks/entity_startup_skill - Entity startup/wake payload`

- Module-level on CLI additions in `src/cli/entity.py`:
  `# Chunk: docs/chunks/entity_startup_skill - Startup and recall CLI commands`

- Template-level in `entity-startup.md.jinja2`:
  `{# Chunk: docs/chunks/entity_startup_skill - Entity startup skill template #}`

## Dependencies

- **entity_memory_schema** (ACTIVE): Provides `Entities` class, `MemoryFrontmatter`, `EntityIdentity` models, `memory_index()` method, directory structure, and all memory CRUD operations. This chunk builds directly on that foundation.
- **template_system subsystem**: Used for rendering the command template. No changes needed — standard usage.

## Risks and Open Questions

- **Startup payload formatting**: The payload is a text document designed for agent consumption. The exact formatting (section headers, memory numbering, whitespace) will be refined during implementation. The key constraint is staying under ~4K tokens.
- **Memory recall search**: Substring matching on titles is simple but may return too many or too few results if titles are generic. This is acceptable for MVP — the agent sees the index and knows the exact titles.
- **Touch protocol integration**: The touch protocol instruction is text-only in this chunk. The actual `ve entity touch` command is implemented in the `entity_touch_command` chunk. The startup skill references it but doesn't implement it — the agent will see the instruction but the command may not exist yet.
- **Active state restoration**: The "active state" section is a placeholder. The entity doesn't yet have a mechanism to persist what channels it was watching or what async operations were pending. The startup skill includes the section header and instructs the agent to check, but the actual state persistence is future work.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->