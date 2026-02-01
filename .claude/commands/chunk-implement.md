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

2. Implement the chunk plan as described in <chunk directory>/PLAN.md

3. When implementation is complete, STOP. Do NOT:
   - Modify the chunk GOAL.md status field
   - Run chunk-complete or any finalization steps
   - Set status to ACTIVE or any other value

   A separate COMPLETE phase handles status transitions and finalization.