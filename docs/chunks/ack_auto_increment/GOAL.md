---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/board.py
- src/board/storage.py
- src/templates/commands/steward-watch.md.jinja2
- src/templates/commands/steward-changelog.md.jinja2
- tests/test_board_cli.py
code_references:
- ref: src/board/storage.py#ack_and_advance
  implements: "Read-increment-write cursor advancement helper"
- ref: src/cli/board.py#ack_cmd
  implements: "CLI command with optional position arg, auto-increment default, and deprecation warning"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- watchmulti_manual_ack
---

# Chunk Goal

## Minor Goal

`ve board ack <channel>` auto-increments the cursor by 1 instead of requiring an explicit position argument. Since messages are delivered one at a time, the ack always means "I processed the most recently delivered message" — the position is implicit.

A design that requires callers to pass an explicit position is fragile: any arithmetic error or race condition between ack and message delivery silently skips messages. Auto-increment keeps cursor advancement and message delivery lockstep — callers can't skip ahead.

### CLI behavior

- `ve board ack <channel>` (no position) — reads cursor file, writes cursor+1. This is the default.
- `ve board ack <channel> <position>` — works for backward compatibility during rollout. Callers that pass a position continue to function and receive a deprecation warning suggesting the no-position form.

### Skill/template surface

Steward skill templates that reference `ve board ack` use the no-position form:

- `src/templates/commands/steward-watch.md.jinja2` — Step 5 (ack step) calls `ve board ack <channel>` with no position tracking in Step 2
- `src/templates/commands/steward-setup.md.jinja2` — ack mentions in the suggested behavior section use the no-position form
- Other templates referencing `ve board ack` use the no-position form

### Why backward compat matters

The operator has multiple projects with steward configurations and rendered CLAUDE.md files that reference `ve board ack <channel> <position>`. These won't all be re-rendered immediately. The position argument keeps working (with a deprecation warning) until the rollout is complete.

## Success Criteria

- `ve board ack my-channel` increments cursor from N to N+1 (no position arg)
- `ve board ack my-channel 5` still works but emits deprecation warning
- Steward-watch skill template updated to remove position tracking
- `ve init` renders updated templates
- All existing tests pass, new tests cover no-position form