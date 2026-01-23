---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/claude/CLAUDE.md.jinja2
code_references:
  - ref: src/templates/claude/CLAUDE.md.jinja2
    implements: "Friction Log documentation section, entry structure, lifecycle, and artifact-type guidance"
narrative: null
investigation: friction_log_artifact
subsystems: []
created_after:
- orch_attention_queue
- orch_conflict_oracle
- orch_agent_skills
- orch_question_forward
---

# Chunk Goal

## Minor Goal

Document the friction log artifact type in CLAUDE.md, making the workflow discoverable to agents and users.

This ensures new agents understand friction logs exist, when to use them, and how they fit into the artifact hierarchy alongside chunks, investigations, narratives, and subsystems.

## Success Criteria

- CLAUDE.md.jinja2 template includes a "Friction Log" section in the artifact documentation
- Documentation explains:
  - What friction logs are for (accumulating pain points over time)
  - How they differ from other artifacts (indefinite lifespan, many entries, no artifact-level status)
  - Entry structure (`### FXXX: YYYY-MM-DD [theme-id] Title`)
  - How themes emerge organically
  - How friction spawns proposed_chunks
  - The bidirectional linking with chunks via `friction_entries`
- Mentions the `/friction-log` command for quick capture
- References `docs/trunk/FRICTION.md` as the canonical location
- `ve init` regenerates CLAUDE.md with the new content

## Dependencies

Requires `friction_template_and_cli` chunk to be implemented first (the artifact must exist before documenting it).