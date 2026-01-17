---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references:
  - ref: src/chunks.py#BackreferenceInfo
    implements: "Dataclass for storing backreference info per file"
  - ref: src/chunks.py#count_backreferences
    implements: "Backreference census - scans source files for chunk/narrative/subsystem refs"
  - ref: src/chunks.py#ConsolidationResult
    implements: "Dataclass for chunk consolidation results"
  - ref: src/chunks.py#ClusterResult
    implements: "Dataclass for chunk clustering results"
  - ref: src/chunks.py#cluster_chunks
    implements: "TF-IDF based chunk clustering using agglomerative clustering"
  - ref: src/chunks.py#consolidate_chunks
    implements: "Consolidates multiple chunks into a narrative with frontmatter updates"
  - ref: src/chunks.py#update_backreferences
    implements: "Replaces chunk backreferences with narrative backreferences in source files"
  - ref: src/ve.py#backrefs
    implements: "CLI command 've chunk backrefs' for backreference census"
  - ref: src/ve.py#cluster
    implements: "CLI command 've chunk cluster' for chunk clustering"
  - ref: src/ve.py#compact
    implements: "CLI command 've narrative compact' for consolidation"
  - ref: src/ve.py#update_refs
    implements: "CLI command 've narrative update-refs' for backreference updates"
  - ref: src/templates/commands/narrative-compact.md.jinja2
    implements: "Slash command template for /narrative-compact workflow"
  - ref: tests/test_narrative_consolidation.py
    implements: "Test suite for consolidation workflow"
narrative: null
investigation: chunk_reference_decay
subsystems: []
friction_entries: []
created_after:
- orch_dashboard
- friction_noninteractive
---

# Chunk Goal

## Minor Goal

Implement a chunk-to-narrative consolidation workflow that groups related chunks into narratives and updates code backreferences. This addresses the "reference decay" problem: code blocks accumulate many chunk backreferences that drip-feed context rather than providing high-value understanding.

The investigation found that:
- Files like src/ve.py have 46+ chunk backreferences spanning 97% of project history
- Old chunk references document WHAT was built, not WHY architecturally
- A synthesized narrative provides ~40 lines of coherent context vs ~400-800 lines across 8 chunk GOALs
- Narratives are superior for PURPOSE understanding; chunks remain valuable for HISTORY

The workflow (possibly `/narrative-compact` or similar) should:
- Identify code blocks with high chunk backreference counts
- Cluster related chunks by theme/code overlap
- Generate a narrative synthesizing those chunks
- Update code backreferences to point to the narrative (while preserving chunk links in the narrative for archaeology)

## Success Criteria

- Command or workflow identifies code files with excessive chunk backreferences (threshold configurable, default ~5+)
- Clusters chunks by theme using code overlap analysis or temporal proximity
- Generates narrative OVERVIEW.md synthesizing the clustered chunks' PURPOSE
- Updates code backreferences from `# Chunk:` to `# Narrative:` format (requires narrative_backreference_support chunk)
- Preserves original chunk references in narrative frontmatter for archaeology
- Integrates with existing CLI patterns
- Depends on narrative_backreference_support chunk for the `# Narrative:` format