---
description: Consolidate multiple chunks into a narrative to reduce backreference clutter.
---




<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

This file is rendered from: src/templates/commands/narrative-compact.md.jinja2
Edit the source template, then run `ve init` to regenerate.
-->


## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.


## Instructions

The operator wants to consolidate chunks to reduce backreference clutter:

$ARGUMENTS

---

## Background

Code backreferences (`# Chunk: ...`) accumulate over time, creating "reference decay":
- Files with many chunk refs drip-feed context rather than providing high-value understanding
- Narratives provide PURPOSE context (why code exists architecturally)
- Chunks provide HISTORY context (what work created the code)
- Consolidating chunks into narratives reduces noise while preserving archaeology

## Phase 1: Analyze Current State

1. **Run backreference census** to identify files with excessive chunk references:
   ```
   ve chunk backrefs --threshold 5
   ```

2. **Review the output** to understand which files have the most backreferences

3. **If the operator specified a file or area**, focus on that:
   - Extract chunk IDs from the specified file
   - Note how many unique chunks are referenced

## Phase 2: Identify Related Chunks

If the operator provided specific chunk IDs, skip to Phase 3.

Otherwise, cluster the chunks to find related groups:

1. **Run clustering** on the candidate chunks:
   ```
   ve chunk cluster chunk1 chunk2 chunk3 ...
   ```

   Or cluster all ACTIVE chunks:
   ```
   ve chunk cluster --all
   ```

2. **Present clustering results** to the operator:
   > "I found these clusters of related chunks:
   >
   > **Cluster 1: [theme]** (N chunks)
   > - chunk_a: [brief purpose]
   > - chunk_b: [brief purpose]
   >
   > **Cluster 2: [theme]** (M chunks)
   > - chunk_c: [brief purpose]
   > ...
   >
   > Which cluster(s) would you like to consolidate into a narrative?"

3. **Get confirmation** from the operator on which chunks to consolidate

## Phase 3: Create Consolidated Narrative

1. **Propose a narrative name** based on the common theme:
   - Use underscore separation (e.g., `chunk_lifecycle`, `auth_flow`)
   - Keep under 32 characters
   - Make it descriptive of the PURPOSE, not the history

   > "I propose naming the narrative `[proposed_name]` because it captures [rationale].
   > Does this name work, or would you prefer something different?"

2. **Get operator confirmation** on the name

3. **Run the consolidation command**:
   ```
   ve narrative compact chunk1 chunk2 chunk3 --name narrative_name --description "Purpose description"
   ```

4. **Report the result**:
   > "Created narrative: docs/narratives/[name]
   >
   > Consolidated chunks:
   > - chunk_a
   > - chunk_b
   > - chunk_c
   >
   > Files with backreferences to update:
   > - src/file.py: N refs -> 1 narrative ref"

## Phase 4: Update Code Backreferences

1. **Ask the operator** if they want to update backreferences now:
   > "Would you like to update the code backreferences now?
   > This will replace multiple `# Chunk:` comments with a single `# Narrative:` comment
   > in affected files.
   >
   > Run: `ve narrative update-refs [narrative_name]`"

2. **If the operator agrees**, run the update:
   ```
   ve narrative update-refs narrative_name
   ```

   Or for a dry run first:
   ```
   ve narrative update-refs narrative_name --dry-run
   ```

3. **Report the changes**:
   > "Updated backreferences in N file(s):
   > - src/file.py: replaced X chunk refs with 1 narrative ref
   > - ..."

## Phase 5: Refine Narrative Content (Optional)

If time permits and the operator wants a more complete narrative:

1. **Read the created narrative** at `docs/narratives/[name]/OVERVIEW.md`

2. **Suggest improvements** to the narrative content:
   - Synthesize the PURPOSE from the consolidated chunk goals
   - Update `advances_trunk_goal` with how this work advances the project
   - Populate the "Driving Ambition" section with architectural context

3. **Ask the operator** if they want to refine the content now

---

## Summary

After completing the consolidation, provide a summary:

> "Consolidation complete:
>
> **Created narrative**: docs/narratives/[name]
> **Consolidated**: N chunks
> **Updated**: M source files with backreferences
>
> **Benefits**:
> - Reduced backreference clutter from [X total refs] to [Y narrative refs]
> - Chunks remain linked in narrative frontmatter for archaeology
> - Code now has PURPOSE context via narrative reference
>
> **Next steps**:
> - Review the narrative OVERVIEW.md and refine if needed
> - The consolidated chunks remain as HISTORY references in the narrative"