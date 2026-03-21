---
description: Implement the active chunk.
---


<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

Run `ve init` to regenerate.
-->

## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.


## Instructions

1. Determine the currently active chunk by running `ve chunk list --current`. We
   will refer to the directory returned by this command below as <chunk
   directory>

2. Check if <chunk directory>/REVIEW_FEEDBACK.md exists. If it does:
   - This is a re-implementation cycle after reviewer feedback
   - Read the file carefully — it contains specific issues from the reviewer
   - You MUST address EVERY issue listed. For each issue:
     - **Fix** it in the code, OR
     - **Defer** it with a documented reason (add to PLAN.md Deviations), OR
     - **Dispute** it with evidence for why the current approach is correct
   - Non-functional feedback (documentation, style, naming conventions) is
     equally important as functional feedback — do not skip these
   - After addressing all issues, delete the REVIEW_FEEDBACK.md file to
     signal completion

3. Implement the chunk plan as described in <chunk directory>/PLAN.md

4. When implementation is complete, STOP. Do NOT:
   - Modify the chunk GOAL.md status field
   - Run chunk-complete or any finalization steps
   - Set status to ACTIVE or any other value

   A separate COMPLETE phase handles status transitions and finalization.

5. If you addressed review feedback in step 2, verify you deleted the
   REVIEW_FEEDBACK.md file. This signals to the orchestrator that all
   feedback has been addressed.