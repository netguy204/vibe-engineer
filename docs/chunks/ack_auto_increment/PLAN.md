

# Implementation Plan

## Approach

The `ve board ack` command currently requires an explicit `<position>` argument.
This is fragile — callers must track cursor state and compute the next position,
which invites arithmetic errors and race conditions.

The change makes `position` optional in the CLI. When omitted, ack reads the
current cursor via `load_cursor()` and writes `cursor + 1`. When provided, the
old behavior is preserved with a deprecation warning to stderr. This is a
backward-compatible change: existing callers that pass a position continue to
work during the rollout period.

The storage layer (`save_cursor` / `load_cursor`) is unchanged — all the logic
lives in the CLI command handler. A new helper `ack_and_advance()` in
`src/board/storage.py` encapsulates the read-increment-write pattern so it can
be reused if needed outside the CLI.

Skill templates (`steward-watch`, `steward-changelog`) are updated to use the
simpler no-position form, removing the cursor-tracking ceremony from Step 2 and
simplifying Step 5. The `swarm-monitor` template uses `watch-multi` with
auto-ack, so it doesn't need changes.

Tests follow TDD per docs/trunk/TESTING_PHILOSOPHY.md: write failing tests for
the new no-position behavior and deprecation warning first, then implement.

## Sequence

### Step 1: Write failing tests for auto-increment ack

Location: `tests/test_board_cli.py`

Add tests before any implementation:

1. **`test_ack_auto_increment`** — Invoke `ve board ack my-channel` (no
   position) with a cursor file pre-set to 5. Assert exit code 0, output
   contains "6", and `load_cursor()` returns 6.

2. **`test_ack_auto_increment_from_zero`** — Invoke with no existing cursor
   file. Assert cursor advances from 0 to 1.

3. **`test_ack_with_position_deprecation_warning`** — Invoke `ve board ack
   my-channel 42` (explicit position). Assert exit code 0, cursor is 42, and
   stderr contains a deprecation warning mentioning the no-position form.

4. **`test_ack_existing_test_still_passes`** — Verify the existing
   `test_ack_command` still passes (this is implicit but worth confirming
   after the argument becomes optional).

Run `uv run pytest tests/test_board_cli.py -k ack` to confirm the new tests
fail.

### Step 2: Add `ack_and_advance` helper to storage module

Location: `src/board/storage.py`

Add a new function:

```python
def ack_and_advance(channel: str, project_root: Path) -> int:
    """Read the current cursor and advance it by 1.

    Returns the new cursor position.
    """
    current = load_cursor(channel, project_root)
    new_position = current + 1
    save_cursor(channel, new_position, project_root)
    return new_position
```

This is a thin composition of existing `load_cursor` and `save_cursor`. It
keeps the atomic read-increment-write in one place.

### Step 3: Update the CLI `ack` command

Location: `src/cli/board.py`

Change the `ack_cmd` function:

1. Make `position` an optional argument (default `None`):
   ```python
   @click.argument("position", type=int, required=False, default=None)
   ```

2. When `position is None`: call `ack_and_advance(channel, project_root)` and
   echo the new position.

3. When `position` is provided: emit a deprecation warning to stderr
   (`click.echo(..., err=True)`), then call `save_cursor()` as before.

Add a backreference comment:
```python
# Chunk: docs/chunks/ack_auto_increment - Auto-increment cursor on ack
```

### Step 4: Run tests and verify

Run `uv run pytest tests/test_board_cli.py -k ack` to confirm:
- All new tests pass
- The existing `test_ack_command` still passes (backward compat)

Run the full test suite `uv run pytest tests/` to check for regressions.

### Step 5: Update steward-watch skill template

Location: `src/templates/commands/steward-watch.md.jinja2`

**Step 2 (Start the watch):** Remove the cursor-reading ceremony. The agent no
longer needs to note the cursor position before watching, because ack handles
it automatically. Remove the `cat .ve/board/cursors/<channel>.cursor` example
and the "note the current cursor position" instructions. Keep the single-watch
constraint and TaskStop instructions.

**Step 5 (Ack to advance cursor):** Simplify to:
```
ve board ack <channel>
```
Remove the reference to "N+1" and "cursor position you noted in Step 2."
Keep the critical notes about not acking before processing is complete, and
about acking every message.

**Key Concepts section:** Update the cursor management bullet to reflect that
ack auto-increments — callers no longer compute the position.

### Step 6: Update steward-changelog skill template

Location: `src/templates/commands/steward-changelog.md.jinja2`

In the "Ack and optionally continue" section: change `ve board ack
<changelog_channel> <position>` to `ve board ack <changelog_channel>`. Remove
the instruction about reading the cursor file before watching to determine
the position.

### Step 7: Re-render templates and verify

Run `uv run ve init` to re-render all templates from the updated Jinja2
sources. Verify that the rendered `.claude/commands/steward-watch.md` and
`.claude/commands/steward-changelog.md` reflect the simplified ack commands.

### Step 8: Update code_paths in GOAL.md frontmatter

Location: `docs/chunks/ack_auto_increment/GOAL.md`

Set `code_paths` to:
```yaml
code_paths:
- src/cli/board.py
- src/board/storage.py
- src/templates/commands/steward-watch.md.jinja2
- src/templates/commands/steward-changelog.md.jinja2
- tests/test_board_cli.py
```

### Step 9: Final validation

Run the full test suite: `uv run pytest tests/`

Manually verify the CLI works:
- `uv run ve board ack --help` shows position as optional
- The rendered command files no longer reference the position argument

## Risks and Open Questions

- **Concurrent ack calls**: If two agents ack the same channel simultaneously,
  the read-increment-write in `ack_and_advance` is not atomic at the filesystem
  level. This is acceptable because the steward design enforces single-consumer
  per channel (one watch at a time). No mitigation needed.

- **Deprecation warning visibility**: Stderr warnings may be lost in agent
  contexts where only stdout is captured. This is acceptable — the warning is
  for human operators during the transition period, and the old behavior
  continues to work correctly.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->