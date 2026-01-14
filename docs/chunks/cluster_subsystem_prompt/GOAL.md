---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/cluster_analysis.py
  - src/ve.py
  - src/project.py
  - tests/test_cluster_subsystem_prompt.py
  - src/templates/commands/chunk-plan.md.jinja2
code_references:
  - ref: src/cluster_analysis.py#ClusterSizeWarning
    implements: "Dataclass for cluster size warning result"
  - ref: src/cluster_analysis.py#check_cluster_size
    implements: "Cluster size check with subsystem awareness"
  - ref: src/cluster_analysis.py#format_cluster_warning
    implements: "Warning message formatter with ordinal"
  - ref: src/cluster_analysis.py#_ordinal
    implements: "Integer to ordinal string conversion"
  - ref: src/template_system.py#VeConfig
    implements: "cluster_subsystem_threshold configuration field"
  - ref: src/template_system.py#load_ve_config
    implements: "Load cluster_subsystem_threshold from config"
  - ref: src/ve.py#create
    implements: "Cluster size warning at chunk creation"
  - ref: tests/test_cluster_subsystem_prompt.py
    implements: "Tests for cluster size warning feature"
  - ref: src/templates/commands/chunk-plan.md.jinja2
    implements: "Rename guidance mentioning subsystem documentation"
narrative: null
investigation: bug_chunk_semantic_value
subsystems: []
friction_entries: []
created_after:
- background_keyword_semantic
---

# Chunk Goal

## Minor Goal

When `ve chunk create` would expand a cluster (chunks sharing a naming prefix) beyond a configurable threshold, prompt the operator to consider defining a subsystem for that cluster. This surfaces missing subsystem documentation proactively rather than waiting for bug accumulation to reveal architectural complexity.

**Context from investigation:** The `orch_*` cluster has 20 chunks with a 55% bug rate and no subsystem documentation. If this check had existed when the 5th or 6th `orch_*` chunk was created, it could have prompted subsystem definition earlier, potentially preventing many of those bugs by establishing invariants upfront.

## Success Criteria

1. **Cluster detection at create**: `ve chunk create foo_bar` detects the `foo_` prefix and counts existing chunks with that prefix
2. **Cluster detection after rename**: When a chunk is renamed during `/chunk-plan` (e.g., recognizing it belongs to an existing cluster), re-check cluster size against threshold
3. **Threshold check**: If count >= threshold (default 5, configurable in `.ve-config.yaml`), emit a warning/prompt
4. **Prompt content**: Message suggests considering `/subsystem-discover` for the cluster, e.g., "You're creating the 6th `orch_*` chunk. Consider documenting this as a subsystem with `/subsystem-discover`."
5. **Non-blocking**: The prompt is advisory, not a hard block—operator can proceed without defining a subsystem
6. **Subsystem awareness**: If a subsystem already exists for this prefix/area, skip the prompt
7. **Tests**: Unit tests verify threshold detection at both create and rename points