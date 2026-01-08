Update code references in the current chunk and move both the PLAN.md and the GOAL.md to the ACTIVE state.

1. Determine the currently active chunk by running `ve chunk list --latest`. We
   will refer to the directory returned by this command below as <chunk
   directory>

2. Identify where in the code the <chunk directory>/GOAL.md is implemented. The
   code_paths field of this file's metadata and the <chunk directory>/PLAN.md
   file in the chunk directory can help guide your search and git diff may
   provide clues but may be more or less than the true scope of the code
   involved in the change. Take note of the file names and the line ranges for
   semantically meaningful (with respect to the GOAL.md) chunks of code and
   record these chunks in the code_references field in the GOAL.md metadata.
   When we mark a goal as historical, we are saying that there is so much
   semantic drift between what the document set out to achieve and what the code
   base does now, that the document is now only valuable as a historic reference
   point. If it appears that the goal is not represented in the code, STOP AND
   NOTIFY THE OPERATOR. It is likely that this chunk cannot be completed because
   it is not reflected in the code yet. 

3. Extract the sequential ID for the chunk from the prefix number in the chunk
   directory. We will call this <chunk_id> below.

4. Run `ve chunk complete <chunk_id>` to verify that the metadata syntax for the
   GOAL.md file is correct

5. Run `ve chunk overlap <chunk_id>` to find the previous chunks whose
   references and validity may have been impacted by this chunk's changes.

5. In parallel sub-agents run /chunk-resolve-references for each of the returned
   directories. 

6. Report to the operator on updates made to previous chunk metadata or chunks that
   need to be investigated for continuing applicability.