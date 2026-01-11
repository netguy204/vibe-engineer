---
description: Implement the active chunk.
---




<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

This file is rendered from: src/templates/commands/chunk-implement.md.jinja2
Edit the source template, then run `ve init` to regenerate.
-->


## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.


## Instructions

1. Determine the currently active chunk by running `ve chunk list --latest`. We
   will refer to the directory returned by this command below as <chunk
   directory>

2. Implement the chunk plan as described in <chunk directory>/PLAN.md