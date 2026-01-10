---
description: Update code references in the current chunk and move both the PLAN.md and the GOAL.md to the ACTIVE state.
---

## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.

## Instructions

1. Determine the currently active chunk by running `ve chunk list --latest`. We
   will refer to the directory returned by this command below as <chunk
   directory>

2. Identify where in the code the <chunk directory>/GOAL.md is implemented. The
   code_paths field of this file's metadata and the <chunk directory>/PLAN.md
   file in the chunk directory can help guide your search and git diff may
   provide clues but may be more or less than the true scope of the code
   involved in the change.

   Record these locations in the code_references field using **symbolic references**:
   - Format: `{file_path}#{symbol_path}` where symbol_path uses `::` for nesting
   - Examples:
     - `src/chunks.py#Chunks` - reference to a class
     - `src/chunks.py#Chunks::create_chunk` - reference to a method
     - `src/ve.py#validate_short_name` - reference to a standalone function
     - `src/models.py` - reference to an entire module (no symbol)

   Each reference should include:
   - `ref`: The symbolic reference string
   - `implements`: Description of what requirement/goal this code implements

   Example code_references:
   ```yaml
   code_references:
     - ref: src/chunks.py#Chunks::validate_chunk_complete
       implements: "Chunk completion validation logic"
     - ref: src/symbols.py#extract_symbols
       implements: "Python AST-based symbol extraction"
   ```

   When we mark a goal as historical, we are saying that there is so much
   semantic drift between what the document set out to achieve and what the code
   base does now, that the document is now only valuable as a historic reference
   point. If it appears that the goal is not represented in the code, STOP AND
   NOTIFY THE OPERATOR. It is likely that this chunk cannot be completed because
   it is not reflected in the code yet. 

3. Extract the sequential ID for the chunk from the prefix number in the chunk
   directory. We will call this <chunk_id> below.

4. Run `ve chunk validate <chunk_id>` to verify that the metadata syntax for the
   GOAL.md file is correct

5. Run `ve chunk overlap <chunk_id>` to find the previous chunks whose
   references and validity may have been impacted by this chunk's changes.

6. In parallel sub-agents run /chunk-resolve-references for each of the returned
   directories.

7. Report to the operator on updates made to previous chunk metadata or chunks that
   need to be investigated for continuing applicability.

8. Run `ve subsystem overlap <chunk_id>` to find subsystems whose code references
   overlap with this chunk's changes.

9. For each overlapping subsystem returned in step 8:
   a. Read the subsystem's OVERVIEW.md to understand its intent, invariants, and scope
   b. Analyze whether the chunk's changes are **semantic** (affecting behavior/contracts)
      or **non-semantic** (refactoring, comments, formatting)
   c. If non-semantic: no further action needed for this subsystem
   d. If semantic: apply status-based behavior:
      - **STABLE**: Verify changes align with existing patterns. Flag any deviations
        for operator review before proceeding.
      - **DOCUMENTED**: Report the overlap but do NOT expand scope to fix inconsistencies.
        Recommend deferring documentation updates unless this chunk explicitly addresses
        the subsystem.
      - **REFACTORING**: MAY recommend documentation updates or scope expansion for
        consistency. Propose next steps to operator for approval.
      - **DISCOVERING**: Assist with documentation updates as part of ongoing discovery.
      - **DEPRECATED**: Warn if chunk is using deprecated patterns. Suggest alternatives
        documented in the subsystem's OVERVIEW.md.

10. Report subsystem analysis results to operator with concrete next-step
    recommendations based on each overlapping subsystem's status. For semantic changes,
    always get operator confirmation before expanding scope or updating subsystem documentation.

11. Update the chunk status to ACTIVE using the CLI command:
    ```
    ve chunk status <chunk_id> ACTIVE
    ```
    Then remove the comment explaining the structure of the front matter from the
    <chunk directory>/GOAL.md file