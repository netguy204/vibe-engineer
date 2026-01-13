---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cluster_analysis.py
- src/ve.py
- tests/test_cluster_list.py
code_references:
  - ref: src/cluster_analysis.py#ClusterCategories
    implements: "Cluster categorization dataclass with size-based buckets"
  - ref: src/cluster_analysis.py#get_chunk_clusters
    implements: "Group chunks by first underscore-delimited word prefix"
  - ref: src/cluster_analysis.py#categorize_clusters
    implements: "Categorize clusters into singletons/small/healthy/superclusters"
  - ref: src/cluster_analysis.py#MergeSuggestion
    implements: "Dataclass for singleton merge suggestions"
  - ref: src/cluster_analysis.py#suggest_singleton_merges
    implements: "TF-IDF based semantic similarity for singleton merge suggestions"
  - ref: src/cluster_analysis.py#format_cluster_output
    implements: "Terminal output formatting for cluster analysis"
  - ref: src/ve.py#cluster_list_cmd
    implements: "CLI command for ve chunk cluster-list"
  - ref: tests/test_cluster_list.py
    implements: "Test coverage for cluster analysis functionality"
narrative: null
investigation: alphabetical_chunk_grouping
subsystems: []
friction_entries: []
created_after:
- orch_dashboard
- friction_noninteractive
---

# Chunk Goal

## Minor Goal

Implement `ve cluster list` command to show current prefix clusters, their sizes, and members. The command will help operators identify when chunk naming has drifted into problematic patterns—specifically highlighting singletons (chunks that don't group with anything, providing no navigational benefit) and superclusters (>8 members, where grouping becomes noise rather than navigation aid).

This diagnostic tool supports the alphabetical grouping investigation's finding that mid-sized clusters (3-8 chunks) provide navigational value in the filesystem view. By making cluster distribution visible, operators can identify when janitorial renaming is needed.

## Success Criteria

- `ve cluster list` groups chunks by first underscore-delimited word prefix
- Output shows each cluster with its size and member chunks
- Singletons (size 1) are visually distinguished or grouped separately
- Superclusters (>8 members) are highlighted as potentially needing attention
- Optional `--suggest-merges` flag identifies semantically similar singletons that could be renamed into existing clusters (using TF-IDF pairwise similarity from the investigation prototype)
- Command integrates with existing CLI structure and follows established patterns
- Tests cover cluster detection, size categorization, and output formatting

