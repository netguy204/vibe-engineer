---
decision: FEEDBACK
summary: "Core implementation is solid but two functional gaps: consolidated memory index omits categories, and touch protocol memory_ids are not exposed to agents"
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: Skill is invocable as `/entity-startup` or `ve entity startup <name>`

- **Status**: satisfied
- **Evidence**: Template at `src/templates/commands/entity-startup.md.jinja2` renders to `.claude/commands/entity-startup.md` via `ve init`. CLI command `ve entity startup <name>` implemented in `src/cli/entity.py:66-85`. Both confirmed working.

### Criterion 2: All tier-2 memories are loaded in full into the session context

- **Status**: satisfied
- **Evidence**: `startup_payload()` calls `memory_index()` which loads all core memories with full frontmatter + content. Each core memory rendered with CM numbering, title, category, and full body. Tests: `test_startup_payload_includes_core_memories`, `test_startup_payload_core_memories_numbered`.

### Criterion 3: Tier-1 memories are presented as a searchable index (title + category)

- **Status**: gap
- **Evidence**: The consolidated memory index only renders titles (`f"- {title}"`), not categories. The GOAL specifies "title + category" and the PLAN says "A compact list of titles with categories". The `memory_index()` method only stores `fm.title` for consolidated memories, discarding the category. Fix: include category in both `memory_index()` consolidated entries and `startup_payload()` rendering.

### Criterion 4: The agent can retrieve a specific tier-1 memory by referencing its title (e.g., `ve entity recall <memory_title>`)

- **Status**: satisfied
- **Evidence**: `recall_memory()` performs case-insensitive substring search on memory titles across core and consolidated tiers (excluding journal). CLI `ve entity recall <name> <query>` wraps it. Tests: `test_recall_finds_by_exact_title`, `test_recall_finds_by_substring`, `test_recall_case_insensitive`.

### Criterion 5: Total startup payload stays under 4K tokens

- **Status**: satisfied
- **Evidence**: Investigation validated ~2,400 tokens for 11 core + 19 consolidated memories. Payload is structured text with compact sections. No explicit token-counting test, but the design is well within budget.

### Criterion 6: The touch protocol instruction is included in the startup context

- **Status**: gap
- **Evidence**: The Touch Protocol section IS included with the instruction `ve entity touch <memory_id> <reason>`. However, the startup payload renders core memories as `CM1`, `CM2`, etc. without exposing the actual `memory_id` (filename stem) needed by the `ve entity touch` command. The `/entity-startup` template (Step 6) even shows `ve entity touch CM3 "reason"` as an example — but CM3 is not a valid memory_id. The agent has no way to map CM numbers to actual filename stems, making the touch protocol non-functional as implemented.

### Criterion 7: Entity identity is loaded and shapes the agent's behavior

- **Status**: satisfied
- **Evidence**: `startup_payload()` reads identity frontmatter (name, role) and the full body of `identity.md` (including Startup Instructions). Template Step 3 instructs the agent to adopt the identity. Tests: `test_startup_payload_includes_identity`, `test_startup_payload_includes_identity_body`.

## Feedback Items

### Issue 1: Consolidated memory index missing categories

- **Location**: `src/entities.py:337-345` (startup_payload consolidated section) and `src/entities.py:205-209` (memory_index consolidated entries)
- **Concern**: GOAL criterion 3 specifies "title + category" but only titles are rendered. The `memory_index()` method discards category for consolidated memories.
- **Suggestion**: In `memory_index()`, change consolidated entries from `fm.title` to `{"title": fm.title, "category": fm.category}`. In `startup_payload()`, render as `f"- {entry['title']} ({entry['category']})"`.
- **Severity**: functional
- **Confidence**: high

### Issue 2: Touch protocol unusable — core memory IDs not exposed

- **Location**: `src/entities.py:320-329` (core memory rendering) and `src/templates/commands/entity-startup.md.jinja2:76-83` (Step 6 example)
- **Concern**: The startup payload shows core memories as CM1, CM2, etc. but never reveals the actual filename stem (memory_id) needed by `ve entity touch`. The template example `ve entity touch CM3 "reason"` would fail at runtime. The touch protocol instruction is present but non-functional.
- **Suggestion**: Include the actual memory_id in each core memory heading or as a metadata line, e.g., `### CM1: Title\n*Category: skill | ID: 20260101_000000_verify_state*`. Also fix the template Step 6 example to show a realistic memory_id or explain the mapping.
- **Severity**: functional
- **Confidence**: high
