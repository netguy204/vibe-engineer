---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/ve.py
  - src/project.py
  - src/templates/CLAUDE.md
code_references:
  - file: src/project.py
    ranges:
      - lines: 12-18
        implements: "InitResult dataclass - tracks created/skipped/warnings for idempotent operations"
      - lines: 20-31
        implements: "Project class with lazy Chunks property"
      - lines: 32-48
        implements: "_init_trunk() - creates docs/trunk/ and copies template documents"
      - lines: 50-75
        implements: "_init_commands() - creates .claude/commands/ symlinks with copy fallback"
      - lines: 77-89
        implements: "_init_claude_md() - copies CLAUDE.md template to project root"
      - lines: 91-108
        implements: "init() - orchestrates all initialization, aggregates results"
  - file: src/ve.py
    ranges:
      - lines: 61-76
        implements: "CLI init command - invokes Project.init() and displays results"
  - file: src/templates/CLAUDE.md
    ranges:
      - lines: 1-46
        implements: "CLAUDE.md template explaining vibe engineering workflow to agents"
  - file: tests/test_project.py
    ranges:
      - lines: 7-34
        implements: "TestProjectClass - tests Project class basics and lazy Chunks property"
      - lines: 36-129
        implements: "TestProjectInit - tests init() creates trunk docs, commands, CLAUDE.md"
      - lines: 131-200
        implements: "TestProjectInitIdempotency - tests init() skips existing files"
  - file: tests/test_init.py
    ranges:
      - lines: 9-68
        implements: "TestInitCommand - CLI integration tests for 've init'"
---

# Chunk Goal

## Minor Goal

Implement the `ve init` command that bootstraps a project for the vibe engineering workflow. This is a critical enabling step—without initialization, users cannot begin using the documentation-driven development workflow that is core to the project's thesis.

The init command must:

1. **Initialize the trunk document set** - Copy templates from `src/templates/trunk/` to `docs/trunk/`, creating the foundational documentation structure (GOAL.md, SPEC.md, DECISIONS.md, TESTING_PHILOSOPHY.md).

2. **Set up Claude Code commands** - Create the `.claude/commands/` directory and symlink all command templates from `src/templates/commands/` into it. This enables the `/chunk-create`, `/chunk-plan`, `/chunk-complete`, and `/chunk-update-references` slash commands within Claude Code sessions.

3. **Create CLAUDE.md** - Copy the `src/templates/CLAUDE.md` template to the project root. This template explains the vibe engineering workflow to agents, including:
   - The purpose of the `docs/trunk/` directory and its documents
   - The concept of chunks and the `docs/chunks/` directory structure
   - How agents should navigate and use this documentation system

## Success Criteria

- Running `ve init` in an empty project creates:
  - `docs/trunk/GOAL.md` (from template)
  - `docs/trunk/SPEC.md` (from template)
  - `docs/trunk/DECISIONS.md` (from template)
  - `docs/trunk/TESTING_PHILOSOPHY.md` (from template)
  - `.claude/commands/` directory with symlinks to all command templates
  - `CLAUDE.md` at project root (from `src/templates/CLAUDE.md`)

- The command is idempotent: running `ve init` on an already-initialized project skips existing files without error

- Symlinks in `.claude/commands/` point to the ve package's `src/templates/commands/` directory (so they update automatically when ve is upgraded)

- The generated `CLAUDE.md` provides sufficient context for an uninitiated agent to:
  - Understand the trunk/chunks documentation model
  - Know where to find the project goal and specification
  - Navigate chunk history to understand implementation decisions

## Behavior Details

### Idempotency
- If `docs/trunk/` exists with files, skip those files (don't overwrite)
- If `.claude/commands/` exists with symlinks, skip existing symlinks
- If `CLAUDE.md` exists, skip it
- Report what was created vs skipped

### Error Handling
- If symlink creation fails (e.g., on Windows without developer mode), fall back to copying files and warn the user
- If template files are missing from the ve installation, fail with a clear error message

### Output
- Print each file/directory created
- Summarize what was skipped if anything already existed