<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add a cluster size detection feature that warns operators when creating or renaming chunks that would expand a prefix cluster beyond a configurable threshold. This proactively surfaces potential subsystem candidates before bug accumulation reveals complexity.

The implementation follows the existing cluster analysis patterns in `src/cluster_analysis.py` and integrates with:
1. The chunk creation flow in `src/ve.py` (`create` command)
2. The prefix suggestion already used in `/chunk-plan` (which may trigger a rename)

Key design decisions:
- **Non-blocking warnings**: Per success criterion #5, prompts are advisory. The operator can proceed without defining a subsystem.
- **Subsystem awareness**: Skip the prompt if a subsystem exists for this prefix/area (SC #6).
- **Configurable threshold**: Default to 5 chunks, configurable in `.ve-config.yaml` (SC #4).
- **Dual detection points**: Check at create time and after potential rename during `/chunk-plan` (SC #1, #2).

This follows DEC-005 (commands don't prescribe git operations) - we only emit warnings, not force any workflow.

## Subsystem Considerations

No existing subsystems are directly relevant to this work. This chunk adds a new feature that uses existing cluster analysis utilities.

## Sequence

### Step 1: Define configuration schema for threshold

Add `cluster_subsystem_threshold` field to the project configuration. The config file is `.ve-config.yaml` at project root.

Location: `src/project.py` (add to any config loading) or create a simple config loader function.

Default value: 5 (as specified in the investigation findings).

### Step 2: Add cluster size check utility function

Create a function in `src/cluster_analysis.py` that:
1. Takes a prefix and project_dir
2. Counts existing chunks with that prefix
3. Checks if a subsystem exists for that prefix
4. Returns a `ClusterSizeWarning` dataclass with:
   - `should_warn: bool`
   - `cluster_size: int`
   - `prefix: str`
   - `has_subsystem: bool`
   - `threshold: int`

The subsystem check can use `Subsystems.find_by_shortname()` to see if a subsystem with that prefix exists.

Location: `src/cluster_analysis.py` (add new function `check_cluster_size`)

### Step 3: Add warning formatting function

Create a function to format the cluster size warning message as specified in SC #4:
- "You're creating the Nth `{prefix}_*` chunk. Consider documenting this as a subsystem with `/subsystem-discover`."

Location: `src/cluster_analysis.py` (add new function `format_cluster_warning`)

### Step 4: Integrate into chunk create command

Modify the `create` command in `src/ve.py` to:
1. After successful creation, extract the prefix from the new chunk name
2. Call the cluster size check function
3. If warning is triggered and no `--yes` flag, emit the warning message

The warning should appear AFTER the "Created docs/chunks/..." success message so the user knows the chunk was created.

Location: `src/ve.py` (modify `create` function, around line 163-169)

### Step 5: Export helper for rename detection point

The `/chunk-plan` command (a slash command template) may rename chunks. After rename, it should re-check cluster size. Since templates can't import Python directly, we need to:
1. Add a new CLI subcommand `ve chunk cluster-check <chunk_name>` that outputs the warning if applicable
2. The slash command template can invoke this after rename

Alternative: Just document that the agent should manually check using `ve chunk cluster-list` after rename. This is simpler and the agent already runs `ve chunk suggest-prefix` which shows similar chunks.

Decision: Go with option 2 (documentation-based) for simplicity. The agent workflow already includes `ve chunk suggest-prefix` output which shows the cluster. Adding explicit guidance in the `/chunk-plan` template is sufficient.

### Step 6: Write tests for cluster size check

Create tests in `tests/test_cluster_subsystem_prompt.py`:

1. **test_check_cluster_size_below_threshold**: Creating 4th chunk in a cluster doesn't trigger warning
2. **test_check_cluster_size_at_threshold**: Creating 5th chunk triggers warning
3. **test_check_cluster_size_with_existing_subsystem**: No warning if subsystem exists for prefix
4. **test_check_cluster_size_configurable_threshold**: Custom threshold in config is respected
5. **test_cli_create_emits_warning**: Integration test that `ve chunk create` shows warning when threshold exceeded

### Step 7: Update chunk-plan template with rename guidance

Add guidance to the `/chunk-plan` template noting that after rename, the operator should consider subsystem documentation if the cluster is growing large.

Location: `src/templates/commands/chunk-plan.md.jinja2`

## Dependencies

No external dependencies. All required functionality exists:
- Cluster prefix extraction: `get_chunk_prefix()` in `src/chunks.py`
- Cluster analysis: `get_chunk_clusters()` in `src/cluster_analysis.py`
- Subsystem lookup: `Subsystems.find_by_shortname()` in `src/subsystems.py`

## Risks and Open Questions

1. **Threshold value**: Default of 5 is based on investigation findings about the orch_* cluster (20 chunks, 55% bug rate). A cluster of 5-6 is arguably still manageable. Consider if 5 is too aggressive - operator feedback will inform future adjustment.

2. **Subsystem matching heuristics**: Current plan checks if a subsystem with exact prefix name exists. A cluster like `auth_*` would need subsystem `auth`. This may miss subsystems with different naming (e.g., `authentication` subsystem for `auth_*` chunks). For v1, exact match is acceptable; can be enhanced later.

3. **False positives**: Large clusters aren't always bad - some domains naturally have many aspects (e.g., `orch_*` for orchestrator). The non-blocking nature mitigates this - operator can dismiss.

4. **Config file location**: Using `.ve-config.yaml` which already exists for `is_ve_source_repo`. Need to ensure config loading handles missing file gracefully.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->