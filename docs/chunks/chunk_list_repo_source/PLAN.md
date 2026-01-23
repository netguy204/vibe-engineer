<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Modified the `get_current_task_chunk` function in `task_utils.py` to return a tuple of
`(chunk_name, external_artifact_repo)` instead of just `chunk_name`. This allows the CLI
to access the repository reference and format the output in the `{repo}::docs/chunks/{chunk}`
convention established elsewhere in the codebase.

The CLI handler `_list_task_chunks` in `ve.py` was updated to unpack this tuple and output
the formatted string when the `--latest` flag is used in task context.

Single-repo mode behavior remains unchanged - it still outputs just `docs/chunks/{chunk}`.

## Subsystem Considerations

<!--
Before designing your implementation, check docs/subsystems/ for relevant
cross-cutting patterns.

QUESTIONS TO CONSIDER:
- Does this chunk touch any existing subsystem's scope?
- Will this chunk implement part of a subsystem (contribute code) or use it
  (depend on it)?
- Did you discover code during exploration that should be part of a subsystem
  but doesn't follow its patterns?

If no subsystems are relevant, delete this section.

WHEN SUBSYSTEMS ARE RELEVANT:
List each relevant subsystem with its status and your relationship:
- **docs/subsystems/0001-validation** (DOCUMENTED): This chunk USES the validation
  subsystem to check input
- **docs/subsystems/0002-error_handling** (REFACTORING): This chunk IMPLEMENTS a
  new error type following the subsystem's patterns

HOW SUBSYSTEM STATUS AFFECTS YOUR WORK:

DOCUMENTED subsystems: The subsystem's patterns are captured but deviations are not
being actively fixed. If you discover code that deviates from the subsystem's
patterns, add it to the subsystem's Known Deviations section. Do NOT prioritize
fixing those deviations—your chunk has its own goals.

REFACTORING subsystems: The subsystem is being actively consolidated. If your chunk
work touches code that deviates from the subsystem's patterns, attempt to bring it
into compliance as part of your work. This is "opportunistic improvement"—improve
what you touch, but don't expand scope to fix unrelated deviations.

WHEN YOU DISCOVER DEVIATING CODE:
- Add it to the subsystem's Known Deviations section
- Note whether you will address it (REFACTORING status + relevant to your work)
  or leave it for future work (DOCUMENTED status or outside your chunk's scope)

Example:
- **Discovered deviation**: src/legacy/parser.py#validate_input does its own
  validation instead of using the validation subsystem
  - Added to docs/subsystems/0001-validation Known Deviations
  - Action: Will not address (subsystem is DOCUMENTED; deviation outside chunk scope)
-->

## Sequence

### Step 1: Modify get_current_task_chunk return type

Updated `get_current_task_chunk` in `src/task_utils.py` to return a tuple of
`(chunk_name, external_artifact_repo)` instead of just `chunk_name`. Added a chunk
backreference comment.

### Step 2: Update CLI handler to format output with repo ref

Updated `_list_task_chunks` in `src/ve.py` to unpack the tuple from
`get_current_task_chunk` and format the output as `{external_repo}::docs/chunks/{chunk_name}`.
Added a chunk backreference comment.

### Step 3: Update existing test for new output format

Updated the test `test_latest_returns_implementing_chunk_from_external_repo` in
`tests/test_task_chunk_list.py` to expect the new format `acme/ext::docs/chunks/0002-auth_validation`
instead of the old format `docs/chunks/0002-auth_validation`.

## Dependencies

<!--
What must exist before this chunk can be implemented?
- Other chunks that must be complete
- External libraries to add
- Infrastructure or configuration

If there are no dependencies, delete this section.
-->

## Risks and Open Questions

<!--
What might go wrong? What are you unsure about?
Being explicit about uncertainty helps you (and agents) know where to
be careful and when to stop and ask questions.

Example:
- fsync behavior may differ across filesystems; need to verify on ext4 and APFS
- Unclear whether concurrent reads during write are safe; may need mutex
- Performance target is aggressive; may need to iterate on buffer sizes
-->

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