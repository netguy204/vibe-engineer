<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk restores content that was lost from source templates due to the template drift pattern identified in the `template_drift` investigation. The approach is straightforward:

1. **Extract correct content from git history** using `git show <commit>:<file>` to retrieve the intended content from specific commits
2. **Backport content to source templates** by editing the Jinja2 templates in `src/templates/`
3. **Verify via re-render** to ensure the rendered output matches expectations

This is a content restoration task, not a code logic change. The templates are declarative Jinja2 files, so the work is primarily textual editing. Per TESTING_PHILOSOPHY.md, we don't test template prose content, so no new tests are required.

## Sequence

### Step 1: Restore cluster prefix suggestion to chunk-plan.md.jinja2

**Source**: Commit `8a29e62` shows the correct content in `.claude/commands/chunk-plan.md`

**Content to add**: Insert a new Step 2 between "Determine the currently active chunk" and "Study <chunk directory>/GOAL.md" that:
- Runs `ve chunk suggest-prefix <chunk_name>` to check for semantic clustering
- Presents the suggestion to the operator if a prefix is found
- Allows renaming before continuing

**Location**: `src/templates/commands/chunk-plan.md.jinja2`

**Edits**:
1. Renumber current Step 2 → Step 3, Step 3 → Step 4
2. Insert new Step 2 with the cluster prefix suggestion logic:
   ```
   2. Run `ve chunk suggest-prefix <chunk_name>` (using just the directory name,
      not the full path) to check if this chunk should be renamed for better
      semantic clustering. If a prefix is suggested:
      - Present the suggestion to the operator: "This chunk is similar to
        `{prefix}_*` chunks. Consider renaming to `{prefix}_{current_name}`?"
      - If the operator accepts, use `mv` to rename the chunk directory
      - Update <chunk directory> to the new path before continuing
   ```

### Step 2: Add investigation frontmatter reference to CLAUDE.md.jinja2

**Source**: Commit `bd524c5` shows the correct content in `CLAUDE.md`

**Content to add**: In the "Chunk Frontmatter References" section, add the `investigation` reference between `narrative` and `subsystems`.

**Location**: `src/templates/claude/CLAUDE.md.jinja2`, line ~36-38

**Edit**: Change the frontmatter list from:
```markdown
- **narrative**: References a narrative directory (e.g., `investigations`) that this chunk helps implement
- **subsystems**: List of subsystem relationships indicating which subsystems this chunk implements or uses
```

To:
```markdown
- **narrative**: References a narrative directory (e.g., `investigations`) that this chunk helps implement
- **investigation**: References an investigation directory (e.g., `memory_leak`) from which this chunk originated, providing traceability from implementation work back to exploratory findings
- **subsystems**: List of subsystem relationships indicating which subsystems this chunk implements or uses
```

### Step 3: Update Narratives section with proposed_chunks reference

**Source**: Commit `62b6d8f` shows the correct content in `CLAUDE.md`

**Content to change**: Update the Narratives section to reference `proposed_chunks` frontmatter instead of just "Chunks".

**Location**: `src/templates/claude/CLAUDE.md.jinja2`, line ~46

**Edit**: Change:
```markdown
- **Chunks** - List of chunk prompts and their corresponding chunk directories
```

To:
```markdown
- **Proposed Chunks** - List of chunk prompts and their corresponding chunk directories (in `proposed_chunks` frontmatter)
```

### Step 4: Add Proposed Chunks to Subsystems section

**Source**: Commit `62b6d8f` shows the correct content in `CLAUDE.md`

**Content to add**: In the Subsystems section bullet list, add a line about proposed chunks.

**Location**: `src/templates/claude/CLAUDE.md.jinja2`, line ~57

**Edit**: Add after "Code References":
```markdown
- **Proposed Chunks** - Consolidation work discovered but not yet implemented (in `proposed_chunks` frontmatter)
```

### Step 5: Add expanded Investigation lifecycle details

**Source**: Commit `62b6d8f` shows the complete Investigation section in `CLAUDE.md`

**Content to add**: Expand the Investigations section with:
- Full lifecycle description (Create, Explore, Conclude, Resolve)
- Status value table (ONGOING, SOLVED, NOTED, DEFERRED with meanings)
- "When to Use" guidance (Investigation vs Chunk vs Narrative)

**Location**: `src/templates/claude/CLAUDE.md.jinja2`, after line ~80

**Edit**: Replace the current minimal Investigations section with the expanded version from commit `62b6d8f`.

### Step 6: Add Proposed Chunks cross-cutting pattern section

**Source**: Commit `62b6d8f` shows the `## Proposed Chunks` section in `CLAUDE.md`

**Content to add**: A new section explaining the `proposed_chunks` frontmatter pattern as a cross-cutting concern used in narratives, subsystems, and investigations.

**Location**: `src/templates/claude/CLAUDE.md.jinja2`, after the expanded Investigations section (before Available Commands)

**Edit**: Insert:
```markdown
## Proposed Chunks

The `proposed_chunks` frontmatter field is a cross-cutting pattern used in narratives, subsystems, and investigations to track work that has been proposed but not yet created as chunks. Each entry has:

- **prompt**: The chunk prompt text describing the work
- **chunk_directory**: `null` until a chunk is created, then the directory name

Use `ve chunk list-proposed` to see all proposed chunks that haven't been created yet across the entire project. This helps identify pending work from all sources.

The distinction between `chunks` (in subsystem frontmatter) and `proposed_chunks` is important:
- `chunks`: Tracks relationships to already-created chunks (implements/uses)
- `proposed_chunks`: Tracks proposed work that may or may not become chunks
```

### Step 7: Add Development section

**Source**: Commit `62b6d8f` and `9b8915f` show the Development section in `CLAUDE.md`

**Content to add**: A Development section explaining how to run ve during development.

**Location**: `src/templates/claude/CLAUDE.md.jinja2`, at the end of the file

**Edit**: Add:
```markdown
## Development

This project uses UV for package management. Run tests with `uv run pytest tests/`.
```

Note: The extended developer instructions from commit `9b8915f` ("As a developer of ve...") are specifically for the ve source repository and should NOT be in the consumer-facing template. That guidance belongs in the ve source CLAUDE.md (a separate chunk from the investigation).

### Step 8: Verify rendered output

Run the template render command and verify:
1. `.claude/commands/chunk-plan.md` contains the cluster prefix suggestion step
2. `CLAUDE.md` contains all restored sections

**Command**: `uv run ve project init --force` (or the appropriate render command)

**Verification**: Diff the rendered files against expected content.

## Risks and Open Questions

- **"What Counts as Code" section**: The goal mentions restoring this section, but git archaeology shows it was never actually implemented in the rendered files. This section was a conceptual item in the investigation's findings but was not part of any commit. Skipping this item unless the operator clarifies it should be created as new content.

- **Template rendering command**: Need to verify the exact command to re-render templates. May be `ve project init` or a separate render command.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->