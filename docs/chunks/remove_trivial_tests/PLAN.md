# Implementation Plan

## Approach

This chunk removes trivial tests from the test suite and updates the testing
philosophy with guidance to prevent future trivial tests. The approach is:

1. **Systematic audit**: Review each test file and identify trivial tests using
   the criteria in the chunk GOAL.md
2. **Categorize findings**: Document which tests are trivial and why
3. **Remove trivial tests**: Delete identified tests, preserving meaningful ones
4. **Update testing philosophy**: Add generalizable guidance as an anti-pattern
5. **Verify test suite**: Run pytest to confirm no regressions

### What Makes a Test Trivial

A test is trivial if it:
- Asserts that an attribute equals the value it was just assigned
- Cannot fail unless Python/the framework itself is broken
- Tests no computed properties, transformations, side effects, or behavior

Examples of trivial patterns:
```python
# TRIVIAL: Tests Python assignment works
obj = Thing(name="foo")
assert obj.name == "foo"

# TRIVIAL: Tests Pydantic stores values
config = Config(value="x")
assert config.value == "x"
```

### Audit Results

After reviewing all 27 test files, I identified the following trivial tests:

**test_models.py - TestSymbolicReference**
- `test_valid_file_only_reference`: Asserts `ref.ref == "src/chunks.py"` after
  setting it - trivial
- `test_valid_class_reference`: Same pattern - trivial
- `test_valid_method_reference`: Same pattern - trivial
- `test_valid_nested_class_reference`: Same pattern - trivial
- `test_valid_standalone_function`: Same pattern - trivial

**test_models.py - TestSubsystemRelationship**
- `test_valid_implements_relationship`: Asserts values equal what was just
  assigned - trivial
- `test_valid_uses_relationship`: Same pattern - trivial
- `test_subsystem_id_with_underscores`: Asserts value equals assigned - trivial
- `test_subsystem_id_with_multiple_hyphens`: Same pattern - trivial

**test_subsystems.py - TestSubsystemStatus**
- `test_all_status_values_exist`: Asserts enum values equal their string
  representations - tests language/enum mechanics - trivial
- `test_enum_is_string_enum`: Asserts isinstance and str() work - trivial

**test_subsystems.py - TestChunkRelationship**
- `test_valid_implements_relationship`: Asserts values equal what was assigned - trivial
- `test_valid_uses_relationship`: Same pattern - trivial

**test_subsystems.py - TestSubsystemFrontmatter**
- `test_valid_frontmatter_empty_chunks`: Asserts `chunks == []` after setting
  to `[]` - trivial
- `test_valid_frontmatter_empty_code_references`: Same pattern - trivial
- `test_valid_frontmatter_defaults`: Asserts defaults equal documented defaults - trivial

**test_task_models.py - TestTaskConfig**
- `test_task_config_valid_minimal`: Asserts values equal what was assigned - trivial
- `test_task_config_valid_multiple_projects`: Asserts `len(projects) == 3` - trivial

**test_task_models.py - TestExternalChunkRef**
- `test_external_chunk_ref_valid_minimal`: Asserts values equal what was assigned - trivial
- `test_external_chunk_ref_valid_with_versioning`: Same pattern - trivial
- `test_external_chunk_ref_accepts_valid_pinned`: Same pattern - trivial

**test_task_models.py - TestChunkDependent**
- `test_chunk_dependent_valid_single`: Asserts `len(dependents) == 1` - trivial
- `test_chunk_dependent_valid_multiple`: Asserts `len(dependents) == 2` - trivial
- `test_chunk_dependent_accepts_empty_list`: Asserts `dependents == []` - trivial
- `test_chunk_dependent_accepts_dict_syntax`: Asserts Pydantic coercion works - trivial

**test_project.py - TestProjectClass**
- `test_project_dir_stored`: Asserts `project_dir == temp_project` after
  `Project(temp_project)` - trivial

**test_template_system.py - TestActiveChunk**
- `test_active_chunk_has_short_name`: Asserts value equals what was assigned - trivial
- `test_active_chunk_has_id`: Same pattern - trivial

**test_template_system.py - TestActiveNarrative**
- `test_active_narrative_has_short_name`: Asserts value equals what was assigned - trivial
- `test_active_narrative_has_id`: Same pattern - trivial

**test_template_system.py - TestActiveSubsystem**
- `test_active_subsystem_has_short_name`: Asserts value equals what was assigned - trivial
- `test_active_subsystem_has_id`: Same pattern - trivial

### Tests That Are NOT Trivial

Many tests that look superficially similar are actually meaningful:

- **Validation tests** (e.g., `test_invalid_empty_ref`): Test that the system
  _rejects_ bad input - this is behavior
- **Computed property tests** (e.g., `test_active_chunk_goal_path_returns_path`):
  Test a property that computes a path from other data
- **Side effect tests** (e.g., `test_create_chunk_creates_directory`): Test that
  an operation produces expected filesystem changes
- **Error condition tests**: Test that specific errors are raised with expected
  messages
- **Business logic tests** (e.g., overlap detection, symbolic reference parsing):
  Test actual algorithms

## Sequence

### Step 1: Remove trivial tests from test_models.py

Remove the 9 trivial tests identified in TestSymbolicReference and
TestSubsystemRelationship classes. Keep all validation error tests.

Location: tests/test_models.py

### Step 2: Remove trivial tests from test_subsystems.py

Remove the 7 trivial tests identified in TestSubsystemStatus, TestChunkRelationship,
and TestSubsystemFrontmatter classes. Keep all validation and parsing tests.

Location: tests/test_subsystems.py

### Step 3: Remove trivial tests from test_task_models.py

Remove the 9 trivial tests identified in TestTaskConfig, TestExternalChunkRef,
and TestChunkDependent classes. Keep all validation error tests.

Location: tests/test_task_models.py

### Step 4: Remove trivial test from test_project.py

Remove `test_project_dir_stored` from TestProjectClass. Keep all other tests
which verify actual behavior (file creation, idempotency, etc.).

Location: tests/test_project.py

### Step 5: Remove trivial tests from test_template_system.py

Remove the 6 trivial tests from TestActiveChunk, TestActiveNarrative, and
TestActiveSubsystem that only verify attribute storage. Keep tests that verify
computed paths and actual template rendering behavior.

Location: tests/test_template_system.py

### Step 6: Run test suite to verify no regressions

Run `pytest tests/` to confirm all remaining tests pass.

### Step 7: Update TESTING_PHILOSOPHY.md

Add a new section documenting the "trivial test" anti-pattern with:
- Definition of the general principle (test behavior, not language semantics)
- Abstract criteria for identifying trivial tests
- Examples illustrating the principle
- Guidance for recognizing novel forms of this mistake

Location: docs/trunk/TESTING_PHILOSOPHY.md

## Risks and Open Questions

- **Risk**: Some tests that appear trivial might be catching real bugs in edge
  cases. Mitigation: Carefully review each test's purpose before removal and run
  the full test suite afterward.

- **Risk**: Removing "valid input" tests might reduce confidence that the models
  work. Response: The validation error tests provide the same confidence - if
  invalid input is rejected correctly, valid input must be working. The trivial
  tests add noise without adding value.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->