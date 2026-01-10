---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models.py
- src/narratives.py
- src/chunks.py
- src/ve.py
- src/templates/narrative/OVERVIEW.md.jinja2
- src/templates/subsystem/OVERVIEW.md.jinja2
- docs/narratives/0001-cross_repo_chunks/OVERVIEW.md
- docs/narratives/0002-subsystem_documentation/OVERVIEW.md
- docs/narratives/0003-investigations/OVERVIEW.md
- docs/subsystems/0001-template_system/OVERVIEW.md
- CLAUDE.md
- tests/test_chunk_list_proposed.py
- tests/test_narratives.py
code_references:
- ref: src/models.py#ProposedChunk
  implements: Shared Pydantic model for {prompt, chunk_directory} structure
- ref: src/models.py#NarrativeStatus
  implements: Narrative lifecycle enum (DRAFTING, ACTIVE, COMPLETED)
- ref: src/models.py#NarrativeFrontmatter
  implements: Narrative frontmatter schema with proposed_chunks field
- ref: src/models.py#SubsystemFrontmatter
  implements: Extended subsystem frontmatter to include proposed_chunks
- ref: src/models.py#InvestigationFrontmatter
  implements: Updated investigation frontmatter to use ProposedChunk model
- ref: src/narratives.py#Narratives::parse_narrative_frontmatter
  implements: Parse and validate narrative OVERVIEW.md frontmatter
- ref: src/chunks.py#Chunks::list_proposed_chunks
  implements: Collect proposed chunks across investigations, narratives, and subsystems
- ref: src/ve.py#list_proposed_chunks
  implements: CLI command 've chunk list-proposed'
- ref: src/templates/narrative/OVERVIEW.md.jinja2
  implements: Narrative template with proposed_chunks frontmatter
- ref: src/templates/subsystem/OVERVIEW.md.jinja2
  implements: Subsystem template with proposed_chunks frontmatter
- ref: tests/test_chunk_list_proposed.py
  implements: Tests for list-proposed command and logic
- ref: tests/test_narratives.py#TestNarrativeFrontmatterParsing
  implements: Tests for narrative frontmatter parsing
narrative: null
subsystems:
- subsystem_id: template_system
  relationship: uses
created_after:
- code_to_docs_backrefs
---

# Chunk Goal

## Minor Goal

Standardize how proposed chunks are tracked across all artifact types (narratives, subsystems, and investigations) by migrating to a consistent `proposed_chunks` frontmatter format. This enables the set of proposed-but-not-yet-created chunks to be computable data, allowing new CLI commands to list pending work across the entire system.

Currently, investigations use a `proposed_chunks` array in frontmatter with `{prompt, chunk_directory}` entries. Narratives and subsystems track proposed work differently:
- Narratives have a `chunks` array, but this name doesn't convey that the chunks may not exist yet
- Subsystems describe proposed consolidation work in prose (the "Consolidation Chunks" section) rather than structured frontmatter

This chunk unifies these approaches by standardizing on `proposed_chunks` as the field name across all artifact types, clearly signaling that these are proposals that may or may not be implemented.

## Success Criteria

1. **Narrative template updated**:
   - Rename `chunks` to `proposed_chunks` in `src/templates/narrative/OVERVIEW.md.jinja2` frontmatter
   - Use consistent `{prompt, chunk_directory}` format matching investigations
   - Update template comments to reflect the new naming

2. **Subsystem template updated**:
   - Add `proposed_chunks` array in `src/templates/subsystem/OVERVIEW.md.jinja2` frontmatter for consolidation work
   - Keep existing `chunks` array for tracking already-created chunk relationships (implements/uses)
   - Migrate the prose "Consolidation Chunks" section guidance to reference the frontmatter array

3. **CLI command added**:
   - `ve chunk list-proposed` (or similar) lists all proposed chunks across investigations, narratives, and subsystems
   - Filters to entries where `chunk_directory` is null/empty (not yet created)
   - Shows source artifact (which investigation/narrative/subsystem proposed it)

4. **Existing artifacts migrated**:
   - Any existing narrative documents have `chunks` renamed to `proposed_chunks`
   - Any existing subsystem documents with proposed consolidation work in prose are migrated to the frontmatter array

5. **Documentation updated**:
   - CLAUDE.md explains the `proposed_chunks` pattern as a cross-cutting concept
   - Documents the new `ve chunk list-proposed` command