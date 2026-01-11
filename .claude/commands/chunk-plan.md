---
description: Create a chunk PLAN.md file containing the technical breakdown for the work in that chunk's GOAL.md file.
---

## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.


## Instructions

1. Determine the currently active chunk by running `ve chunk list --latest`. We
   will refer to the directory returned by this command below as <chunk
   directory>

2. Study <chunk directory>/GOAL.md

3. In light of the broader project objective in docs/trunk/GOAL.md and the
   guiding architecture decisions in docs/trunk/DECISIONS.md and the existing
   codebase: Complete the template in <chunk directory>/PLAN.md with a detailed
   sequence of steps that will achieve the goal. If a chunk is part of a
   narrative (docs/narratives/[goal.frontmatter.narrative]/OVERVIEW.md), it may
   be valuable to read about the broader picture that the goal fits into. 