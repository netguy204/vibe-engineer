---
description: Collaboratively refine a high-level ambition into a set of chunk prompts.
---


<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

Run `ve init` to regenerate.
-->

## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.

## Instructions

The operator wants to collaboratively develop this concept with you:

$ARGUMENTS

---

1. Create a short name handle that describes this concept. A short name should
   be 32 characters or less and words should be underscore separated. We will
   refer to this shortname later as <shortname>.

2. Run `ve narrative create <shortname>` and note the created path. The narrative
   will be created in `docs/narratives/`. Example output:
   ```
   Created docs/narratives/<shortname>
   ```
   We will refer to this path later as <narrative_path>.

3. Complete the template in <narrative_path>/OVERVIEW.md with the
   information supplied by the operator and through further clarification
   interactions with the operator.

4. **When populating `proposed_chunks`, understand the `depends_on` semantics.**

   Each entry in `proposed_chunks` can optionally declare a `depends_on` field.
   This field has three meaningful states—the same null vs empty distinction
   used in chunk GOAL.md files:

   - **Omit the field** (or set to `null`): You don't know this prompt's dependencies
     yet. At chunk-create time, the orchestrator's conflict oracle will analyze.

   - **Use `depends_on: []`**: You explicitly know this prompt has no dependencies
     on other prompts in this narrative. This bypasses oracle consultation.

   - **Use `depends_on: [0, 2]`**: This prompt depends on prompts at indices 0 and 2
     in the same `proposed_chunks` array. At chunk-create time, these indices are
     translated to chunk directory names.

   **Practical guidance:**

   - If the chunks can be worked on in any order, **omit `depends_on`** to let
     the oracle detect any subtle dependencies you might have missed.
   - If you've reasoned through the order and know chunk 3 requires chunk 1's
     code to exist, use `depends_on: [1]` for chunk 3's entry.
   - If a prompt truly has no inter-dependencies, you can use `[]` to assert this,
     but omitting is safer when uncertain.

   See the OVERVIEW.md template's PROPOSED_CHUNKS section for the full semantics table.