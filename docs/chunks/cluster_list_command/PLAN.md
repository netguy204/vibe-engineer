# Implementation Plan

## Approach

The `ve cluster list` command will provide diagnostic visibility into how chunks are grouped by their alphabetical prefix clusters. This supports the investigation's finding that mid-sized clusters (3-8 chunks) provide navigational value, while singletons and superclusters are indicators that naming hygiene may need attention.

### Step 1: Core Cluster Detection Logic

Create module `src/cluster_analysis.py` containing:

**Function: `get_chunk_clusters(project_dir: Path) -> dict[str, list[str]]`**
- Get all chunks via `Chunks(project_dir).enumerate_chunks()`
- For each chunk, extract the prefix (first underscore-delimited word using `extract_short_name()` then splitting on `_`)
- Group chunks by prefix into a dict mapping prefix -> list of chunk names
- Return the mapping sorted by prefix alphabetically

**Function: `categorize_clusters(clusters: dict[str, list[str]]) -> ClusterCategories`**
- Take the cluster mapping and categorize by size:
  - `singletons`: clusters with size 1 (no navigational benefit)
  - `small`: clusters with size 2 (minimal benefit)
  - `healthy`: clusters with size 3-8 (optimal for navigation)
  - `superclusters`: clusters with size >8 (noise, needs attention)
- Return a `ClusterCategories` dataclass with these categorized clusters

**Dataclass: `ClusterCategories`**
- `singletons: dict[str, list[str]]`
- `small: dict[str, list[str]]`
- `healthy: dict[str, list[str]]`
- `superclusters: dict[str, list[str]]`
- Helper properties: `total_clusters`, `total_chunks`, `singleton_count`, `supercluster_count`

### Step 2: Merge Suggestion Logic (Optional Feature)

**Function: `suggest_singleton_merges(project_dir: Path, clusters: dict[str, list[str]], threshold: float = 0.4) -> list[MergeSuggestion]`**
- For each singleton cluster, use TF-IDF pairwise similarity (reuse from `suggest_prefix` in `chunks.py`)
- Find semantically similar chunks in other clusters
- Return suggestions where a singleton might fit better with an existing cluster

**Dataclass: `MergeSuggestion`**
- `singleton_chunk: str` - the singleton chunk name
- `target_cluster: str` - the cluster prefix it could merge into
- `similar_chunks: list[tuple[str, float]]` - chunks in target cluster with similarity scores
- `suggested_new_name: str` - what the chunk would be renamed to

This reuses the TF-IDF infrastructure already built for `suggest_prefix` in `chunks.py`, specifically:
- `extract_goal_text()` - extracts text from GOAL.md
- `get_chunk_prefix()` - gets prefix from chunk name
- TfidfVectorizer with same parameters (stop_words="english", max_features=500, ngram_range=(1,2))

### Step 3: CLI Command Implementation

Add to `src/ve.py` under the `chunk` command group:

```python
@chunk.command("cluster-list")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--suggest-merges", is_flag=True, help="Suggest singleton merges based on semantic similarity")
def cluster_list(project_dir, suggest_merges):
    """List prefix clusters and identify singletons/superclusters."""
```

**Default output format:**
```
## Superclusters (>8 chunks) - needs attention
  chunk_* (14 chunks): chunk_create, chunk_list, chunk_validate, ...

## Healthy clusters (3-8 chunks)
  ordering_* (6 chunks): artifact_index, causal_ordering, created_after_field, ...
  template_* (5 chunks): canonical_template, migrate_chunks_template, ...

## Small clusters (2 chunks)
  investigation_* (2 chunks): investigation_commands, investigation_template

## Singletons (no grouping benefit)
  27 singletons: agent_discovery_command, bidirectional_refs, ...

Summary: 47 chunks in 32 clusters
  - 1 supercluster (14 chunks) ⚠️
  - 3 healthy clusters (16 chunks)
  - 2 small clusters (4 chunks)
  - 27 singletons
```

**With `--suggest-merges` flag:**
```
## Merge suggestions for singletons

  agent_discovery_command → subsystem_* cluster
    Similar to: subsystem_cli_scaffolding (0.55), subsystem_template (0.52)
    Suggested rename: subsystem_agent_discovery

  bidirectional_refs → crossref_* cluster
    Similar to: symbolic_code_refs (0.48), update_crossref_format (0.45)
    Suggested rename: crossref_bidirectional
```

### Step 4: Output Formatting

**Function: `format_cluster_output(categories: ClusterCategories, suggest_merges: list[MergeSuggestion] | None = None) -> str`**
- Format superclusters with warning indicator
- Format healthy clusters showing count and abbreviated member list
- Format singletons as a compact list
- Add summary statistics
- If merge suggestions provided, format them with similarity scores

### Step 5: Tests

Create `tests/test_cluster_list.py` with test cases:

1. **Cluster detection tests:**
   - `test_groups_chunks_by_prefix` - verifies basic prefix grouping
   - `test_handles_legacy_numbered_format` - {NNNN}-{short_name} chunks
   - `test_handles_no_underscore_chunks` - chunks without underscore become their own singleton
   - `test_empty_chunks_directory` - graceful handling of no chunks

2. **Categorization tests:**
   - `test_categorizes_singletons` - size 1 clusters
   - `test_categorizes_small_clusters` - size 2 clusters
   - `test_categorizes_healthy_clusters` - size 3-8 clusters
   - `test_categorizes_superclusters` - size >8 clusters

3. **CLI tests:**
   - `test_cluster_list_shows_all_categories` - default output
   - `test_cluster_list_with_suggest_merges` - merge suggestions
   - `test_cluster_list_no_chunks` - empty state handling
   - `test_cluster_list_output_format` - verify expected format

4. **Merge suggestion tests:**
   - `test_suggest_merges_finds_similar_singletons` - finds semantic matches
   - `test_suggest_merges_respects_threshold` - only suggests above threshold
   - `test_suggest_merges_skips_non_singletons` - only processes singletons

## Code Paths

Files to create:
- `src/cluster_analysis.py` - Core cluster detection and analysis logic

Files to modify:
- `src/ve.py` - Add `cluster-list` command to chunk group

Files to create for testing:
- `tests/test_cluster_list.py` - Test coverage for cluster analysis

## Dependencies

- Reuses `Chunks` class from `src/chunks.py` for chunk enumeration
- Reuses `extract_short_name()` from `src/models.py` for handling legacy format
- Reuses TF-IDF infrastructure pattern from `suggest_prefix()` in `src/chunks.py`
- Follows CLI patterns from existing commands like `cluster-rename`

## Notes

- The command is named `cluster-list` (hyphenated) to match `cluster-rename` convention
- Supercluster threshold of 8 aligns with investigation findings on optimal cluster sizes
- Merge suggestions are opt-in via flag since they require TF-IDF computation which is heavier
- Output format prioritizes superclusters first since they need the most attention
- Singletons are compressed to avoid overwhelming output when there are many
