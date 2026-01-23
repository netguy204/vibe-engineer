<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The implementation follows a two-context strategy that mirrors patterns already
established in the codebase for other task-aware commands (create, list, sync):

1. **Context Detection**: Extend validation to detect whether it's running in a
   task context (`.ve-task.yaml` present) or project context (no task config).

2. **External Chunk Resolution**: When validating an external chunk from a
   project context, dereference it via `external.yaml` to locate the actual
   chunk content in the external artifact repo.

3. **Code Reference Validation Scope**: Adapt `_validate_symbol_exists()` to
   understand project-qualified references and resolve them appropriately:
   - In task context: Resolve all project prefixes to actual directories
   - In project context: Validate local refs, skip cross-project refs with
     informative message

The approach leverages existing infrastructure:
- `task_utils.is_task_directory()`, `load_task_config()`, `resolve_repo_directory()`
- `external_refs.load_external_ref()`, `is_external_artifact()`
- `symbols.parse_reference()`, `qualify_ref()`

Per TESTING_PHILOSOPHY.md, tests will be written first following TDD. Tests will
verify the semantic behavior: can external chunks be validated, are cross-project
refs handled correctly in each context.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (DOCUMENTED): This chunk USES the external
  reference utilities from this subsystem (`load_external_ref`, `is_external_artifact`,
  `ARTIFACT_DIR_NAME`). No deviations discovered—following existing patterns.

## Sequence

### Step 1: Write failing tests for external chunk validation from project context

Create tests in `tests/test_chunk_validate.py` that verify:

1. A project with an `external.yaml` pointing to an external repo can validate
   that external chunk by name
2. The validation reads the actual GOAL.md from the dereferenced location
3. Error messages are clear when external repo is not accessible

Test structure:
- Set up a project dir with `docs/chunks/ext_chunk/external.yaml`
- Set up an external repo dir with `docs/chunks/ext_chunk/GOAL.md`
- Run `ve chunk validate ext_chunk --project-dir <project>`
- Expect success (or meaningful failure if content is invalid)

Location: tests/test_chunk_validate.py (new test class: `TestExternalChunkValidation`)

### Step 2: Implement external chunk resolution in Chunks class

Add method `_resolve_chunk_location()` to `src/chunks.py` that:

1. Checks if the chunk exists locally (current behavior)
2. If not found locally, checks if there's an external.yaml for that chunk
3. If external.yaml exists, reads it and returns path to actual chunk in external repo
4. Uses `external_refs.load_external_ref()` to parse external.yaml
5. Uses a simple heuristic to locate the external repo (sibling directory with
   matching repo name, or explicit search path parameter)

Update `validate_chunk_complete()` to use this resolution before parsing frontmatter.

Location: src/chunks.py

### Step 3: Write failing tests for task-context validation

Create tests that verify:

1. Running `ve chunk validate <chunk>` from a task directory validates chunks
   in the external artifact repo
2. Cross-project code references are fully validated (files resolved across
   project boundaries)
3. Local (non-qualified) code references are validated against the project
   containing the chunk

Test structure:
- Set up task directory with `.ve-task.yaml`
- Set up external repo with chunk containing cross-project refs
- Set up project directories
- Run validation and verify cross-project refs are checked

Location: tests/test_chunk_validate.py (new test class: `TestTaskContextValidation`)

### Step 4: Add task context awareness to validation

Modify `validate_chunk_complete()` in `src/chunks.py` to:

1. Accept optional `task_dir` parameter for task context
2. When task_dir is provided, resolve code references using task config:
   - Parse project qualifier from reference using `symbols.parse_reference()`
   - Map project qualifier to actual path using `task_utils.resolve_repo_directory()`
   - Validate symbol exists in resolved path

Location: src/chunks.py

### Step 5: Write failing tests for project-context partial validation

Create tests that verify:

1. Running validation from project context with cross-project refs produces
   informative skip message (not error)
2. Local refs (no project qualifier) are validated normally
3. The skip message indicates why validation was partial

Location: tests/test_chunk_validate.py (extend `TestExternalChunkValidation`)

### Step 6: Implement partial validation with skip messages

Update `_validate_symbol_exists()` in `src/chunks.py` to:

1. Accept optional `task_dir` and `available_projects` parameters
2. Parse the reference to extract project qualifier
3. If project-qualified and not in task context:
   - Return info message: "Skipped: Cross-project reference requires task context"
4. If project-qualified and in task context:
   - Resolve project to path and validate
5. If not project-qualified:
   - Validate against current project (existing behavior)

Location: src/chunks.py

### Step 7: Wire up CLI command to detect and pass context

Update `ve chunk validate` command in `src/ve.py` to:

1. Detect task context by walking up from project_dir looking for `.ve-task.yaml`
2. If task context found, pass task_dir to validation
3. If no task context, use current project-only validation

This mirrors the pattern used by `ve chunk create` and `ve chunk list`.

Location: src/ve.py

### Step 8: Integration test for end-to-end behavior

Add integration tests that verify the full CLI behavior:

1. `ve chunk validate ext_chunk` from project context resolves external chunk
2. `ve chunk validate my_chunk` from task context validates cross-project refs
3. Output messages are agent-friendly (clear success/failure, actionable hints)

Location: tests/test_chunk_validate.py

## Dependencies

No external dependencies. All required infrastructure exists:

- `task_utils` module provides task context detection and resolution
- `external_refs` module provides external.yaml parsing
- `symbols` module provides reference parsing with project qualifiers
- Existing test helpers in `conftest.py` can be extended for task setup

## Risks and Open Questions

1. **External repo location heuristic**: When running from a project context,
   we need to find the external repo on disk. The plan assumes it's a sibling
   directory matching the repo name from `external.yaml`. If this doesn't hold
   (e.g., the project is not within a task directory structure), we may need to
   add a `--external-repo` flag or accept that validation only works in task
   context for external chunks.

2. **Project qualifier format**: The `symbols.parse_reference()` function expects
   `org/repo::path#symbol` format. Need to verify this matches how references
   are actually written in chunk frontmatter. If deviations exist, may need to
   normalize during parsing.

3. **Test fixture complexity**: Task context tests require setting up multiple
   directories (task dir, external repo, project dirs). This may make tests
   verbose. Consider extracting a shared fixture if patterns emerge.

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