---
status: ACTIVE
ticket: null
parent_chunk: watchmulti_exit_on_message
code_paths:
- src/board/client.py
- src/cli/board.py
- tests/test_board_client.py
- tests/test_board_cli.py
code_references:
- ref: src/board/client.py#BoardClient::watch_multi
  implements: "auto_ack parameter that skips cursor re-send when False"
- ref: src/board/client.py#BoardClient::watch_multi_with_reconnect
  implements: "auto_ack pass-through to inner watch_multi"
- ref: src/cli/board.py#watch_multi_cmd
  implements: "--no-auto-ack CLI flag, position output format, save_cursor skip"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- websocket_zombie_cleanup
---
# Chunk Goal

## Minor Goal

A `--no-auto-ack` flag on `ve board watch-multi` delivers messages without advancing the cursor. The consumer is responsible for calling `ve board ack` after completing side effects, giving at-least-once processing guarantees.

By default, watch-multi auto-advances cursors after each delivered message. This is correct for the swarm-monitor use case (display only, no durability needed), but insufficient for distributed orchestration where messages trigger durable side effects — if the agent crashes between receiving a message and completing the action, auto-ack would lose the message. The `--no-auto-ack` flag opts into manual ack semantics for those workflows.

Behavior:
- **CLI**: `--no-auto-ack` flag on `ve board watch-multi` (default: auto-ack for backward compatibility)
- **Output**: When `--no-auto-ack` is set, the message position is included in output so the consumer knows what to ack
- **Client**: `watch_multi` method accepts an `auto_ack=True` parameter; when False, cursor advancement after delivery is skipped

Use cases:
1. Swarm monitor (current): auto-ack, no durability needed
2. Distributed orchestration (future): manual ack after side effects are durable, resilient to agent failure

## Success Criteria

- `ve board watch-multi --no-auto-ack ch1 ch2` delivers messages with position but doesn't advance cursor
- After crash and restart, unacked messages re-deliver
- Default behavior (auto-ack) unchanged
- Output includes position field when `--no-auto-ack` is set

## Relationship to Parent

Parent chunk `watchmulti_exit_on_message` introduced `--count` for event-driven workflows. `--no-auto-ack` covers durable processing workflows — a different axis of configurability on the same command.