---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/entity.py
- src/entity_repo.py
- tests/test_entity_push_pull_cli.py
- tests/test_entity_fork_merge_cli.py
- tests/test_entity_repo.py
code_references:
- ref: src/entity_repo.py#is_merge_in_progress
  implements: "Detects whether a git merge is already in progress in an entity worktree"
- ref: src/entity_repo.py#apply_resolutions
  implements: "Stages auto-resolved conflict files without committing, leaving unresolvable files in conflict state"
- ref: src/entity_repo.py#abort_merge
  implements: "Explicit abort escape hatch, now only invoked via --abort flag rather than silently on unresolvable conflicts"
- ref: src/cli/entity.py#pull
  implements: "Pull command with merge-in-progress guard, three resolver-outcome branches, and no auto-abort on unresolvable conflicts"
- ref: src/cli/entity.py#merge
  implements: "Merge command with --abort flag, merge-in-progress guard, and coherent handling of all three resolver outcomes"
- ref: tests/test_entity_repo.py#TestIsMergeInProgress
  implements: "Unit tests for merge-in-progress detection"
- ref: tests/test_entity_repo.py#TestApplyResolutions
  implements: "Unit tests for staging resolved conflicts without touching unresolvable files"
- ref: tests/test_entity_push_pull_cli.py#TestPullConflictResolution
  implements: "CLI tests for all three resolver-outcome branches and merge-in-progress detection on pull"
- ref: tests/test_entity_fork_merge_cli.py
  implements: "CLI tests for zero/mixed/all-resolved branches, merge-in-progress detection, and --abort flag on merge"
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- entity_sync_ergonomics
---

# Chunk Goal

## Minor Goal

When `ve entity pull` or `ve entity merge` produces conflicts that the
wiki-conflict resolver cannot synthesize a resolution for, the
in-progress merge state in the entity worktree is preserved. The
operator finds the affected files marked with standard
`<<<<<<<`/`=======`/`>>>>>>>` conflict markers, edits them in their
editor, runs `git add` + `git commit` from inside the entity directory,
and the merge completes — the same workflow `git merge` users already
know.

The CLI distinguishes three resolver outcomes and acts coherently on
each:

1. All conflicts auto-resolved → present resolutions for approval, then
   commit.
2. Some auto-resolved, some unresolvable → apply the resolutions to the
   index, leave the unresolvable files in conflict state with markers,
   and tell the operator which files need manual editing and how to
   finish.
3. No conflicts auto-resolved (resolver returned zero resolutions) →
   leave every conflicted file in conflict state with markers, tell the
   operator to resolve manually and commit.

In none of these cases does the CLI run `git merge --abort`. The merge
state is the operator's recovery surface; aborting it without operator
consent is an unforced data-loss event, since it discards the very
markers the operator is being told to "resolve manually."

The message "Resolve unresolvable conflicts manually and commit" is
always matched by an entity worktree that actually contains those
conflicts.

## Success Criteria

- `ve entity pull` and `ve entity merge` never call `abort_merge` on
  the unresolvable-conflicts path. The merge state (`.git/MERGE_HEAD`,
  conflict markers in working files, conflicted entries in the index)
  is preserved for the operator.
- When the resolver returns zero resolutions but reports unresolvable
  conflicts, the operator sees a message that names the affected files,
  shows the standard "edit, `git add`, `git commit`" recovery, and
  exits non-zero so scripts can detect the pause.
- When the resolver returns a mix of resolutions and unresolvable
  conflicts and the operator approves the resolutions, those
  resolutions land in the index. Unresolvable files stay in conflict
  state. The same recovery message points the operator at the remaining
  files. The operator can complete the merge with `git add` + `git
  commit` without re-running `ve entity pull`.
- Re-running `ve entity pull` while a merge is in progress is detected
  and surfaces a clear message ("merge in progress; resolve files X, Y
  and commit, or run `ve entity merge --abort` to discard"), instead of
  silently re-driving the resolver.
- An explicit `ve entity merge --abort` command exists for the operator
  to opt into discarding the in-progress merge — an intentional escape
  hatch, not an automatic behavior.
- Tests cover all three resolver-outcome branches plus the
  merge-already-in-progress detection.

## Out of Scope

- Changing the wiki-conflict resolver's prompt, model, or
  resolution-quality heuristics.
- Auto-resolving the four file types that triggered this report
  (memory snapshot dirs, wiki log, wiki project pages) — the resolver's
  job is what it is; this chunk owns the recovery surface when the
  resolver legitimately can't help.
- New entity-sync primitives.