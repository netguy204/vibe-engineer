# Testing Philosophy

This document establishes how we think about verification in this project.
It informs every chunk's testing strategy but doesn't prescribe specific tests.

## Testing Principles

### Test-Driven Development

We practice test-driven development. The workflow is:

1. **Write failing tests first** - Before writing any implementation code, write tests that express what the code should do. These tests must fail initially.
2. **Write the implementation** - Write the minimum code necessary to make the tests pass.
3. **See previously failing tests succeed** - The same tests that failed now pass, providing confidence that the implementation satisfies the requirements.

This order is non-negotiable. Writing tests after implementation invites tests that merely describe what the code happens to do, rather than what it should do.

### Goal-Driven Test Design

Tests must assert semantically meaningful properties with respect to the goal. There must always be a clear, traceable relationship between:

- The success criteria in a chunk's GOAL.md
- The tests that verify those criteria

Each test should answer: "What success criterion does this test verify?" If the answer isn't clear, the test may not be valuable.

### Semantic Assertions Over Structural Assertions

**Avoid superficial assertions.** Tests that check types, property existence, or implementation details provide false confidence. They pass when the code is wrong and break when the code is refactored correctly.

Bad:
```python
def test_create_chunk():
    result = chunks.create_chunk("VE-001", "feature")
    assert result is not None
    assert isinstance(result, pathlib.Path)
    assert hasattr(result, 'name')
```

Good:
```python
def test_create_chunk_creates_directory():
    result = chunks.create_chunk("VE-001", "feature")
    assert result.exists()
    assert result.is_dir()
    assert "0001-feature-VE-001" in result.name
```

The bad test passes even if the directory is never created. The good test verifies the actual goal: a directory exists with the expected name.

### Test Behavior at Boundaries

The interesting bugs live at boundaries. Prioritize testing:

- Empty states (no chunks exist)
- Error conditions (invalid input, missing files)
- Edge cases explicitly mentioned in success criteria

## Test Categories

### Unit Tests

Unit tests verify individual functions and classes in isolation. In this project:

- **Boundary**: A single function or method
- **Dependencies**: Real implementations for simple dependencies (pathlib, re). Temporary directories for filesystem operations.
- **Location**: `tests/test_<module>.py`

Example: `test_chunks.py` tests the `Chunks` class methods directly without going through the CLI.

### CLI Integration Tests

CLI integration tests verify the command-line interface end-to-end. They exercise the full path from argument parsing through to output.

- **Boundary**: The entire CLI command
- **Dependencies**: Real filesystem via temporary directories. Click's `CliRunner` for invoking commands.
- **Location**: `tests/test_<command>.py` (e.g., `test_chunk_start.py`, `test_chunk_list.py`)

These tests verify success criteria like:
- Exit codes (0 for success, non-zero for errors)
- Output messages (what the user sees)
- Side effects (files created, directories structured correctly)

### What We Don't Have

This project does not currently use:
- **Property tests**: The domain doesn't have complex invariants that benefit from fuzzing
- **Performance tests**: No performance requirements in SPEC.md
- **System tests**: CLI integration tests serve this purpose

## Hard-to-Test Properties

### User Confirmation Prompts

Interactive prompts (e.g., "Create another chunk with the same name?") are tested by:
- Providing simulated input via Click's test runner: `runner.invoke(cli, [...], input="y\n")`
- Testing both confirmation and rejection paths
- Testing the `--yes` flag that bypasses prompts

## What We Don't Test

- **Template content**: We verify templates render without error and files are created, but don't assert on template prose
- **Help text wording**: We verify help exists, not its exact phrasing
- **Output formatting**: We verify key information is present, not exact formatting

## Test Organization

```
tests/
├── conftest.py           # Shared fixtures (temp_project, runner)
├── test_chunks.py        # Unit tests for Chunks class
├── test_chunk_start.py   # CLI tests for 've chunk start'
├── test_chunk_list.py    # CLI tests for 've chunk list'
├── test_project.py       # Unit tests for Project class
└── test_init.py          # CLI tests for 've init'
```

Naming convention: `test_<module>.py` for unit tests, `test_<command>.py` for CLI tests.

## CI Requirements

All tests must pass before code is merged:

```bash
pytest tests/
```

Tests should complete in under 10 seconds. If tests become slow, investigate before adding timeouts or skips.
