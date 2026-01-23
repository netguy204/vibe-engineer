---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/claude/CLAUDE.md.jinja2
code_references:
  - ref: src/templates/claude/CLAUDE.md.jinja2
    implements: "Learning Philosophy section documenting the natural progression from chunks to narratives/subsystems to tasks to orchestration"
narrative: null
investigation: task_agent_experience
subsystems: []
created_after:
- chunk_create_guard
- orch_attention_reason
- orch_inject_validate
- deferred_worktree_creation
---

# Chunk Goal

## Minor Goal

Add a brief "Learning Philosophy" section to the project CLAUDE.md template (`src/templates/claude/CLAUDE.md.jinja2`) that sets expectations for how operators naturally progress through the vibe engineering system:

1. **Chunks first** - Operators start with the immediate gratification of the chunk loop (create → plan → implement → complete)
2. **Larger artifacts when needed** - Narratives, subsystems, and investigations are discovered when chunks aren't enough
3. **Tasks for multi-project work** - When work spans repositories, the same patterns apply at a larger scale
4. **Orchestration for parallel workflows** - When managing multiple concurrent workstreams, the orchestrator (`ve orch`) automates scheduling, attention routing, and conflict detection

This section should be concise (a few sentences or a short paragraph) and placed in the "Getting Started" section or as a new brief section nearby. It should communicate that:
- You don't need to learn everything upfront
- Each artifact type is discovered when the current level becomes insufficient
- The documentation itself teaches you what you need (via backreferences and following code to docs)
- The system scales with your ambition: single chunks → multi-chunk narratives → multi-project tasks → parallel orchestration

## Success Criteria

1. The CLAUDE.md.jinja2 template contains a new section (or addition to Getting Started) mentioning the natural learning progression
2. The content is concise—no more than 10-15 lines—conveying the key insight without duplicating the full learning philosophy
3. Running `uv run ve init` successfully regenerates CLAUDE.md with the new content
4. The message is encouraging and signals that complexity is opt-in, not required upfront