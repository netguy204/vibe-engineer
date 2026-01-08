---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/ve.py
  - src/project.py
  - src/templates/CLAUDE.md
code_references:
  - ref: src/project.py#InitResult
    implements: "Tracks created/skipped/warnings for idempotent operations"
  - ref: src/project.py#Project
    implements: "Project class with lazy Chunks property"
  - ref: src/project.py#Project::_init_trunk
    implements: "Creates docs/trunk/ and copies template documents"
  - ref: src/project.py#Project::_init_commands
    implements: "Creates .claude/commands/ symlinks with copy fallback"
  - ref: src/project.py#Project::_init_claude_md
    implements: "Copies CLAUDE.md template to project root"
  - ref: src/project.py#Project::init
    implements: "Orchestrates all initialization, aggregates results"
  - ref: src/ve.py#init
    implements: "CLI init command - invokes Project.init() and displays results"
  - ref: src/templates/CLAUDE.md
    implements: "CLAUDE.md template explaining vibe engineering workflow to agents"
  - ref: tests/test_project.py
    implements: "Tests Project class, init(), and idempotency"
  - ref: tests/test_init.py
    implements: "CLI integration tests for 've init'"
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