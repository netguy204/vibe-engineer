

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Two text-only fixes in two source files. No new logic, no schema changes — purely
correcting the command signature and example shown to agents during startup.

1. Fix the startup payload string in `src/entities.py`
2. Fix the skill template in `src/templates/commands/entity-startup.md.jinja2`
3. Tighten the existing test assertion to catch regressions of the correct signature
4. Re-render with `ve init` and run the test suite

No architectural decisions are introduced. This is a documentation correctness fix.

## Sequence

### Step 1: Fix the startup payload in `src/entities.py`

Location: `src/entities.py` — the Touch Protocol section of `build_startup_payload`
(currently around line 365–372).

Change the string from:

```
ve entity touch <memory_id> "<reason>"
```

to:

```
ve entity touch <name> <memory_id> "<reason>"
```

Also update the inline example so the entity name placeholder appears before the
memory ID:

Before:
```
ve entity touch 20260319_core_memory "applied this insight"
```

After:
```
ve entity touch <name> 20260319_core_memory "applied this insight"
```

Use `<name>` as a literal placeholder consistent with the rest of the payload's
style; agents will substitute their own entity name.

### Step 2: Fix the skill template in `entity-startup.md.jinja2`

Location: `src/templates/commands/entity-startup.md.jinja2`, Step 6 block
(currently around lines 71–84).

**2a — Clarify the ID format** (line ~73, the prose before the code fence):

Replace the CM-shorthand reference ("CM1, CM2, ...") with language that points
agents to the full filename stem shown in the `ID:` field of the startup payload.

Before:
```
When you notice yourself applying a core memory (CM1, CM2, ...), run:
```

After:
```
When you notice yourself applying a core memory, run the touch command
using the full ID stem shown next to each memory (the `ID:` field in the
startup payload above):
```

**2b — Fix the command signature** (line ~76, the code fence):

Before:
```
ve entity touch <memory_id> <reason>
```

After:
```
ve entity touch <name> <memory_id> <reason>
```

**2c — Fix the example** (line ~83, the example code fence):

Before:
```
ve entity touch CM3 "Used template editing workflow to fix rendering issue"
```

After (use a realistic full stem and include the entity name):
```
ve entity touch aria 20260414_120742_089450_template_editing_workflow "Used template editing workflow to fix rendering issue"
```

### Step 3: Strengthen the existing test

Location: `tests/test_entities.py`, `test_startup_payload_includes_touch_protocol`
(currently around line 397–401).

The test currently only checks that `"ve entity touch"` appears in the payload.
Extend it to also assert the 3-argument form is present so a future regression
of the missing `<name>` argument is immediately caught:

```python
def test_startup_payload_includes_touch_protocol(self, entities):
    """Touch Protocol shows correct 3-argument signature."""
    entities.create_entity("agent")
    payload = entities.startup_payload("agent")
    # Must include entity name argument in the command signature
    assert "ve entity touch <name> <memory_id>" in payload
```

### Step 4: Re-render templates and verify

Run `uv run ve init` to re-render `entity-startup.md.jinja2` into the installed
skill file. Confirm the rendered output contains the correct signature.

### Step 5: Run the test suite

```
uv run pytest tests/test_entities.py tests/test_entity_cli.py -v
```

All tests should pass, including the tightened assertion from Step 3.

### Step 6: Add backreference comment

Add a backreference comment to the Touch Protocol section in `src/entities.py`
so future agents can trace it back to this chunk:

```python
# Chunk: docs/chunks/entity_touch_protocol_docs - Fix Touch Protocol command signature
```

Place it immediately before the `sections.append("## Touch Protocol")` line.

## Dependencies

None. Both files are self-contained; no other chunks need to land first.

## Risks and Open Questions

- The test change in Step 3 asserts a literal substring. If the startup payload
  text is refactored (e.g., the placeholder style changes), the test will need
  updating — but that's the desired coupling: the test should fail when the
  signature regresses.
- `ve init` may require the full project environment. Use `uv run ve init` as
  instructed in CLAUDE.md.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
