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

2. And if the operator has referenced a ticket number, extract it and supply it to
   the command below where the placeholder <ticket number> is referenced. If no
   ticket number is referenced, pass no argument to the command below in the
   <ticket number> placeholder.

3. **Determine whether to create a FUTURE or IMPLEMENTING chunk.** Apply these
   checks in priority order:

   **Priority 1: Explicit user intent signals (CHECK THIS FIRST)**

   BEFORE running any commands, scan the user's prompt for explicit timing signals.
   This takes precedence over everything else:

   - **FUTURE signals**: "future", "schedule", "scheduled", "later", "queue",
     "queued", "backlog", "upcoming", "not now", "after current work",
     "next up after", "when we're ready", "eventually", "down the road",
     "for later", "defer", "deferred"
     → If ANY of these are found, use `--future`. Do not proceed to Priority 2.

   - **IMPLEMENTING signals**: "now", "immediately", "start working on",
     "work on this next", "let's do this", "begin", "start this", "dive into",
     "tackle this", "right now", "today"
     → If found, do NOT use `--future` (but see step 3a for conflict handling)

   Note: Consider context when interpreting signals. "Start a future task"
   contains "start" but clearly indicates FUTURE intent. When in doubt, the
   explicit timing word ("future", "schedule", etc.) takes precedence.

   **Priority 2: Existing implementing chunk check (ONLY if no explicit signal)**

   If and only if no explicit intent signal was found in Priority 1, run
   `ve chunk list --latest` to check if there's already an IMPLEMENTING chunk:

   - If there IS an IMPLEMENTING chunk → use `--future`
   - If there is NO IMPLEMENTING chunk (command exits with error or returns
     nothing) → do NOT use `--future`

3a. **Handle IMPLEMENTING conflicts.** If the user explicitly signaled they want
    to work on this NOW (IMPLEMENTING signals detected), but `ve chunk list --latest`
    shows an existing IMPLEMENTING chunk:

    1. **Inform the user** of the conflict: "You want to start this chunk
       immediately, but chunk X is currently being implemented."

    2. **Offer to pause** the current chunk: "Would you like me to pause the
       current chunk so we can start this one?"

    3. **If the user agrees**, execute the safe pause protocol:
       - Run `pytest tests/` and confirm all tests pass. If tests fail, inform
         the user and do NOT proceed with the pause—the codebase should be
         healthy before switching context.
       - Add a "## Paused State" section to the current chunk's PLAN.md
         documenting:
         - Which steps have been completed
         - What remains to be done
         - Any work-in-progress context the next agent needs
       - Run `ve chunk status <current_chunk_id> FUTURE` to change the current
         chunk's status from IMPLEMENTING to FUTURE

    4. **Then proceed** to create the new chunk as IMPLEMENTING (without `--future`)

    If the user declines the pause, use `--future` for the new chunk instead.

4. Run `ve chunk create <shortname> <ticket number> [--future]` and note the chunk
   directory name that is returned by the command. Include `--future` based on
   the determination in step 3. Substitute this name below for the <chunk
   directory> placeholder.

5. Refine the contents of <chunk directory>/GOAL.md given the piece of work that
   the user has described, ask them any questions required to complete the
   template and cohesively and thoroughly define the goal of what they're trying
   to accomplish.

6. **Check for investigation origin.** If this chunk was derived from an
   investigation's `proposed_chunks` (e.g., the user referenced an investigation
   or you can identify that the work originated from exploratory findings):

   - Set the `investigation` field in the chunk's frontmatter to the investigation
     directory name (e.g., `investigation: memory_leak` for
     `docs/investigations/memory_leak/`)
   - Update the investigation's OVERVIEW.md to add this chunk's directory to the
     corresponding `proposed_chunks` entry's `chunk_directory` field

**Note on FUTURE chunks:** A FUTURE chunk is queued for later work. When the user
is ready to start working on it, they can run `ve chunk activate <chunk_id>` to
change its status from FUTURE to IMPLEMENTING. Only one chunk can be IMPLEMENTING
at a time. 