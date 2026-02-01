---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/chunk-plan.md.jinja2
- docs/trunk/ARTIFACTS.md
code_references:
  - ref: src/templates/commands/chunk-plan.md.jinja2
    implements: "Cluster prefix suggestion step (Step 2) for semantic chunk naming"
  - ref: docs/trunk/ARTIFACTS.md
    implements: "Investigation frontmatter reference, Proposed Chunks section, and Investigation lifecycle details (moved from CLAUDE.md.jinja2 by progressive_disclosure_refactor)"
narrative: null
investigation: template_drift
subsystems: []
created_after:
- xr_ve_worktrees_flag
- task_chunk_validation
---

# Chunk Goal

## Minor Goal

Restore content that was lost from source templates due to the template drift pattern identified in the `template_drift` investigation. Agents previously edited rendered files (`.claude/commands/*.md`, `CLAUDE.md`) instead of source templates (`src/templates/`), and subsequent re-renders overwrote their work.

This chunk backports the lost content from git history to the source templates, ensuring future renders include the complete, intended content.

## Success Criteria

1. **chunk-plan.md.jinja2 restored**: The cluster prefix suggestion step is restored to `src/templates/commands/chunk-plan.md.jinja2` from commit `8a29e62`:
   - Step 2 runs `ve chunk suggest-prefix <chunk_name>` to check for semantic clustering
   - Presents suggestion to operator if prefix is found
   - Allows renaming before continuing

2. **CLAUDE.md.jinja2 restored**: The following sections are restored to `src/templates/claude/CLAUDE.md.jinja2` from commit `62b6d8f`:
   - `investigation` frontmatter reference in "Chunk Frontmatter References" section
   - "Proposed Chunks" section explaining the `proposed_chunks` frontmatter pattern
   - Correct prose linking "Proposed Chunks" to `proposed_chunks` frontmatter (not just "Chunks")
   - Investigation lifecycle details (status table, when to use)
   - "What Counts as Code" section (clarifying templates are code)
   - Development section (uv run instructions for ve developers)

3. **Re-render produces correct output**: Running template render produces `.claude/commands/chunk-plan.md` and `CLAUDE.md` with the restored content

## Git History References

Use these commits to extract the correct content:

- **`8a29e62`** - Contains cluster prefix suggestion for chunk-plan.md (`.claude/commands/chunk-plan.md` diff)
- **`62b6d8f`** - Contains proposed_chunks standardization for CLAUDE.md (`CLAUDE.md` diff)

Run `git show <commit> -- <file>` to extract the content that needs to be restored to the source templates.