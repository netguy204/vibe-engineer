---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- README.md
code_references:
  - ref: README.md
    implements: "Orchestrator and Steward documentation sections in the project README"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- leader_board_durable_objects
- leader_board_user_config
---

# Chunk Goal

## Minor Goal

Add two new sections to the project README.md:

1. **Orchestrator (`ve orch`)** — Explain how to use the orchestrator for parallel chunk execution across worktrees. Cover the key commands (`ve orch inject`, `ve orch status`), the concept of FUTURE chunks being scheduled and executed in isolated worktrees, and how the orchestrator handles planning/implementation/completion autonomously.

2. **Steward** — Explain how to use the steward for autonomous project management. Cover setup (`/steward-setup`), the watch loop (`/steward-watch`), how inbound messages are triaged and turned into chunks, and how the steward delegates work to the orchestrator.

These sections should be placed in the "Usage" area of the README, after the existing "Cross-Repository Work" section and before "Development Setup". They help new users understand and adopt both features.

## Success Criteria

- README.md contains a new "Orchestrator" section explaining `ve orch` commands and parallel execution
- README.md contains a new "Steward" section explaining autonomous project management
- Both sections include example CLI commands
- Sections are placed logically within the existing README structure
- Existing README content is not modified

