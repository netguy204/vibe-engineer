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

Make `ve board ack <channel>` auto-increment the cursor by 1 instead of requiring an explicit position argument. Since messages are delivered one at a time, the ack always means "I processed the most recently delivered message" — the position is implicit.

The current design where callers pass an explicit position is fragile: any arithmetic error or race condition between ack and message delivery silently skips messages. Auto-increment makes cursor advancement and message delivery lockstep — you can't skip ahead.

### CLI changes

- `ve board ack <channel>` (no position) — reads cursor file, writes cursor+1. This is the new default.
- `ve board ack <channel> <position>` — still works for backward compatibility during rollout. Existing callers that pass a position will continue to function. Emit a deprecation warning suggesting the no-position form.

### Skill/template changes

Update all steward skill templates that reference `ve board ack` to use the new no-position form:

- `src/templates/commands/steward-watch.md.jinja2` — Step 5 (ack step): remove position tracking from Step 2, simplify Step 5 to just `ve board ack <channel>`
- `src/templates/commands/steward-setup.md.jinja2` — if ack is mentioned in the suggested behavior section
- Any other templates referencing `ve board ack`

### Why backward compat matters

The operator has multiple projects with steward configurations and rendered CLAUDE.md files that reference `ve board ack <channel> <position>`. These won't all be re-rendered immediately. The position argument must keep working (with a deprecation warning) until the rollout is complete.

## Success Criteria

- `ve board ack my-channel` increments cursor from N to N+1 (no position arg)
- `ve board ack my-channel 5` still works but emits deprecation warning
- Steward-watch skill template updated to remove position tracking
- `ve init` renders updated templates
- All existing tests pass, new tests cover no-position form