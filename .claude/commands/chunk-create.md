---
description: Create a new chunk of work and refine its goal.
---




<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

This file is rendered from: src/templates/commands/chunk-create.md.jinja2
Edit the source template, then run `ve init` to regenerate.
-->


## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.


## Instructions

The operator wants to define a piece of work to do the following:

$ARGUMENTS

---

You will help them achieve this by following these steps carefully and
completely in order:

1. Determine a short name for this work. A short name must be less than 32
   characters long. Its words are underscore separated and it is intended to
   provide a terse handle for thinking about what the work represents.
   Substitute this shortname below for the <shortname> placeholder.

   **Naming Guidance:** When naming this chunk, ask yourself: **"What initiative
   does this chunk advance?"** Use that initiative noun as a prefix.

   - **Good prefixes** (initiative nouns): `ordering_`, `taskdir_`, `template_`,
     `validation_`, `crossref_` — these describe the multi-chunk effort being
     advanced
   - **Bad prefixes** (artifact types or generic terms): `chunk_`, `fix_`, `cli_`,
     `api_`, `util_`, `misc_`, `update_` — these create meaningless superclusters

   If this chunk is derived from a narrative or investigation, look there for
   the initiative name. For example, work from `docs/narratives/causal_ordering/`
   might use the `ordering_` prefix.

2. And if the operator has referenced a ticket number, extract it and supply it to
   the command below where the placeholder <ticket number> is referenced. If no
   ticket number is referenced, pass no argument to the command below in the
   <ticket number> placeholder.

3. Run `ve chunk create <shortname> <ticket number>` and note the scratchpad path
   that is returned by the command. The chunk will be created at:
   `~/.vibe/scratchpad/[project-name]/chunks/<shortname>/GOAL.md`

   Substitute this path below for the <chunk directory> placeholder.

4. Refine the contents of <chunk directory>/GOAL.md given the piece of work that
   the user has described, ask them any questions required to complete the
   template and cohesively and thoroughly define the goal of what they're trying
   to accomplish.

   **Note:** Scratchpad chunks have a simpler schema than in-repo chunks. They
   include: `status`, `ticket`, `success_criteria`, and `created_at`. You don't
   need to set code_paths, code_references, or subsystem references.


5. **Check if this is a bug fix.** Look for these signals that indicate bug fix
   work: "bug", "fix", "broken", "error", "issue", "defect", "regression",
   "incorrect", "wrong", "failing".

   If the work is a bug fix, note this in the GOAL.md success criteria so that
   when implementation is complete, the fix can be verified.

6. **Check for existing implementing chunk.** Run `ve chunk list --latest` to
   check if there's already an IMPLEMENTING chunk.

   If there IS an existing IMPLEMENTING chunk, inform the user:
   "Note: Chunk <existing_chunk> is currently being implemented. You can work
   on this new chunk by completing or archiving the current one first, or
   continue working on both concurrently in the scratchpad."

**Note on scratchpad workflow:** Chunks are created in `~/.vibe/scratchpad/`
which is outside the git repository. This keeps personal work notes separate
from the codebase. When you're done with a chunk, use `ve chunk complete` to
archive it.