<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a documentation fix chunk—no code changes are needed. We will:
1. Fix the 8 actual integrity violations found by `ve validate`
2. The "18 violations" mentioned in the original investigation has been reduced to 8 after `integrity_validate` was implemented

The violations fall into two categories:
- **Investigation reference malformation** (1 error): A chunk has `docs/investigations/task_agent_experience` instead of `task_agent_experience`
- **Malformed chunk_directory in proposed_chunks** (6 errors): The referential_integrity investigation uses full paths like `docs/chunks/integrity_validate` instead of short names like `integrity_validate`
- **External chunk frontmatter parsing** (1 error): The `xr_ve_worktrees_flag` external chunk cannot be validated because it doesn't have local GOAL.md

Note: The external chunk error is a limitation of the validation system (it tries to parse frontmatter for external chunks which don't have local GOAL.md). This is out of scope for this chunk—we'll focus on the 7 fixable documentation errors. The external chunk issue should be addressed in a separate `integrity_external_chunks` chunk.

## Subsystem Considerations

No subsystems are directly affected by this documentation fix chunk.

## Sequence

### Step 1: Fix malformed investigation reference in task_init_scaffolding

**File:** `docs/chunks/task_init_scaffolding/GOAL.md`

**Current:** `investigation: docs/investigations/task_agent_experience`
**Fixed:** `investigation: task_agent_experience`

The investigation field should use the short name (directory name only), not the full path.

### Step 2: Fix malformed chunk_directory values in referential_integrity investigation

**File:** `docs/investigations/referential_integrity/OVERVIEW.md`

Update the `proposed_chunks` frontmatter section to remove the `docs/chunks/` prefix from all `chunk_directory` values:

| Current | Fixed |
|---------|-------|
| `docs/chunks/integrity_validate` | `integrity_validate` |
| `docs/chunks/integrity_code_backrefs` | `integrity_code_backrefs` |
| `docs/chunks/integrity_proposed_chunks` | `integrity_proposed_chunks` |
| `docs/chunks/integrity_bidirectional` | `integrity_bidirectional` |
| `docs/chunks/integrity_fix_existing` | `integrity_fix_existing` |
| `docs/chunks/integrity_validate_fix_command` | `integrity_validate_fix_command` |

### Step 3: Verify fixes with ve validate

Run `ve validate` to confirm all fixable errors have been resolved. Expected remaining error:
- `xr_ve_worktrees_flag` external chunk parsing error (out of scope - requires code change to integrity validation)

### Step 4: Document external chunk limitation

Note that one error remains (`xr_ve_worktrees_flag` external chunk) which cannot be fixed by documentation edits. This is a limitation in the validation system that attempts to parse frontmatter for external chunks which don't have local GOAL.md files. This should be tracked as a follow-up issue.

## Dependencies

- **integrity_validate** (ACTIVE): The `ve validate` command must exist to verify fixes

## Risks and Open Questions

1. **External chunk validation limitation**: The `xr_ve_worktrees_flag` error cannot be fixed by documentation edits alone. The integrity validator needs to be updated to skip or handle external chunks differently. This is out of scope for this chunk.

2. **Original count mismatch**: The investigation mentioned "18 violations" but `ve validate` only shows 8 errors. This is expected—some issues were likely fixed during the development of the `integrity_validate` chunk itself, or the investigation's prototype used different validation criteria.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->