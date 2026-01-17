---
status: DRAFTING
advances_trunk_goal: "Required Properties: It must be possible to perform the workflow outside the context of a Git repository"
investigation: bidirectional_doc_code_sync
proposed_chunks:
  - prompt: "Scratchpad storage infrastructure"
    chunk_directory: scratchpad_storage
  - prompt: "Chunk command migration"
    chunk_directory: scratchpad_chunk_commands
  - prompt: "Narrative command migration"
    chunk_directory: scratchpad_narrative_commands
  - prompt: "Cross-project scratchpad queries"
    chunk_directory: scratchpad_cross_project
created_after: []
---

<!--
STATUS VALUES:
- DRAFTING: The narrative is being refined; chunks not yet created
- ACTIVE: Chunks are being created and implemented from this narrative
- COMPLETED: All chunks have been created and the narrative's ambition is realized

ADVANCES_TRUNK_GOAL:
- Reference the specific section of docs/trunk/GOAL.md this narrative advances
- Example: "Required Properties: Must support multi-repository workflows"

PROPOSED_CHUNKS:
- Starts empty; entries are added as prompts are turned into chunks via /chunk-create
- Each entry records which prompt was refined and where the resulting chunk lives
- prompt: The prompt text from this document that was used to create the chunk
- chunk_directory: The created chunk directory (e.g., "0007-feature_name"), null until created
- DO NOT POPULATE this array during narrative creation. It will be populated as
  chunks are created.
- Use `ve chunk list-proposed` to see all proposed chunks that haven't been created yet
-->

## Advances Trunk Goal

**Required Properties**: "It must be possible to perform the workflow outside the context of a Git repository."

This narrative enables chunks (personal work-in-progress notes) to live outside any specific repository in a user-global location. When repositories migrate to subsystem-based documentation, concept documentation lives in-repo as subsystems while personal work notes live in `~/.vibe/scratchpad/`. This separation allows the workflow to function even without git context and prevents documentation clutter over time.

Also supports: "Following the workflow must maintain the health of documents over time and should not grow more difficult over time."

## Driving Ambition

The bidirectional_doc_code_sync investigation established that chunks have been conflating two purposes:

1. **Concept documentation** (wiki-like) → now lives as subsystems in-repo
2. **Work unit scratchpad** (personal notes) → should live outside git

This repository has completed the migration to subsystem-based documentation. The final step is implementing the user-global scratchpad where chunk commands operate post-migration.

**The scratchpad concept**:
- Lives at `~/.vibe/scratchpad/` organized by project
- Personal work notes, not version controlled
- Supports cross-project "What am I working on?" queries
- Supports scratchpad → Linear ticket promotion
- Both chunks AND narratives go here in migrated repos (they're both "flow artifacts" for personal planning)

**Why this matters**:
- Prevents documentation clutter (no accumulating chunk directories)
- Enables personal workflow that isn't coupled to repository state
- Supports cross-project context for daily standup ("What am I working on across all projects?")
- Creates clear separation: subsystems = shared truth, scratchpad = personal process

**Success looks like**:
- All chunk/narrative commands use scratchpad storage (no in-repo storage)
- Task context routes to `task:[name]/`, single-repo routes to `[project]/`
- An operator can query scratchpad across all projects and tasks
- An operator can promote a scratchpad entry to a Linear ticket

## Chunks

The work decomposes into these chunks, ordered by dependency:

1. **Scratchpad storage infrastructure**: Create the scratchpad module with models and storage layer at `~/.vibe/scratchpad/`. Structure:
   ```
   ~/.vibe/scratchpad/
   ├── [project-name]/           # single-project work (derived from repo name)
   │   ├── chunks/               # GOAL.md structure
   │   └── narratives/           # OVERVIEW.md structure
   └── task:[task-name]/         # multi-repo task work (prefixed)
       ├── chunks/
       └── narratives/
   ```
   Implement models for both artifact types with familiar frontmatter semantics. Implement CRUD operations: create, read, list, archive. Project name derived from repository path; task name from task context.

2. **Chunk command migration**: Rewrite chunk commands (`create`, `list`, `complete`) to use scratchpad storage. No backwards compatibility with in-repo chunks needed. Commands detect task context and route to `task:[name]/` or `[project]/` accordingly. Update `/chunk-create` skill template.

3. **Narrative command migration**: Rewrite narrative commands (`create`, `list`, `compact`) to use scratchpad storage. Narratives in scratchpad reference their chunks (also in scratchpad). Task-context narratives go to `task:[name]/narratives/`. Update `/narrative-create` skill template.

4. **Cross-project scratchpad queries**: Implement `ve scratchpad list` command that aggregates scratchpad entries (both chunks and narratives) across all projects and tasks in `~/.vibe/scratchpad/`. Support filtering by project, task, or all. Enable the "What am I working on?" use case.

## Completion Criteria

When this narrative is complete:

1. **Chunk commands use scratchpad**: `ve chunk create foo` creates `~/.vibe/scratchpad/vibe-engineer/chunks/foo/GOAL.md`

2. **Narrative commands use scratchpad**: `ve narrative create bar` creates `~/.vibe/scratchpad/vibe-engineer/narratives/bar/OVERVIEW.md`

3. **Task context routing**: In a task context, `ve chunk create foo` creates `~/.vibe/scratchpad/task:my-task/chunks/foo/GOAL.md`

4. **Cross-project visibility**: `ve scratchpad list` shows work-in-progress across all projects and tasks

5. **Personal workflow independence**: Scratchpad entries are personal, not version-controlled, and don't clutter repositories

This completes the bidirectional_doc_code_sync migration by separating concept documentation (subsystems, in-repo) from personal work notes (scratchpad, user-global).

## Future Extensions (Out of Scope)

The following are valuable but not required for this narrative:

- **Scratchpad → ticket promotion**: `ve scratchpad promote <entry>` creates a Linear ticket
- **Archive management**: `ve scratchpad archive <entry>` moves completed entries
- **Scratchpad sync**: Optional sync to cloud storage for cross-machine access