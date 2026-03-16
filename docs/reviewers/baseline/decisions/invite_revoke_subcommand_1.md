---
decision: APPROVE
summary: All success criteria satisfied — revoke moved under invite group, deprecated alias emits warning, help shows all three subcommands, all 21 tests pass.
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve board invite revoke <token>` revokes a single token

- **Status**: satisfied
- **Evidence**: `@invite.command("revoke")` at src/cli/board.py:492; `test_revoke_happy_path` invokes via `["invite", "revoke", token_hex, ...]` and passes.

### Criterion 2: `ve board invite revoke --all --swarm <id>` bulk-revokes all tokens

- **Status**: satisfied
- **Evidence**: `--all` flag at src/cli/board.py:496, bulk DELETE at lines 512-523; `test_revoke_all_happy_path` invokes via `["invite", "revoke", "--all", "--swarm", ...]` and passes.

### Criterion 3: `ve board invite --help` shows `create`, `list`, and `revoke` subcommands

- **Status**: satisfied
- **Evidence**: All three commands registered on the `invite` Click group; `test_invite_help_shows_revoke` asserts all three appear in `--help` output.

### Criterion 4: Old `ve board revoke` either removed or emits a deprecation warning

- **Status**: satisfied
- **Evidence**: Deprecated alias `revoke_deprecated` at src/cli/board.py:549-558 emits warning to stderr and delegates via `ctx.invoke`; `test_deprecated_board_revoke_warns` confirms warning text and exit code 0.
