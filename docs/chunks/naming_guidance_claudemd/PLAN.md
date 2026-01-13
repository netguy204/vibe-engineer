<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a documentation-only change to the CLAUDE.md Jinja2 template. The goal is to add passive guidance for chunk naming conventions that agents will see when reading CLAUDE.md, without requiring skill invocation.

The content distills findings from the `alphabetical_chunk_grouping` investigation:
- Domain-concept prefixes ("ordering_", "taskdir_", "template_") produce semantically coherent mid-sized clusters
- Artifact-type prefixes ("chunk_", "subsystem_", "investigation_") create superclusters that don't aid navigation
- Action-verb prefixes ("fix_", "update_", "add_") similarly fail to create useful groupings
- The key question is "What initiative does this chunk advance?" rather than "What artifact type is this?"

The section should be concise (3-5 sentences per success criteria) and placed in the Chunks section where naming decisions are relevant.

## Subsystem Considerations

No subsystems are directly relevant. This is a documentation-only change to the CLAUDE.md template. However, the content relates to work in the `alphabetical_chunk_grouping` investigation and sibling chunks (`similarity_prefix_suggest`, `cluster_seed_naming`, `cluster_rename`).

## Sequence

### Step 1: Identify insertion point in CLAUDE.md template

The new section should be placed within the "Chunks" section of `src/templates/claude/CLAUDE.md.jinja2`, after the "Chunk Lifecycle" subsection but before "Chunk Frontmatter References". This placement ensures operators see naming guidance at the point where chunk naming is most relevant—immediately after learning what chunks are and how they're created.

**Target location**: After the "Chunk Lifecycle" section (around line 35-40), before "Chunk Frontmatter References".

### Step 2: Add "Chunk Naming Conventions" subsection to CLAUDE.md template

Edit `src/templates/claude/CLAUDE.md.jinja2` to add a new "Chunk Naming Conventions" subsection.

**Content to add** (3-5 sentences as required):

```markdown
### Chunk Naming Conventions

Name chunks by the **initiative** they advance, not the artifact type or action verb. Ask: "What multi-chunk effort does this chunk belong to?" Good prefixes are domain concepts that group related work: `ordering_`, `taskdir_`, `template_`. Avoid generic prefixes that create superclusters: `chunk_`, `fix_`, `cli_`, `api_`, `util_`. See `docs/investigations/alphabetical_chunk_grouping/OVERVIEW.md` for detailed rationale.
```

**Backreference comment**: Add a Jinja comment before the section:
```jinja2
{# Chunk: docs/chunks/naming_guidance_claudemd - Chunk naming convention guidance #}
```

### Step 3: Regenerate CLAUDE.md and verify

Run `uv run ve init` to regenerate CLAUDE.md from the template.

**Verification checklist**:
- The command succeeds without errors
- CLAUDE.md contains the new "Chunk Naming Conventions" subsection
- The section appears within the "Chunks" section, after "Chunk Lifecycle"
- The content is concise (3-5 sentences)
- The investigation reference path is correct
- Template renders correctly for both ve source repo (with ve_config) and consumer projects (without ve_config)

## Dependencies

No dependencies. The CLAUDE.md template already exists and is functional. The referenced investigation (`alphabetical_chunk_grouping`) is in SOLVED status with the detailed rationale available.

## Risks and Open Questions

- **Placement**: The plan places the section after "Chunk Lifecycle" within the Chunks section. An alternative would be a standalone section later in the document. The current approach is more discoverable since it's near where chunk creation is discussed.

- **Reference path format**: The reference to the investigation uses a project-root-relative path per DEC-004. This is consistent with other documentation references in CLAUDE.md.

- **Length constraint**: The success criteria specifies 3-5 sentences. The proposed content fits this constraint while covering the key points: initiative-based naming, good examples, bad examples, and a reference for details.

## Deviations

_To be populated during implementation._
