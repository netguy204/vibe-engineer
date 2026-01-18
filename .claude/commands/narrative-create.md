---
description: Collaboratively refine a high-level ambition into a set of chunk prompts.
---



<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

This file is rendered from: src/templates/commands/narrative-create.md.jinja2
Edit the source template, then run `ve init` to regenerate.
-->


## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.

**Note:** Narratives are stored in the user-global scratchpad at `~/.vibe/scratchpad/`.
In project context, narratives are stored in `~/.vibe/scratchpad/[project]/narratives/`.
In task context, narratives are stored in `~/.vibe/scratchpad/task:[name]/narratives/`.

## Instructions

The operator wants to collaboratively develop this concept with you:

$ARGUMENTS

---

1. Create a short name handle that describes this concept. A short name should
   be 32 characters or less and words should be underscore separated. We will
   refer to this shortname later as <shortname>.

2. Run `ve narrative create <shortname>` and note the created path. The narrative
   will be created in the scratchpad. Example output:
   ```
   Created ~/.vibe/scratchpad/[project]/narratives/<shortname>
   ```
   We will refer to this path later as <narrative_path>.

3. Complete the template in <narrative_path>/OVERVIEW.md with the
   information supplied by the operator and through further clarification
   interactions with the operator. 