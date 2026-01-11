---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/chunks.py
  - src/ve.py
  - pyproject.toml
  - tests/test_chunk_suggest_prefix.py
  - .claude/commands/chunk-plan.md
code_references:
  - ref: src/chunks.py#SuggestPrefixResult
    implements: "Result dataclass for prefix suggestion analysis"
  - ref: src/chunks.py#extract_goal_text
    implements: "Extract text content from GOAL.md, skipping frontmatter and HTML comments"
  - ref: src/chunks.py#get_chunk_prefix
    implements: "Get alphabetical prefix (first word before underscore)"
  - ref: src/chunks.py#suggest_prefix
    implements: "Main TF-IDF similarity computation and prefix suggestion logic"
  - ref: src/ve.py#suggest_prefix_cmd
    implements: "CLI command ve chunk suggest-prefix"
  - ref: tests/test_chunk_suggest_prefix.py
    implements: "TDD tests for business logic, task context, and CLI"
  - ref: .claude/commands/chunk-plan.md
    implements: "Skill integration to call suggest-prefix during planning"
narrative: null
subsystems: []
created_after:
- artifact_promote
- project_qualified_refs
- task_init_scaffolding
- task_status_command
- task_config_local_paths
---

# Chunk Goal

## Minor Goal

Implement similarity-based prefix suggestion that runs during chunk planning to help operators name chunks for semantic alphabetical clustering.

When an operator runs `/chunk-plan`, the system computes pairwise TF-IDF similarity between the new chunk's GOAL.md and all existing chunks. If the top-k nearest neighbors share a common prefix, the system suggests renaming the chunk to match that prefix (e.g., "This chunk is similar to `taskdir_*` chunks. Consider renaming to `taskdir_<current_name>`").

This enables the navigational value of mid-sized semantic clusters (3-8 chunks) identified in the `alphabetical_chunk_grouping` investigation, where domain-concept prefixes like `ordering_`, `taskdir_`, and `template_` produce coherent groupings that aid filesystem navigation.

## Success Criteria

- A new CLI command `ve chunk suggest-prefix <chunk_dir>` computes TF-IDF similarity between the target chunk's GOAL.md and all other chunks
- The command outputs a suggested prefix if top-k similar chunks (similarity threshold ~0.4) share a common prefix
- Output includes the recommended prefix and lists which similar chunks informed the recommendation
- If no strong similarity exists, no suggestion is made (fall back to characteristic naming prompt in a future chunk)
- sklearn is added as a dependency in pyproject.toml for TF-IDF vectorization
- The `/chunk-plan` skill calls `ve chunk suggest-prefix` before planning begins
- If a suggestion is made, `/chunk-plan` offers to rename the chunk automatically using `mv` if the operator accepts
- The similarity computation follows the approach in `docs/investigations/alphabetical_chunk_grouping/prototypes/embedding_cluster.py`