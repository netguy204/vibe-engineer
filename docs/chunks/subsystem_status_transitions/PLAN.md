<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk implements the `ve subsystem status` command following the existing CLI patterns established in src/ve.py. The implementation builds directly on:

- The `SubsystemStatus` enum from src/models.py (lines 12-19)
- The `Subsystems` utility class from src/subsystems.py
- The `update_frontmatter_field()` utility from src/task_utils.py (lines 177-217)

The command will support two modes:
1. **Display mode**: `ve subsystem status <id>` - shows current status
2. **Transition mode**: `ve subsystem status <id> <new-status>` - validates and applies transition

The state machine enforces a deliberate lifecycle where subsystems mature from discovery through documentation to potential stability. The key insight is that DEPRECATED is terminal (no way out), and moving to STABLE requires going through REFACTORING first—you can't declare something stable without actively consolidating it.

Testing follows the project's test-driven development philosophy per docs/trunk/TESTING_PHILOSOPHY.md: write failing tests first, then implement the minimum code to pass them.

## Sequence

### Step 1: Define the state transition rules in models.py

Add a constant dictionary mapping each `SubsystemStatus` to its valid transitions. This encapsulates the state machine logic in a single, testable location.

```python
VALID_STATUS_TRANSITIONS: dict[SubsystemStatus, set[SubsystemStatus]] = {
    SubsystemStatus.DISCOVERING: {SubsystemStatus.DOCUMENTED, SubsystemStatus.DEPRECATED},
    SubsystemStatus.DOCUMENTED: {SubsystemStatus.REFACTORING, SubsystemStatus.DEPRECATED},
    SubsystemStatus.REFACTORING: {SubsystemStatus.STABLE, SubsystemStatus.DOCUMENTED, SubsystemStatus.DEPRECATED},
    SubsystemStatus.STABLE: {SubsystemStatus.DEPRECATED, SubsystemStatus.REFACTORING},
    SubsystemStatus.DEPRECATED: set(),  # Terminal state
}
```

Location: src/models.py

### Step 2: Add update_status method to Subsystems class

Add a method to the `Subsystems` class that:
1. Reads the current status from the subsystem's OVERVIEW.md frontmatter
2. Validates the transition is allowed
3. Updates the frontmatter using the `update_frontmatter_field()` pattern from task_utils.py (adapted for OVERVIEW.md paths)

The method signature:
```python
def update_status(self, subsystem_id: str, new_status: SubsystemStatus) -> tuple[SubsystemStatus, SubsystemStatus]:
    """Update subsystem status with transition validation.

    Returns:
        Tuple of (old_status, new_status) on success.

    Raises:
        ValueError: If subsystem not found, invalid status, or invalid transition.
    """
```

Location: src/subsystems.py

### Step 3: Write failing tests for the status command

Create tests covering all success criteria from GOAL.md:

**Test categories:**

1. **Display mode tests** (SC 4):
   - `test_status_display_shows_current_status` - Shows "validation: DISCOVERING"
   - `test_status_display_with_full_id` - Works with "0001-validation"
   - `test_status_display_with_shortname` - Works with just "validation"

2. **Transition mode tests** (SC 1, 3):
   - `test_valid_transition_discovering_to_documented` - DISCOVERING → DOCUMENTED works
   - `test_valid_transition_documented_to_refactoring` - DOCUMENTED → REFACTORING works
   - `test_valid_transition_refactoring_to_stable` - REFACTORING → STABLE works
   - `test_valid_transition_stable_to_deprecated` - STABLE → DEPRECATED works
   - `test_valid_transition_refactoring_to_documented` - REFACTORING → DOCUMENTED (rollback) works
   - `test_invalid_transition_discovering_to_stable` - Cannot skip steps
   - `test_invalid_transition_deprecated_to_any` - Terminal state enforced

3. **ID resolution tests** (SC 2):
   - `test_resolves_shortname_to_full_id` - "validation" resolves to "0001-validation"
   - `test_accepts_full_id_directly` - "0001-validation" works directly

4. **Error handling tests** (SC 5):
   - `test_subsystem_not_found_error` - Clear error message
   - `test_invalid_status_value_error` - Lists valid statuses
   - `test_invalid_transition_error` - Shows current status and valid next states

5. **Output format tests** (SC 6):
   - `test_success_output_shows_transition` - "validation: DISCOVERING → DOCUMENTED"

6. **Frontmatter preservation tests** (SC 7):
   - `test_update_preserves_other_frontmatter_fields` - chunks, code_references intact
   - `test_update_preserves_document_content` - Body content unchanged

Location: tests/test_subsystem_status.py

### Step 4: Implement the CLI command

Add the `status` subcommand to the `subsystem` group in src/ve.py:

```python
@subsystem.command()
@click.argument("subsystem_id")
@click.argument("new_status", required=False)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def status(subsystem_id, new_status, project_dir):
    """Show or update subsystem status."""
```

Implementation flow:
1. Initialize `Subsystems(project_dir)`
2. Resolve `subsystem_id` using `find_by_shortname()` if it's a shortname
3. Parse current frontmatter to get existing status
4. If `new_status` is None: display mode - print current status
5. If `new_status` provided: validate it's a valid SubsystemStatus enum value
6. Call `subsystems.update_status()` to validate transition and update
7. Print success or error message

Location: src/ve.py

### Step 5: Implement update_frontmatter for OVERVIEW.md

Create a helper function (or adapt `update_frontmatter_field`) that works with subsystem OVERVIEW.md files. The existing `update_frontmatter_field` in task_utils.py handles GOAL.md files, but the pattern is the same:

1. Read file content
2. Extract frontmatter between `---` markers using regex
3. Parse YAML with `yaml.safe_load()`
4. Update the `status` field
5. Reconstruct file with `yaml.dump()` and write back

This can either be:
- A new method `update_overview_frontmatter()` in subsystems.py, or
- Reuse `update_frontmatter_field()` by passing the OVERVIEW.md path directly

Location: src/subsystems.py (preferred, to keep subsystem logic together)

### Step 6: Run tests and verify all pass

Execute the test suite to ensure all tests pass:

```bash
pytest tests/test_subsystem_status.py -v
```

Then run the full test suite to ensure no regressions:

```bash
pytest tests/ -v
```

### Step 7: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter to include the files touched:

```yaml
code_paths:
  - src/models.py
  - src/subsystems.py
  - src/ve.py
  - tests/test_subsystem_status.py
```

## Dependencies

- **Chunk 0014-subsystem_schemas_and_model**: Provides `SubsystemStatus` enum - COMPLETE
- **Chunk 0016-subsystem_cli_scaffolding**: Provides `ve subsystem` command group and `Subsystems` class - COMPLETE

No external library dependencies beyond what's already in the project.

## Risks and Open Questions

1. **Shortname collision**: If multiple subsystems somehow have the same shortname (shouldn't happen due to duplicate check in `discover`), `find_by_shortname()` returns the first match. This is acceptable behavior.

2. **Concurrent updates**: If two processes update the same subsystem's status simultaneously, the last write wins. This is acceptable for a CLI tool where concurrent usage is unlikely.

3. **YAML formatting**: The `yaml.dump()` function may reformat the frontmatter slightly differently than the original. This is acceptable as long as the content is preserved correctly and remains parseable.

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
-->
