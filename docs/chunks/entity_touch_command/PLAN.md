

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Build the `ve entity touch <entity_name> <memory_id> [reason]` CLI command following the established patterns from `entity_memory_schema`: Click command in `src/cli/entity.py`, domain logic in `src/entities.py`, with a model for touch events in `src/models/entity.py`.

The touch command does two things:
1. **Updates `last_reinforced`** on the target memory file via the existing `Entities.update_memory_field()` method
2. **Appends a touch event** to `.entities/<name>/touch_log.jsonl` — a JSONL file where each line is a JSON object with `timestamp`, `memory_id`, `memory_title`, and optional `reason`

This follows the investigation's H6 prototype format (see `docs/investigations/agent_memory_consolidation/prototypes/touch_log.jsonl`). The touch log is a session-level append-only file that the shutdown skill reads to identify which memories were actively used.

Memory lookup strategy: The command accepts a `memory_id` which is the filename stem (without `.md`) of the memory file. Since touch is primarily for core memories (tier 2), we search core first, then consolidated, then journal. This keeps the common case fast. The `Entities` class gets a new `find_memory()` method that resolves a memory_id to its file path.

Testing follows TDD per `docs/trunk/TESTING_PHILOSOPHY.md`:
- Unit tests for `Entities.touch_memory()` and `Entities.find_memory()` in `tests/test_entities.py`
- CLI integration tests for `ve entity touch` in `tests/test_entity_cli.py`
- Tests cover: happy path, missing entity, missing memory, touch log creation, reason omission

Per DEC-001, all functionality is accessible via the CLI. Per DEC-008, the touch event model uses Pydantic.

## Sequence

### Step 1: Add TouchEvent model

Add a `TouchEvent` Pydantic model to `src/models/entity.py` with fields:
- `timestamp`: `datetime` — when the touch occurred
- `memory_id`: `str` — filename stem of the touched memory
- `memory_title`: `str` — title from the memory's frontmatter (for human readability in the log)
- `reason`: `str | None` — optional reason the memory was useful

This model handles serialization to JSON for the JSONL touch log.

Location: `src/models/entity.py`

### Step 2: Write failing tests for find_memory

Write tests in `tests/test_entities.py` for a new `Entities.find_memory()` method:
- Finds a core memory by filename stem
- Finds a consolidated memory by filename stem
- Finds a journal memory by filename stem
- Returns `None` for a nonexistent memory_id
- Searches core tier first (optimization for the common case)

Location: `tests/test_entities.py`

### Step 3: Implement find_memory

Add `Entities.find_memory(entity_name: str, memory_id: str) -> Path | None` to `src/entities.py`.

The method searches across all three tier directories for a file whose stem matches `memory_id`. Search order: core → consolidated → journal (core is the expected tier for touch commands). Returns the full path if found, `None` otherwise.

Location: `src/entities.py`

### Step 4: Write failing tests for touch_memory

Write tests in `tests/test_entities.py` for a new `Entities.touch_memory()` method:
- Updates `last_reinforced` on the memory file
- Appends a TouchEvent to `.entities/<name>/touch_log.jsonl`
- Creates touch_log.jsonl if it doesn't exist
- Appends to existing touch_log.jsonl
- Records reason when provided, omits when not
- Raises `ValueError` when entity doesn't exist
- Raises `ValueError` when memory_id is not found
- The touch log entry includes the memory's title (for readability)

Location: `tests/test_entities.py`

### Step 5: Implement touch_memory

Add `Entities.touch_memory(entity_name: str, memory_id: str, reason: str | None = None) -> TouchEvent` to `src/entities.py`.

Implementation:
1. Validate entity exists
2. Call `find_memory()` to locate the memory file
3. Parse the memory to get its frontmatter (for the title)
4. Update `last_reinforced` to `datetime.now(timezone.utc)` via `update_memory_field()`
5. Create a `TouchEvent` with timestamp, memory_id, memory_title, reason
6. Append the event as a JSON line to `.entities/<entity_name>/touch_log.jsonl`
7. Return the `TouchEvent`

The JSONL append is a simple file open in append mode — no locking needed since only one agent runs at a time.

Location: `src/entities.py`

### Step 6: Write failing CLI tests for ve entity touch

Write tests in `tests/test_entity_cli.py` for the `ve entity touch` command:
- Happy path: touches a core memory and echoes confirmation
- With reason: `ve entity touch mysteward <mem_id> "applying lifecycle rule"`
- Missing entity: exits non-zero with error
- Missing memory: exits non-zero with error
- Touch log file is created with correct content

Location: `tests/test_entity_cli.py`

### Step 7: Implement ve entity touch CLI command

Add a `touch` command to the entity group in `src/cli/entity.py`:

```python
@entity.command("touch")
@click.argument("name")
@click.argument("memory_id")
@click.argument("reason", required=False, default=None)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def touch(name, memory_id, reason, project_dir):
```

The command:
1. Instantiates `Entities(project_dir)`
2. Calls `entities.touch_memory(name, memory_id, reason)`
3. Echoes `"Touched '{memory_title}' (last_reinforced updated)"`
4. On `ValueError`, raises `click.ClickException`

Location: `src/cli/entity.py`

### Step 8: Add read_touch_log method

Add `Entities.read_touch_log(entity_name: str) -> list[TouchEvent]` to support the shutdown skill reading which memories were used during a session.

Write a test that creates an entity, touches multiple memories, then reads the log and verifies all events are returned in order.

Location: `src/entities.py`, `tests/test_entities.py`

### Step 9: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter `code_paths` with the files created/modified:
- `src/models/entity.py`
- `src/entities.py`
- `src/cli/entity.py`
- `tests/test_entities.py`
- `tests/test_entity_cli.py`

---

**BACKREFERENCE COMMENTS**

Add chunk backreference `# Chunk: docs/chunks/entity_touch_command` to:
- The `touch` CLI command in `src/cli/entity.py`
- The `touch_memory`, `find_memory`, and `read_touch_log` methods in `src/entities.py`
- The `TouchEvent` model in `src/models/entity.py`

## Dependencies

- **entity_memory_schema** (ACTIVE): Provides `Entities` class, `MemoryFrontmatter` model, `update_memory_field()`, memory directory structure, and CLI command group. All of these are used directly.
- No new external libraries required — uses `json` stdlib for JSONL, existing `pydantic` for the model.

## Risks and Open Questions

- **Memory ID ambiguity**: Memory filenames are auto-generated as `{timestamp}_{slug}.md`, which makes them long and hard to type. The touch command uses the full filename stem. In practice, agents will copy-paste from the startup memory index. If this proves unwieldy, a future chunk could add short aliases or sequential IDs — but that's out of scope here.
- **Touch log growth**: The touch log is append-only within a session. The shutdown skill is responsible for reading and clearing it. If no shutdown skill runs, the log grows indefinitely. This is acceptable for the MVP — the file is tiny (one JSON line per touch).
- **Concurrent touches**: No file locking on the JSONL append. This is safe because only one agent process writes at a time per the entity model. If concurrent agents ever share an entity, this would need revisiting.
- **Performance**: The < 100ms target should be easily met — the operation is one frontmatter field update + one JSONL line append, both against local filesystem.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->