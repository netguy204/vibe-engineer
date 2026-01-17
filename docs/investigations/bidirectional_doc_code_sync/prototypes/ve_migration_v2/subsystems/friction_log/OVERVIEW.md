---
status: DOCUMENTED
# MIGRATION NOTE: This subsystem was synthesized from chunks.
# Review all [NEEDS_HUMAN] and [CONFLICT] sections before finalizing.
# Confidence: 75% synthesized, 15% inferred, 10% needs human input
chunks:
  - name: friction_template_and_cli
    relationship: implements
  - name: friction_chunk_workflow
    relationship: implements
  - name: friction_chunk_linking
    relationship: implements
  - name: friction_claude_docs
    relationship: implements
  - name: friction_noninteractive
    relationship: implements
  - name: selective_artifact_friction
    relationship: implements
code_references:
  - ref: src/friction.py#FrictionLog
    implements: Core friction log management class
    compliance: COMPLIANT
  - ref: src/friction.py#parse_friction_entries
    implements: Parse entries from markdown content
    compliance: COMPLIANT
  - ref: src/friction.py#format_friction_entry
    implements: Format entry for markdown output
    compliance: COMPLIANT
  - ref: src/friction.py#get_next_entry_id
    implements: Generate sequential entry ID
    compliance: COMPLIANT
  - ref: src/friction.py#get_external_friction_sources
    implements: Load external friction sources from frontmatter
    compliance: COMPLIANT
  - ref: src/models.py#FrictionFrontmatter
    implements: Friction log frontmatter schema
    compliance: COMPLIANT
  - ref: src/models.py#FrictionTheme
    implements: Friction theme schema
    compliance: COMPLIANT
  - ref: src/models.py#FrictionProposedChunk
    implements: Proposed chunk with addresses field
    compliance: COMPLIANT
  - ref: src/models.py#FrictionEntryReference
    implements: Chunk reference to friction entry
    compliance: COMPLIANT
  - ref: src/models.py#ExternalFrictionSource
    implements: External friction source reference
    compliance: COMPLIANT
proposed_chunks: []
created_after:
  - workflow_artifacts
---

# friction_log

## Intent

<!-- SYNTHESIS CONFIDENCE: HIGH -->

[SYNTHESIZED] Capture and track pain points encountered during project use, enabling pattern recognition and improvement prioritization.

From friction_template_and_cli chunk: "Provide a friction log artifact type that accumulates pain points over time, with each entry tagged by theme and date, enabling organic pattern discovery."

From friction_chunk_workflow chunk: "Establish the workflow for friction log lifecycle: entries accumulate, patterns emerge from theme clustering, proposed chunks address clusters, chunks link back via friction_entries."

[NEEDS_HUMAN] Business context and strategic importance:
<!-- Why does this subsystem matter to the organization? -->
<!-- Consider: How friction logs help prioritize tooling improvements and track recurring issues -->

## Scope

### In Scope

<!-- SYNTHESIS CONFIDENCE: HIGH -->

[SYNTHESIZED] Based on chunk code_references and success criteria:
- **Entry creation**: `ve friction log` command for adding new friction entries
- **Entry format**: Sequential IDs (F001, F002), date, theme, title, description
- **Theme management**: Organic theme emergence from entry clustering
- **Proposed chunks**: `proposed_chunks` in frontmatter with `addresses` arrays linking to entry IDs
- **Status derivation**: OPEN/ADDRESSED/RESOLVED derived from chunk references, not stored
- **Friction-chunk linking**: `friction_entries` field in chunk frontmatter for traceability
- **Task-aware friction**: Cross-repo friction logging with `--projects` flag
- **External friction sources**: Track friction from external repos in project context

[INFERRED] From code structure:
- **Analysis command**: Pattern analysis across themes
- **List command**: Display friction entries with status

### Out of Scope

<!-- SYNTHESIS CONFIDENCE: MEDIUM -->

[NEEDS_HUMAN] What explicitly does NOT belong here:
- [INFERRED] Chunk creation (belongs to workflow_artifacts)
- [INFERRED] External reference management (belongs to cross_repo_operations)
- [INFERRED] Template rendering (belongs to template_system)

## Invariants

<!-- SYNTHESIS CONFIDENCE: HIGH -->

[SYNTHESIZED] From chunk success criteria:

1. **Entry IDs are F{digits} format, sequential**
   - Pattern: F followed by digits (F001, F002, F123)
   - IDs are never reused, even if entries are removed
   - `get_next_entry_id()` generates next sequential ID
   - Source: friction_template_and_cli

2. **Entry status is derived, not stored**
   - OPEN: Entry ID not in any `proposed_chunks.addresses`
   - ADDRESSED: Entry ID appears in a proposed chunk
   - RESOLVED: Entry addressed by a chunk that reached ACTIVE status
   - Source: friction_chunk_workflow

3. **Themes emerge organically from entries**
   - No predefined theme list; themes added as entries accumulate
   - Existing themes displayed to agents for clustering
   - Source: friction_template_and_cli

4. **Proposed chunks can address multiple entries**
   - `FrictionProposedChunk.addresses` is an array of entry IDs
   - Enables batching related friction points
   - Source: friction_template_and_cli

5. **Chunks reference friction entries via friction_entries field**
   - `ChunkFrontmatter.friction_entries` lists `FrictionEntryReference` objects
   - Each reference has `entry_id` and optional `scope` (full/partial)
   - Provides "why did we do this work?" traceability
   - Source: friction_chunk_linking

6. **Entry format must include date, theme_id, and title**
   - Markdown format: `### FXXX: YYYY-MM-DD [theme-id] Title`
   - Description follows as paragraph text
   - Source: friction_template_and_cli

[NEEDS_HUMAN] Implicit invariants not in chunks:
<!-- What rules exist in code but weren't documented? -->
- Friction log file is always `docs/trunk/FRICTION.md`

## Code References

<!-- SYNTHESIS CONFIDENCE: HIGH -->

[SYNTHESIZED] Consolidated from chunk code_references:

### Core Logic
- `src/friction.py#FrictionLog` - Main friction log management class
- `src/friction.py#parse_friction_entries` - Parse entries from markdown
- `src/friction.py#format_friction_entry` - Format entry for output
- `src/friction.py#get_next_entry_id` - Sequential ID generation
- `src/friction.py#add_friction_entry` - Add new entry to log

### Schema Models
- `src/models.py#FrictionFrontmatter` - Log frontmatter schema
- `src/models.py#FrictionTheme` - Theme definition model
- `src/models.py#FrictionProposedChunk` - Proposed chunk with addresses
- `src/models.py#FrictionEntryReference` - Chunk-to-entry reference
- `src/models.py#FRICTION_ENTRY_ID_PATTERN` - ID validation regex

### Task-Aware Operations
- `src/task_utils.py#create_task_friction_entry` - Cross-repo friction logging
- `src/task_utils.py#add_external_friction_source` - Add external source reference
- `src/models.py#ExternalFrictionSource` - External source schema
- `src/friction.py#get_external_friction_sources` - Load external sources

[NEEDS_HUMAN] Validate these references are current:
<!-- Some chunk references may be stale -->

## Deviations

<!-- SYNTHESIS CONFIDENCE: LOW -->

[NEEDS_HUMAN] Known deviations from ideal:
<!-- Chunks rarely document what's wrong -->
- [INFERRED] No automatic status derivation implemented yet (status is conceptual)
- [INFERRED] Analysis command may need more sophisticated pattern detection

## Chunk Provenance

This subsystem was synthesized from the following chunks:

| Chunk | Status | Contribution | Confidence |
|-------|--------|--------------|------------|
| friction_template_and_cli | ACTIVE | Invariants 1, 3, 4, 6, core code refs | HIGH |
| friction_chunk_workflow | ACTIVE | Invariant 2, workflow documentation | HIGH |
| friction_chunk_linking | ACTIVE | Invariant 5, FrictionEntryReference | HIGH |
| friction_claude_docs | ACTIVE | CLAUDE.md documentation | MEDIUM |
| friction_noninteractive | ACTIVE | Non-interactive mode support | MEDIUM |
| selective_artifact_friction | ACTIVE | Task-aware friction, --projects flag | HIGH |

## Synthesis Metrics

| Section | Synthesized | Inferred | Needs Human | Conflicts |
|---------|-------------|----------|-------------|-----------|
| Intent | 2 | 0 | 1 | 0 |
| Scope | 8 | 2 | 1 | 0 |
| Invariants | 6 | 0 | 1 | 0 |
| Code References | 14 | 0 | 1 | 0 |
| Deviations | 0 | 2 | 1 | 0 |
| **Total** | **30** | **4** | **5** | **0** |

**Overall Confidence**: 77% (30 synthesized / 39 total items)
