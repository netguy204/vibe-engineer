---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/claude/CLAUDE.md.jinja2
  - src/templates/claude/AGENTS.md.jinja2
  - src/templates/commands/chunk-create.md.jinja2
  - docs/trunk/ARTIFACTS.md
  - README.md
code_references:
  - ref: src/templates/claude/CLAUDE.md.jinja2
    implements: "Chunks section framing, Available Commands description, and Getting Started section qualified for intent-bearing work"
  - ref: src/templates/claude/AGENTS.md.jinja2
    implements: "Mirror of CLAUDE.md.jinja2 intent-bearing framing for agent surfaces"
  - ref: src/templates/commands/chunk-create.md.jinja2
    implements: "Skill description qualified to signal chunks are for intent-bearing work"
  - ref: docs/trunk/ARTIFACTS.md
    implements: "Choosing-between-artifacts table and backreference lifespan updated for intent framing"
  - ref: README.md
    implements: "Working in Chunks section reframed around intent ownership"
narrative: intent_ownership
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- intent_principles
---

# Chunk Goal

## Minor Goal

The workflow-facing documentation describes chunks as the artifact for intent-bearing work, not as the default mechanism for all work. Anywhere in the docs that implies "every change should be a chunk," the language is corrected to reflect principle 2: chunks exist only for intent-bearing work; intent-less work bypasses the chunk system entirely.

The canonical principle lives in `docs/trunk/CHUNKS.md`. Other docs reference it rather than re-stating it.

## Success Criteria

1. `src/templates/claude/CLAUDE.md.jinja2` chunk-related sections reference `docs/trunk/CHUNKS.md` principle 2 by name. Examples of when NOT to create a chunk are surfaced (e.g., typo fixes, dependency bumps, mechanical renames).
2. `docs/trunk/ARTIFACTS.md` chunk section reflects the intent-bearing framing. The existing CHUNKS.md cross-reference (already added by `intent_principles`) remains the entry point.
3. README.md (or whatever the project's top-level intro doc is) — if it discusses chunks — reflects the framing.
4. Skill description frontmatter and prose in `src/templates/commands/*.jinja2` are scanned for "chunks for everything" implications:
   - Any phrasing like "use `/chunk-create` to start new work" gets qualified to "...to start new intent-bearing work" or replaced with a CHUNKS.md reference.
   - The `/chunk-create` skill description (separate from chunk 2's behavior changes) reflects the gating purpose.
5. `uv run ve init` runs cleanly.
6. `uv run pytest tests/` passes (no test changes expected; if any break, investigate).

## Out of Scope

- Behavioral changes to `/chunk-create` or `/chunk-complete` (chunks 2 and 3).
- Auditing or rewriting individual existing chunks (chunks 5 and 6).
- Updating the `respect_future_intent` chunk's GOAL.md (chunk 6).
- Changes to `docs/trunk/CHUNKS.md` itself — it's the canonical source; other docs reference it.