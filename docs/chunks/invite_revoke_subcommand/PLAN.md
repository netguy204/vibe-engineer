

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Move the `revoke_cmd` function from `@board.command("revoke")` to `@invite.command("revoke")` in `src/cli/board.py`. The function body is unchanged — only the Click decorator changes. Add a deprecated alias at the old `ve board revoke` location that emits a warning and delegates to the new command.

Update all existing tests in `tests/test_board_invite.py` to invoke via `["invite", "revoke", ...]` instead of `["revoke", ...]`. Add a test verifying the deprecated alias warns and still works.

## Subsystem Considerations

No subsystems are relevant. This is a pure CLI restructuring within `src/cli/board.py`.

## Sequence

### Step 1: Write failing tests for `ve board invite revoke`

Update the revoke test section in `tests/test_board_invite.py`. Change all existing revoke tests to invoke via `["invite", "revoke", ...]` instead of `["revoke", ...]`. This includes:

- `test_revoke_happy_path` → invoke `["invite", "revoke", token_hex, ...]`
- `test_revoke_token_not_found` → invoke `["invite", "revoke", token_hex, ...]`
- `test_revoke_server_error` → invoke `["invite", "revoke", token_hex, ...]`
- `test_revoke_all_happy_path` → invoke `["invite", "revoke", "--all", ...]`
- `test_revoke_all_empty_swarm` → invoke `["invite", "revoke", "--all", ...]`
- `test_revoke_all_server_error` → invoke `["invite", "revoke", "--all", ...]`
- `test_revoke_neither_token_nor_all_errors` → invoke `["invite", "revoke", ...]`
- `test_invite_revoke_round_trip` step 2 → invoke `["invite", "revoke", token_hex, ...]`

Add a new test `test_deprecated_board_revoke_warns` that invokes via the old `["revoke", ...]` path and asserts:
- The command still works (exit code 0)
- Output contains a deprecation warning mentioning `ve board invite revoke`

Location: `tests/test_board_invite.py`

### Step 2: Write test for `ve board invite --help` showing revoke

Add `test_invite_help_shows_revoke` that runs `["invite", "--help"]` and asserts the output contains `create`, `list`, and `revoke` as subcommands.

Location: `tests/test_board_invite.py`

### Step 3: Move `revoke_cmd` from `@board.command` to `@invite.command`

In `src/cli/board.py`:

1. Change `@board.command("revoke")` to `@invite.command("revoke")`
2. Update the backreference comment to reference this chunk
3. Keep the function body identical

Location: `src/cli/board.py` lines 489-539

### Step 4: Add deprecated alias at `ve board revoke`

Add a new `@board.command("revoke")` function that:
1. Accepts the same arguments/options as the original (TOKEN, --swarm, --server, --all)
2. Emits a deprecation warning: `"Warning: 've board revoke' is deprecated. Use 've board invite revoke' instead."`
3. Delegates to `revoke_cmd` by invoking `ctx.invoke(revoke_cmd, ...)` or by calling the function directly with the same arguments
4. Mark it `hidden=True` so it doesn't appear in `ve board --help` (optional, depending on preference — keeping it visible may help users discover the migration)

Location: `src/cli/board.py`

### Step 5: Run tests and verify all pass

Run `uv run pytest tests/test_board_invite.py -v` and confirm:
- All updated revoke tests pass via the new `invite revoke` path
- The deprecated alias test passes
- The help text test passes
- All existing invite create/list tests remain green

## Dependencies

None. The parent chunk `invite_list_revoke` already restructured `invite` into a Click group and implemented the `revoke_cmd` function. This chunk only moves and aliases it.

## Risks and Open Questions

- **Deprecated alias delegation**: Click's `ctx.invoke()` may not forward all arguments cleanly when the target command has moved to a subgroup. If `ctx.invoke` is awkward, the alias can simply call `revoke_cmd.callback(...)` directly. Test will confirm.
- **Hidden vs visible alias**: The GOAL says "either removed or emits a deprecation warning." We'll keep the alias visible (not hidden) so users running `ve board --help` still see it and can discover the migration path. If the operator prefers removal, the alias can be deleted entirely.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->