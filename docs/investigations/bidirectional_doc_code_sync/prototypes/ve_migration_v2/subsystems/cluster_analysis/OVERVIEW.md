---
status: DOCUMENTED
# MIGRATION NOTE: This subsystem was synthesized from chunks.
# Review all [NEEDS_HUMAN] and [CONFLICT] sections before finalizing.
# Confidence: 80% synthesized, 10% inferred, 10% needs human input
chunks:
  - name: cluster_list_command
    relationship: implements
  - name: cluster_rename
    relationship: implements
  - name: cluster_prefix_suggest
    relationship: implements
  - name: cluster_seed_naming
    relationship: implements
  - name: cluster_naming_guidance
    relationship: implements
  - name: cluster_subsystem_prompt
    relationship: implements
code_references:
  - ref: src/cluster_analysis.py#ClusterInfo
    implements: Cluster metadata dataclass
    compliance: COMPLIANT
  - ref: src/cluster_analysis.py#analyze_clusters
    implements: Core cluster analysis function
    compliance: COMPLIANT
  - ref: src/cluster_analysis.py#CLUSTER_CATEGORIES
    implements: Cluster size thresholds (tiny/small/medium/large/huge)
    compliance: COMPLIANT
  - ref: src/cluster_analysis.py#ClusterWarning
    implements: Cluster size warning dataclass
    compliance: COMPLIANT
  - ref: src/cluster_analysis.py#check_cluster_sizes
    implements: Cluster size check against thresholds
    compliance: COMPLIANT
  - ref: src/cluster_analysis.py#format_cluster_warning
    implements: Warning message formatting
    compliance: COMPLIANT
  - ref: src/cluster_rename.py
    implements: Cluster rename operations
    compliance: COMPLIANT
  - ref: src/chunks.py#suggest_prefix
    implements: TF-IDF based prefix suggestion
    compliance: COMPLIANT
  - ref: src/chunks.py#SuggestPrefixResult
    implements: Prefix suggestion result dataclass
    compliance: COMPLIANT
proposed_chunks: []
created_after:
  - workflow_artifacts
---

# cluster_analysis

## Intent

<!-- SYNTHESIS CONFIDENCE: HIGH -->

[SYNTHESIZED] Help users understand and manage chunk naming patterns, suggesting prefixes for cohesion and warning when clusters become too large.

From cluster_list_command chunk: "Provide operators visibility into how chunks cluster by naming prefix, identifying patterns that might indicate emergent subsystems."

From cluster_subsystem_prompt chunk: "Warn operators when a cluster exceeds the threshold, suggesting they consider documenting it as a subsystem."

[NEEDS_HUMAN] Business context and strategic importance:
<!-- Why does this subsystem matter to the organization? -->
<!-- Consider: How naming patterns affect codebase navigability and AI agent understanding -->

## Scope

### In Scope

<!-- SYNTHESIS CONFIDENCE: HIGH -->

[SYNTHESIZED] Based on chunk code_references and success criteria:
- **Cluster listing**: `ve chunk cluster list` command showing chunks grouped by prefix
- **Cluster renaming**: `ve chunk cluster rename` command for batch prefix changes
- **Prefix suggestion**: TF-IDF similarity-based prefix recommendation for new chunks
- **Size warnings**: Configurable thresholds for cluster size warnings
- **Subsystem prompting**: Suggest subsystem creation when clusters grow large

[INFERRED] From code structure:
- **Cluster categorization**: tiny (<3), small (3-5), medium (6-10), large (11-20), huge (>20)
- **Similarity scoring**: Cosine similarity between chunk GOAL.md content

### Out of Scope

<!-- SYNTHESIS CONFIDENCE: MEDIUM -->

[NEEDS_HUMAN] What explicitly does NOT belong here:
- [INFERRED] Chunk creation (belongs to workflow_artifacts)
- [INFERRED] Subsystem creation (belongs to workflow_artifacts)
- [INFERRED] Chunk validation (belongs to workflow_artifacts)

## Invariants

<!-- SYNTHESIS CONFIDENCE: HIGH -->

[SYNTHESIZED] From chunk success criteria:

1. **Clusters identified by naming prefix**
   - Prefix extracted by splitting on underscore and taking first segment
   - Single-word chunks form their own "cluster" of one
   - Source: cluster_list_command

2. **Large clusters (>threshold) trigger subsystem prompts**
   - Default threshold configurable in .ve-config.yaml
   - Warning displayed on chunk creation and cluster list
   - Source: cluster_subsystem_prompt

3. **Prefix suggestions use TF-IDF similarity**
   - Extract text from GOAL.md files
   - Compute cosine similarity with existing clusters
   - Return top N most similar clusters with scores
   - Source: cluster_prefix_suggest

4. **Cluster rename is atomic**
   - All chunks with matching prefix renamed together
   - Git operations (add, commit) performed atomically
   - Source: cluster_rename

[NEEDS_HUMAN] Implicit invariants not in chunks:
<!-- What rules exist in code but weren't documented? -->
- Cluster categories (tiny/small/medium/large/huge) have fixed size ranges

## Code References

<!-- SYNTHESIS CONFIDENCE: HIGH -->

[SYNTHESIZED] Consolidated from chunk code_references:

### Cluster Analysis
- `src/cluster_analysis.py#ClusterInfo` - Cluster metadata (name, chunks, category)
- `src/cluster_analysis.py#analyze_clusters` - Core analysis function
- `src/cluster_analysis.py#CLUSTER_CATEGORIES` - Size category thresholds
- `src/cluster_analysis.py#get_cluster_category` - Categorize by size

### Size Warnings
- `src/cluster_analysis.py#ClusterWarning` - Warning dataclass
- `src/cluster_analysis.py#check_cluster_sizes` - Check against threshold
- `src/cluster_analysis.py#format_cluster_warning` - Format warning message

### Prefix Suggestion
- `src/chunks.py#suggest_prefix` - Main suggestion function
- `src/chunks.py#SuggestPrefixResult` - Result dataclass with scores
- `src/chunks.py#_extract_goal_text` - Extract text from GOAL.md
- `src/chunks.py#_get_prefix_from_name` - Extract prefix from chunk name

### Rename Operations
- `src/cluster_rename.py` - Cluster rename command implementation
- `src/cluster_rename.py#rename_cluster` - Core rename logic
- `src/cluster_rename.py#find_chunks_with_prefix` - Find matching chunks

[NEEDS_HUMAN] Validate these references are current:
<!-- Some chunk references may be stale -->

## Deviations

<!-- SYNTHESIS CONFIDENCE: LOW -->

[NEEDS_HUMAN] Known deviations from ideal:
<!-- Chunks rarely document what's wrong -->
- [INFERRED] External artifacts not dereferenced for prefix suggestion in single-repo mode (see workflow_artifacts deviation)

## Chunk Provenance

This subsystem was synthesized from the following chunks:

| Chunk | Status | Contribution | Confidence |
|-------|--------|--------------|------------|
| cluster_list_command | ACTIVE | Invariant 1, analysis code refs | HIGH |
| cluster_rename | ACTIVE | Invariant 4, rename code refs | HIGH |
| cluster_prefix_suggest | ACTIVE | Invariant 3, suggestion code refs | HIGH |
| cluster_seed_naming | ACTIVE | Naming conventions | MEDIUM |
| cluster_naming_guidance | ACTIVE | Documentation | MEDIUM |
| cluster_subsystem_prompt | ACTIVE | Invariant 2, warning code refs | HIGH |

## Synthesis Metrics

| Section | Synthesized | Inferred | Needs Human | Conflicts |
|---------|-------------|----------|-------------|-----------|
| Intent | 2 | 0 | 1 | 0 |
| Scope | 5 | 2 | 1 | 0 |
| Invariants | 4 | 0 | 1 | 0 |
| Code References | 11 | 0 | 1 | 0 |
| Deviations | 0 | 1 | 1 | 0 |
| **Total** | **22** | **3** | **5** | **0** |

**Overall Confidence**: 73% (22 synthesized / 30 total items)
