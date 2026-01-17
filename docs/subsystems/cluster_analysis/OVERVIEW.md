---
status: DOCUMENTED
proposed_chunks: []
chunks:
- chunk_id: cluster_list_command
  relationship: implements
- chunk_id: cluster_naming_guidance
  relationship: implements
- chunk_id: cluster_prefix_suggest
  relationship: implements
- chunk_id: cluster_rename
  relationship: implements
- chunk_id: cluster_seed_naming
  relationship: implements
- chunk_id: cluster_subsystem_prompt
  relationship: implements
code_references:
- ref: src/cluster_analysis.py#ClusterInfo
  implements: Cluster data model with prefix, chunks, and characteristics
  compliance: COMPLIANT
- ref: src/cluster_analysis.py#analyze_clusters
  implements: Group chunks by alphabetical prefix and analyze characteristics
  compliance: COMPLIANT
- ref: src/cluster_analysis.py#format_cluster_analysis
  implements: Human-readable cluster analysis output
  compliance: COMPLIANT
- ref: src/cluster_rename.py#ClusterRenameResult
  implements: Result dataclass for batch rename operations
  compliance: COMPLIANT
- ref: src/cluster_rename.py#rename_cluster
  implements: Batch rename chunks matching a prefix pattern
  compliance: COMPLIANT
- ref: src/cluster_rename.py#update_backrefs
  implements: Update chunk backreferences in source files
  compliance: COMPLIANT
- ref: src/chunks.py#SuggestPrefixResult
  implements: Result dataclass for prefix suggestion analysis
  compliance: COMPLIANT
- ref: src/chunks.py#extract_goal_text
  implements: Extract text content from GOAL.md for TF-IDF
  compliance: COMPLIANT
- ref: src/chunks.py#get_chunk_prefix
  implements: Get alphabetical prefix from chunk name
  compliance: COMPLIANT
- ref: src/chunks.py#suggest_prefix
  implements: TF-IDF similarity-based prefix suggestion
  compliance: COMPLIANT
- ref: src/ve.py#cluster
  implements: CLI command group for cluster operations
  compliance: COMPLIANT
- ref: src/ve.py#suggest_prefix_cmd
  implements: CLI command for chunk prefix suggestion
  compliance: COMPLIANT
created_after:
- workflow_artifacts
---

# cluster_analysis

## Intent

Help operators name chunks for semantic alphabetical clustering by
analyzing existing prefixes and suggesting names based on content similarity.
Without this subsystem, chunk naming is ad-hoc and navigational structure degrades
as the chunk count grows.

The key insight is that mid-sized semantic clusters (3-8 chunks) with domain-concept
prefixes like `ordering_`, `taskdir_`, and `template_` produce coherent groupings
that aid filesystem navigation.

## Scope

### In Scope

- **Cluster analysis**: Group chunks by prefix, analyze cluster characteristics
- **TF-IDF similarity**: Compute content similarity between chunks
- **Prefix suggestion**: Recommend prefixes based on similar chunks
- **Batch rename**: Rename multiple chunks sharing a prefix
- **Backreference updates**: Update `# Chunk:` comments when renaming
- **Naming guidance**: CLAUDE.md documentation for good naming practices

### Out of Scope

- **Chunk creation**: Uses workflow_artifacts for actual creation
- **Template rendering**: Uses template_system for guidance integration
- **Semantic analysis beyond TF-IDF**: No deep learning or embedding models

## Invariants

### Hard Invariants

1. **TF-IDF similarity threshold ~0.4 for suggestions** - Avoid weak matches that
   would produce noisy suggestions.

2. **Top-k similar chunks must share prefix for suggestion** - Consensus requirement
   prevents suggesting a prefix based on a single similar chunk.

3. **Suggest-prefix runs during chunk planning** - Integrated into `/chunk-plan`
   workflow for timely intervention.

4. **Batch rename preserves git history** - Proper `git mv` operations rather than
   delete + create.

### Soft Conventions

1. **Prefixes should be domain concepts** - Good: `ordering_`, `taskdir_`. Bad: `fix_`, `add_`.

2. **Target cluster size 3-8 chunks** - Smaller is too fragmented, larger loses coherence.

## Implementation Locations

**Primary files**:
- `src/cluster_analysis.py` - Cluster grouping and analysis
- `src/cluster_rename.py` - Batch rename operations
- `src/chunks.py#suggest_prefix` - TF-IDF similarity computation

**Dependencies**: sklearn for TF-IDF vectorization (added to pyproject.toml)

CLI commands: `ve cluster list`, `ve cluster rename`, `ve chunk suggest-prefix`

## Known Deviations

*None identified during migration synthesis.*

## Chunk Relationships

### Implements

- **cluster_list_command**: Analyze and list chunk clusters by prefix
- **cluster_naming_guidance**: CLAUDE.md documentation for naming conventions
- **cluster_prefix_suggest**: TF-IDF similarity-based prefix suggestion
- **cluster_rename**: Batch rename with backreference updates
- **cluster_seed_naming**: Guidance during chunk creation
- **cluster_subsystem_prompt**: Prompt clusters for subsystem discovery

## Investigation Reference

This subsystem emerged from the `alphabetical_chunk_grouping` investigation which
analyzed the navigational value of prefix-based clustering and prototyped the
TF-IDF similarity approach.
