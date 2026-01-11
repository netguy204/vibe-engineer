---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: ["src/project.py", "tests/test_project.py", "tests/test_init.py"]
code_references:
  - ref: src/project.py#Project::_init_chunks
    implements: "Creates docs/chunks/ directory during project initialization"
  - ref: src/project.py#Project::init
    implements: "Integration of _init_chunks() into the init workflow"
  - ref: tests/test_project.py#TestProjectInitChunks
    implements: "Unit tests for _init_chunks() method behavior"
  - ref: tests/test_init.py#TestInitCommand::test_init_creates_chunks_directory
    implements: "CLI test verifying docs/chunks/ directory creation"
  - ref: tests/test_init.py#TestInitCommand::test_init_chunks_in_created_output
    implements: "CLI test verifying docs/chunks/ appears in Created output"
  - ref: tests/test_init.py#TestInitCommand::test_init_chunks_idempotent
    implements: "CLI test verifying idempotent behavior for existing chunks directory"
narrative: null
subsystems: []
created_after: ["task_aware_investigations", "task_aware_subsystem_cmds"]
---

# Chunk Goal

## Minor Goal

The `ve init` command must create the `docs/chunks/` directory so that newly initialized projects are recognized as Vibe Engineer projects by the task init process.

Currently, `ve init` creates `docs/trunk/`, `.claude/commands/`, `CLAUDE.md`, and `docs/narratives/`, but not `docs/chunks/`. However, the task init detection logic in `task_init.py:120-123` uses the presence of `docs/chunks/` as the sentinel to determine whether a directory is a VE project:

```python
if not (path / "docs" / "chunks").exists():
    errors.append(
        f"Directory '{repo_ref}' is not a Vibe Engineer project (missing docs/chunks/)"
    )
```

This creates an inconsistency: a freshly initialized project passes `ve init` successfully but fails task init validation. Adding `docs/chunks/` creation to `ve init` ensures the project is fully recognized as a VE project from the moment of initialization.

## Success Criteria

- Running `ve init` on a new project creates `docs/chunks/` directory
- The `docs/chunks/` directory is reported in the "Created" output
- If `docs/chunks/` already exists, it is skipped (idempotent)
- A newly `ve init`'d project passes `ve task init` validation (recognized as a VE project)
- Existing tests continue to pass

