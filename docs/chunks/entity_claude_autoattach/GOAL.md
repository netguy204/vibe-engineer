---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/entity_claude.py
- src/cli/entity_worktree.py
- src/cli/entity.py
- tests/test_entity_claude_autoattach.py
code_references:
- ref: src/cli/entity_claude.py#prepare_session_environment
  implements: 'Auto-attach prelude: composes is_attached fast-path check, two-line
    progress output for cold-start, and delegation to do_attach. Idempotent.'
- ref: src/cli/entity_worktree.py#is_attached
  implements: Public predicate used by the auto-attach pathway to silent-fast-path
    when the entity is already a worktree of its canonical clone.
- ref: src/cli/entity.py#claude_cmd
  implements: Wires prepare_session_environment into the entity claude command lifecycle
    BEFORE the Claude session launch, translating each typed exception into a distinct
    click.ClickException so failures never reach a half-set-up session.
- ref: tests/test_entity_claude_autoattach.py
  implements: 'Coverage for: is_attached predicate edge cases, silent fast path, cold-start
    progress lines, legacy plain-directory bypass, each clone-failure class propagating,
    end-to-end fresh-machine path, and all five CLI failure surfaces aborting before
    Popen.'
narrative: entity_worktrees
investigation: null
subsystems: []
friction_entries: []
depends_on:
- entity_config_toml
- entity_canonical_clone
- entity_worktree_attach
created_after:
- plugin_hook_cli_bootstrap
---
# Chunk Goal

## Minor Goal

`ve entity claude <name>` auto-attaches the named entity to the current
project when it is not already attached, then opens the Claude session.
The composition is: check whether `.entities/<name>` is an attached
worktree; if not, invoke the worktree-based attach (which itself
composes the canonical-clone helper to clone if absent); then proceed
to the entity-claude session launch. The user experience is a single
command from a fresh checkout on a fresh machine — provided
`~/.ve-config.toml` is set up — to a working Claude session against
the entity.

This is the 1.0 headline capability. An organization writes
`~/.ve-config.toml` (e.g. via an org-wide profile script). A new
employee runs `ve entity claude <some-shared-entity>` in any project,
and the command auto-clones the entity into `entities_dir/<name>`
(producing user-visible progress output so the wait is comprehensible),
attaches it as a worktree at `.entities/<name>`, and launches the Claude
session with the entity's full identity, memories, and wiki immediately
available.

When the entity is already attached, the command short-circuits the
clone-and-attach steps and goes straight to the session launch, so
day-to-day usage has no overhead.

## Success Criteria

- `ve entity claude <name>` against an entity that is already attached
  incurs no clone or attach work — straight to the Claude session —
  verified by absence of git operations during the run.
- `ve entity claude <name>` against an entity not attached but whose
  canonical clone exists in `entities_dir/<name>` performs only the
  worktree-attach step before launching the session.
- `ve entity claude <name>` against an entity neither attached nor
  cloned performs canonical-clone then worktree-attach then launches the
  session, in a single command invocation.
- During the auto-clone path, the user sees informative progress output:
  at minimum, one line announcing the clone with the resolved URL and
  destination, and one line announcing the worktree attach. Silent
  multi-second waits are unacceptable for the 1.0 demo.
- Auto-clone failures (auth, missing repo, network) surface with the
  same distinguishable error classes the canonical-clone helper
  produces, and do not attempt to launch the Claude session against a
  half-set-up entity.
- The end-to-end demo path works on a fresh machine with no
  `entities_dir` directory pre-existing, given a valid
  `~/.ve-config.toml`.
- Tests cover: already-attached short-circuit, attached-but-not-cloned
  (artificial state; cover for completeness), neither-attached-nor-cloned
  end-to-end path, and each failure class surfaces without launching the
  session.

## Notes for Planning

- This is `proposed_chunks[3]` of the `entity_worktrees` narrative —
  the validation milestone for the 1.0 release.
- Depends on `entity_config_toml`, `entity_canonical_clone`, and
  `entity_worktree_attach`.
- Output during auto-clone is a UX detail with real demo impact — the
  operator chose this end-to-end command as the highest-priority outcome
  to validate, so its first impression matters. Keep the progress lines
  terse and informative.
