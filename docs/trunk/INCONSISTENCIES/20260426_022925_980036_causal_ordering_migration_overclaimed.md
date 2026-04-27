---
discovered_by: audit batch 10h
discovered_at: 2026-04-26T02:29:25Z
severity: medium
status: open
artifacts:
  - docs/chunks/causal_ordering_migration/GOAL.md
---

# Claim

`docs/chunks/causal_ordering_migration/GOAL.md` declares the following in its
frontmatter:

```
code_paths:
- docs/chunks/0042-causal_ordering_migration/migrate.py
- tests/test_migration_utilities.py
code_references:
- ref: docs/chunks/0042-causal_ordering_migration/migrate.py#extract_short_name
  ...
- ref: tests/test_migration_utilities.py
  implements: Unit tests for migration script utilities
```

The chunk is in ACTIVE status, asserting that all listed code paths and
references implement the chunk's intent.

# Reality

Two distinct mismatches:

1. **Stale directory prefix.** The migration script lives at
   `docs/chunks/causal_ordering_migration/migrate.py`, not
   `docs/chunks/0042-causal_ordering_migration/migrate.py`. The numeric
   prefix scheme was abandoned (chunks are now named by initiative, not
   sequence). Every `code_paths` and `code_references` entry that uses the
   `0042-` prefix is broken. Verified via `ls`:

   ```
   ls docs/chunks/causal_ordering_migration/
   GOAL.md  PLAN.md  __pycache__  migrate.py
   ```

2. **Missing test file.** `tests/test_migration_utilities.py` does not
   exist. The chunk's `code_references` claim it implements "Unit tests
   for migration script utilities," but no such file is present in the
   `tests/` directory. Verified via `ls`:

   ```
   ls tests/test_migration_utilities.py
   No such file or directory
   ```

   Without this file, success criterion #5 ("ArtifactIndex validates
   result") and the implicit promise of testing coverage have no
   verifying tests checked into the repository.

# Workaround

None applied this session — the chunk's prose was not rewritten because
the missing test file constitutes undeclared over-claim, which fires the
audit's veto rule against tense rewrites.

# Fix paths

1. **Preferred:** Update `code_paths` and `code_references` to drop the
   `0042-` prefix on every entry, AND either add the missing
   `tests/test_migration_utilities.py` file or remove the reference to
   it (if the migration was a one-time script with no surviving test
   coverage). A follow-up chunk should make this metadata correction
   and decide whether the test file ever existed or was aspirational.
2. **Alternative:** Mark the chunk HISTORICAL — the migration was a
   one-time operation against a single repo, the script is preserved
   in-place, and the chunk's enduring intent is essentially captured.
   This would side-step the metadata cleanup but loses the audit trail.
