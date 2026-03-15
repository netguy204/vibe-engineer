---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/steward-setup.md.jinja2
- src/templates/commands/steward-watch.md.jinja2
- src/templates/commands/steward-send.md.jinja2
- src/templates/commands/steward-changelog.md.jinja2
- src/templates/claude/CLAUDE.md.jinja2
code_references:
  - ref: src/templates/commands/steward-setup.md.jinja2
    implements: "Steward setup interview skill - guides operator through SOP creation"
  - ref: src/templates/commands/steward-watch.md.jinja2
    implements: "Steward watch-respond-rewatch loop skill with cursor management"
  - ref: src/templates/commands/steward-send.md.jinja2
    implements: "Steward message sending skill for cross-agent communication"
  - ref: src/templates/commands/steward-changelog.md.jinja2
    implements: "Changelog watching skill with independent cursor tracking"
  - ref: src/templates/claude/CLAUDE.md.jinja2
    implements: "Registration of steward skills in Available Commands section"
  - ref: tests/test_steward_skills.py
    implements: "Template rendering tests for steward skill files"
narrative: leader_board
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- leader_board_cli
created_after:
- finalize_double_commit
---

# Chunk Goal

## Minor Goal

Create Claude Code steward skills that teach agents the leader board workflow
patterns. These are VE template-rendered skills installed by `ve init`.

**Skills:**

- `/steward-setup` — Interviews the operator to produce the project's steward
  SOP document (stored in `docs/trunk/STEWARD.md` or similar). The SOP defines
  the steward's name, its channel, the changelog channel, and critically, how
  it should respond to inbound messages — autonomous fix-and-publish, queue
  work for a human operator, or custom behavior. The interview captures the
  operator's intent for this specific project. Swarm creation is NOT part of
  setup — the operator has already created the swarm via `ve board swarm create`
  and holds the private key in `~/.ve/`.

- `/steward-watch` — The watch-respond-rewatch loop using `run_in_background`.
  Read the SOP, watch with cursor, receive message, triage according to SOP,
  act, post outcome to changelog channel, ack to advance cursor, rewatch.

- `/steward-send` — Send a message to a steward's channel from any agent
  context.

- `/steward-changelog` — Watch a project's changelog channel with the
  requester's own cursor (used to close the loop after sending a message).

## Success Criteria

- All four skills exist as Jinja2 templates in `src/templates/`
- `ve init` renders them into `.claude/commands/` (or `.claude/skills/`)
- `/steward-setup` produces a valid SOP document through operator interview
- `/steward-watch` correctly teaches the watch-respond-rewatch loop pattern
  including cursor management and SOP-driven triage
- `/steward-send` correctly teaches message sending to a steward channel
- `/steward-changelog` correctly teaches changelog watching with independent
  cursor
- A steward agent following `/steward-watch` can autonomously loop without
  human intervention on mechanics

## Rejected Ideas

<!-- DELETE THIS SECTION when the goal is confirmed if there were no rejected
ideas.

This is where the back-and-forth between the agent and the operator is recorded
so that future agents understand why we didn't do something.

If there were rejected ideas in the development of this GOAL with the operator,
list them here with the reason they were rejected.

Example:

### Store the queue in redis

We could store the queue in redis instead of a file. This would allow us to scale the queue to multiple nodes.

Rejected because: The queue has no meaning outside the current session.

---

-->