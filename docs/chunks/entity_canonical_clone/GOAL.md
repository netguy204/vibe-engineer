---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/canonical_clone.py
- tests/test_entity_canonical_clone.py
code_references:
- ref: src/cli/canonical_clone.py#ensure_canonical_clone
  implements: "Idempotent helper that guarantees entities_dir/<name> is a clone of git_base/<name>.git: fast existence check on the second call, full git clone on the first, partial-clone cleanup on failure"
- ref: src/cli/canonical_clone.py#CanonicalCloneError
  implements: "Base exception carrying entity_name and clone_url so downstream callers can render consistent error messages without reconstructing the URL"
- ref: src/cli/canonical_clone.py#AuthFailure
  implements: "Distinguishable failure mode: git rejected credentials — message points the user at credentials for the clone URL's host"
- ref: src/cli/canonical_clone.py#MissingRemoteRepo
  implements: "Distinguishable failure mode: git host says repository does not exist — message names entity and full URL so a typoed name is obvious"
- ref: src/cli/canonical_clone.py#NetworkFailure
  implements: "Distinguishable failure mode: DNS / connection refused / timeout — distinct from auth and missing-repo so callers can suggest retry vs. fix-your-typo"
- ref: src/cli/canonical_clone.py#_classify_clone_error
  implements: "Pure stderr-substring classifier mapping a failed git clone's stderr to AuthFailure / MissingRemoteRepo / NetworkFailure / fallback CanonicalCloneError"
- ref: src/cli/canonical_clone.py#_validate_entity_name
  implements: "Pre-config name validation: rejects empty names, path separators, and leading dots so a tainted name can never escape entities_dir"
- ref: tests/test_entity_canonical_clone.py
  implements: "Coverage for first-time clone, idempotent re-call, entities_dir auto-creation, auth/missing-repo/network classification (SSH + HTTPS variants), fallback classification, partial-clone cleanup, clobber refusal, name validation, ConfigError propagation, and exception-hierarchy sanity"
narrative: entity_worktrees
investigation: null
subsystems: []
friction_entries: []
depends_on:
- entity_config_toml
created_after:
- plugin_hook_cli_bootstrap
---

# Chunk Goal

## Minor Goal

A single canonical-clone helper guarantees that for any entity name N,
`<entities_dir>/<N>` exists as a working git clone of `<git_base>/<N>.git`.
The helper is idempotent — a no-op when the clone is already present, a
fresh clone when it isn't — and is the single substrate every other
entity command consults for "is this entity available on disk yet."

The helper distinguishes the three real failure modes — authentication
failure (push/pull auth not configured), missing remote repository
(entity does not exist under the configured `git_base`), and network
failure — with actionable, distinguishable error messages. A user who
typo'd the entity name should see "no repository at
`{git_base}/typoed-name.git`", not a raw git error spew, so they know to
check their input rather than their auth or network.

This helper exists for both human-driven flows (a user running an
explicit attach) and machine-driven flows (`ve entity claude` doing the
auto-clone behind the scenes). Its narrow surface — "ensure
`entities_dir/N` exists as a clone, idempotently" — makes it usable from
any future prefetch, sync, or bulk-attach command without having to
reshape its interface.

## Success Criteria

- Calling the helper with an entity name N when `entities_dir/N` does
  not exist clones `git_base/N.git` into `entities_dir/N` and returns
  the path.
- Calling the helper a second time with the same name is a no-op (no
  network calls, no git invocations beyond a fast existence check) and
  returns the same path.
- Auth failures during the initial clone surface as an error that
  mentions auth and points the user at the git_base URL they tried to
  reach.
- A missing remote repository (404-equivalent from the git host) surfaces
  as an error that names the entity and the full URL that failed,
  distinguishable from auth failures.
- Network failures (DNS, connection refused, timeout) surface as a
  distinct error class from auth and missing-repo.
- The helper does not partially create `entities_dir/N`; a failed clone
  cleans up so the next invocation can retry cleanly.
- Tests cover: first-time clone, idempotent re-call, auth failure
  classification, missing-repo failure classification, network failure
  classification, partial-clone cleanup.

## Notes for Planning

- This is `proposed_chunks[1]` of the `entity_worktrees` narrative.
- Depends on `entity_config_toml` for `entities_dir` and `git_base`.
- The helper's interface should be narrow enough that future commands
  (prefetch, bulk-attach, sync-all) can reuse it without modification.