---
description: Create a new chunk of work and refine its goal.
---


<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

Run `ve init` to regenerate.
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

2. If the operator has referenced a ticket number, extract it and supply it to
   the command below where the placeholder <ticket number> is referenced. If no
   ticket number is referenced, omit that argument entirely.

   **Note:** The ticket ID affects only the `ticket:` field in GOAL.md frontmatter,
   not the directory name. The directory will always be `docs/chunks/<shortname>/`.

3. Run `ve chunk create <shortname> <ticket number>` and note the path
   that is returned by the command. The chunk will be created at:
   `docs/chunks/<shortname>/GOAL.md` (regardless of whether a ticket was provided)

   Substitute this path below for the <chunk directory> placeholder.

4. Refine the contents of <chunk directory>/GOAL.md given the piece of work that
   the user has described, ask them any questions required to complete the
   template and cohesively and thoroughly define the goal of what they're trying
   to accomplish.

5. **Check if this chunk comes from a narrative or investigation with dependencies.**

   If the work being created matches a prompt in a narrative's or investigation's
   `proposed_chunks` array, check for `depends_on` references:

   a. **Find the matching prompt**: Read the source artifact's OVERVIEW.md and find
      the `proposed_chunks` entry whose `prompt` matches (or closely describes) this work.

   b. **Check for depends_on**: If the matching entry has `depends_on: [0, 2]` or similar,
      these are indices referencing other entries in the same `proposed_chunks` array.

   c. **Resolve to chunk names**: For each index in `depends_on`:
      - Look up `proposed_chunks[index]` in the same array
      - Get the `chunk_directory` value from that entry
      - If `chunk_directory` is a valid name (not null), add it to the chunk's `depends_on`
      - If `chunk_directory` is null, **warn the user**: "Dependency at index N has not
        been created yet. Consider creating chunks in dependency order, or leave this
        dependency unresolved for now."

   d. **Populate the chunk's depends_on field**: Add the resolved chunk directory names
      to the new chunk's GOAL.md `depends_on` frontmatter field as a list of strings.
      Example: `depends_on: ["auth_core", "config_module"]`

   e. **Update the narrative/investigation**: After creating the chunk, update the
      source artifact's `proposed_chunks` array to set `chunk_directory: "<shortname>"`
      for the entry matching this chunk's prompt.

6. **Understand the `depends_on` null vs empty semantics.**

   The `depends_on` field in GOAL.md has three meaningful states, and the default
   template value of `depends_on: []` is an **explicit assertion**, not a placeholder.

   - **`depends_on: []`** (empty list): You have analyzed the chunk and determined it
     has no implementation dependencies on other chunks. This **bypasses the orchestrator's
     conflict oracle**—use it when you're confident the chunk is independent.

   - **`depends_on: null`** or omit entirely: You haven't analyzed dependencies, or the
     analysis is uncertain. This **triggers oracle consultation** at injection time for
     heuristic dependency detection.

   - **`depends_on: ["chunk_a", ...]`**: You know specific chunks that must complete
     before this one. This also **bypasses the oracle** with your explicit declarations.

   **When to change the default:**

   - If step 5 above found dependencies from a narrative/investigation, populate them.
   - If this chunk is part of a batch and you're uncertain about inter-dependencies,
     **change `depends_on: []` to `depends_on: null`** so the oracle can analyze.
   - If you're creating a standalone chunk and have verified it's independent, leave `[]`.

   See the GOAL.md template's DEPENDS_ON section for the full semantics table.

7. **Check if this is a bug fix.** Look for these signals that indicate bug fix
   work: "bug", "fix", "broken", "error", "issue", "defect", "regression",
   "incorrect", "wrong", "failing".

   If the work is a bug fix, note this in the GOAL.md success criteria so that
   when implementation is complete, the fix can be verified.

8. **Check for existing implementing chunk.** Run `ve chunk list --current` to
   check if there's already an IMPLEMENTING chunk.

   If there IS an existing IMPLEMENTING chunk, inform the user:
   "Note: Chunk <existing_chunk> is currently being implemented. You can work
   on this new chunk by completing the current one first with `ve chunk complete`,
   or create this one with `--future` to work on it later."

9. **IMPORTANT: When committing a new chunk, commit the entire chunk directory.**

   The `ve chunk create` command creates both GOAL.md and PLAN.md files. When
   committing after refinement and approval, add the **entire chunk directory**
   to the commit, not just the files you modified:

   ```bash
   git add docs/chunks/<shortname>/
   ```

   **Why this matters:** If you only commit GOAL.md (the file you edited), PLAN.md
   remains untracked on main. When the orchestrator later creates a worktree to
   run the PLAN phase, the merge will fail with "untracked working tree files
   would be overwritten" because PLAN.md exists in both places.

   This is especially critical for FUTURE chunks being prepared for orchestrator
   injection—always commit both files together.