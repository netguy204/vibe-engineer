---
status: SOLVED
trigger: "Entity memory system needs wiki-based knowledge, git-backed portability, and Agent SDK consolidation"
proposed_chunks:
  - prompt: "Define canonical entity wiki schema as ve template with directory structure, page templates, frontmatter conventions, and maintenance instructions"
    chunk_directory: null
    depends_on: []
  - prompt: "Create entity git repo structure and ve entity create command"
    chunk_directory: null
    depends_on: [0]
  - prompt: "Implement ve entity attach/detach for submodule lifecycle"
    chunk_directory: null
    depends_on: [1]
  - prompt: "Revise entity-startup skill to load from wiki-based structure"
    chunk_directory: null
    depends_on: [0, 2]
  - prompt: "Revise entity-shutdown to use wiki diff + Agent SDK consolidation"
    chunk_directory: null
    depends_on: [0, 3]
  - prompt: "Implement ve entity push/pull for remote sync"
    chunk_directory: null
    depends_on: [2]
  - prompt: "Implement ve entity fork/merge with LLM-assisted conflict resolution"
    chunk_directory: null
    depends_on: [5]
  - prompt: "Create migration tool for existing entities to wiki-based structure"
    chunk_directory: null
    depends_on: [0, 1]
  - prompt: "Ensure entity submodules work with orchestrator worktrees"
    chunk_directory: null
    depends_on: [2, 4]
created_after: ["entity_session_harness"]
---

<!--
DO NOT DELETE THIS COMMENT until the investigation reaches a terminal status.
This documents the frontmatter schema and guides investigation workflow.

STATUS VALUES:
- ONGOING: Investigation is active; exploration and analysis in progress
- SOLVED: The investigation question has been answered. If proposed_chunks exist,
  implementation work remains—SOLVED indicates the investigation is complete, not
  that all resulting work is done.
- NOTED: Findings documented but no action required; kept for future reference
- DEFERRED: Investigation paused; may be revisited later when conditions change

TRIGGER:
- Brief description of what prompted this investigation
- Examples:
  - "Test failures in CI after dependency upgrade"
  - "User reported slow response times on dashboard"
  - "Exploring whether GraphQL would simplify our API"
- The trigger naturally captures whether this is an issue (problem to solve)
  or a concept (opportunity to explore)

PROPOSED_CHUNKS:
- Starts empty; entries are added if investigation reveals actionable work
- Each entry records a chunk prompt for work that should be done
- Format: list of {prompt, chunk_directory, depends_on} where:
  - prompt: The proposed chunk prompt text
  - chunk_directory: Populated when/if the chunk is actually created via /chunk-create
  - depends_on: Optional array of integer indices expressing implementation dependencies.

    SEMANTICS (null vs empty distinction):
    | Value           | Meaning                                 | Oracle behavior |
    |-----------------|----------------------------------------|-----------------|
    | omitted/null    | "I don't know dependencies for this"  | Consult oracle  |
    | []              | "Explicitly has no dependencies"       | Bypass oracle   |
    | [0, 2]          | "Depends on prompts at indices 0 & 2"  | Bypass oracle   |

    - Indices are zero-based and reference other prompts in this same array
    - At chunk-create time, index references are translated to chunk directory names
    - Use `[]` when you've analyzed the chunks and determined they're independent
    - Omit the field when you don't have enough context to determine dependencies
- Unlike narrative chunks (which are planned upfront), these emerge from investigation findings
-->

## Trigger

Entities are evolving from ephemeral session workers into persistent specialist employees that work across multiple projects over time. The current memory system (journal → consolidated → core tiers with LLM-driven consolidation) has proven the value of persistent entity memory but has several limitations:

1. **Shallow knowledge**: Core memories are terse identity anchors, but entities lack a place to maintain deep, structured, interlinked knowledge about their domains, preferences, and working patterns.
2. **No cross-project persistence**: Entity memory is project-local. An entity that works on multiple repos rebuilds context from scratch each time.
3. **Consolidation data loss**: The LLM consolidation pipeline has already caused data loss (entity_shutdown_memory_wipe), suggesting the pipeline is fragile for the amount of knowledge it's asked to compress.
4. **No version history**: Entity knowledge changes over time but there's no way to see how it evolved or roll back.

5. **Unreliable shutdown consolidation**: When starting an entity via `ve entity claude` and shutting it down, the journal writing phase often exceeds the shutdown timeout and falls back to transcript scanning. This fallback is unreliable — it frequently produces zero journal entries when meaningful ones should exist. The timeout is too short, but the deeper issue is that the consolidation runs as a prompted task inside the restored CLI session with limited observability. Running consolidation via the Claude Agent SDK instead would provide: (a) no arbitrary timeout — confidence the task will complete, (b) agentic capability to explore the memory hierarchy (read files, compare entries, make decisions), and (c) Claude Max pricing instead of API key rates when the Messages API fallback is used.
6. **Trapped specialists**: The existing entity system has produced well-trained specialists with real expertise — domain knowledge, working patterns, calibrated judgment. But these specialists are locked to the project where they were trained. There's no way to move a specialist to a new context where their skills would be valuable. The entity's value exceeds the project that created it, but the platform doesn't reflect this. Entities should be portable, reusable specialists that move across the platform — not project-local state.

The git submodule concept is load-bearing here: it's what makes entities portable. A specialist trained in one project can be submodule-added to another, bringing their full wiki, memories, and identity with them. The key reframing is that **entities are well-trained specialists that move across the platform**, not ephemeral workers bound to a single repo.

The LLM Wiki pattern (see appendix) offers a compelling alternative for how these specialists maintain their knowledge: a persistent, structured wiki as their primary knowledge store, with the existing consolidation stack layered on top as a fast-loading summary mechanism rather than the primary repository of knowledge.

## Success Criteria

1. **Architecture design**: Clear specification of how entity git repos, wiki structure, and the existing consolidation stack interact — including the data flow from wiki diffs → journal entries → consolidated → core memories.
2. **Submodule lifecycle**: Defined workflow for how entity repos are git-submodule-added to tasks, maintained across projects, and committed at entity shutdown.
3. **Wiki schema design**: Define what an entity's wiki looks like — index structure, page types, maintenance conventions — adapted from the LLM Wiki pattern for agent self-knowledge rather than research.
4. **Migration path**: Concrete plan for migrating existing entities (with current journal/consolidated/core memories) to the new wiki-based system without losing knowledge.
5. **Startup/shutdown integration**: How entity-startup and entity-shutdown skills change — startup loads the wiki + core memories for fast context, shutdown commits wiki changes and runs the consolidation pipeline.
6. **Proposed chunks**: Actionable chunk prompts covering the full implementation.

## Testable Hypotheses

### H1: Wiki diffs can produce meaningful journal entries for the consolidation pipeline

- **Rationale**: If we diff the wiki before/after a session, the changes represent what the entity learned or revised. These diffs can be transformed into journal-format entries that feed the existing consolidation pipeline, preserving backward compatibility.
- **Test**: Prototype a diff-to-journal transformer on a sample wiki edit session. Evaluate whether the resulting journal entries are comparable in quality to current LLM-extracted journals.
- **Status**: VERIFIED — Wiki diffs from a second session produced 137 lines of structured, contextualized changes across 10 modified files. Each diff hunk reads as a high-quality journal entry, superior to transcript-extracted journals because knowledge is already structured and positioned relative to existing knowledge.

### H2: Git repos + submodules enable portable, forkable entities

- **Rationale**: Every entity has its own git repository. A CLI command attaches an entity to a project via `git submodule add`, cloning the entity's repo into the project. The entity works in that project context, and at shutdown its wiki/memory changes are committed to its repo. The entity's history can be pushed back to the origin.

  The key insight: entities **fork and merge** like code. A team member forks an entity specialist, trains it further on their project, and can merge those learnings back to the original. The entity's git history becomes a record of its professional development across contexts and teams.

  **Interaction model**:
  ```
  ve entity attach <entity-repo-url>     # git submodule add → clones entity into .entities/
  ve entity start <name>                  # loads wiki + core memories, begins session
  # ... work session ...
  ve entity shutdown <name>               # updates wiki, diffs, consolidates, commits to entity repo
  ve entity push <name>                   # pushes entity repo to origin
  ve entity fork <name> <new-name>        # fork an entity for divergent training
  ve entity merge <name> <source>         # merge learnings from a fork back
  ```

- **Test**: Create a prototype entity repo, submodule-add it to two different task repos, verify commits flow correctly. Test fork/merge with wiki content to see how git handles wiki merge conflicts. Test interaction with orchestrator worktree system.
- **Status**: VERIFIED — Full lifecycle tested:
  1. Entity repo submodule-added to two projects — both access the wiki correctly
  2. Entity changes committed in project A, pushed to origin, pulled in project B — clean fast-forward
  3. Fork created, divergent expertise added (PagerDuty), merged back — clean merge with both knowledge sets combined
  4. Conflicting edits to same wiki line produced standard git conflict — solvable with LLM-assisted merge
  5. Worktrees work: `git submodule update --init` in worktree, entity accessible and independently editable, main checkout unaffected
  6. Bare repo (simulating GitHub-hosted) as origin works correctly for push/pull flow
- **Open questions** (narrowed):
  - Entity repos should be hosted (GitHub/GitLab) for real cross-team sharing — bare local repos confirmed the mechanics
  - Wiki merge conflicts are standard git conflicts — LLM-assisted merge is the natural resolution (entity reads both sides, synthesizes)
  - Concurrent use from two projects needs branching discipline — each project works on a branch, merges back to main at shutdown
  - Worktree submodules start in detached HEAD — `ve entity start` needs to checkout a working branch

### H3: Core memories establish identity and values, not summarize the wiki

- **Rationale**: Core memories are not a summary of the wiki — they are highly abstracted derivations of an entity's work over a long period. They serve alongside the identity file to establish *who the agent is and what's important to them*: internalized principles, hard-won judgment, aesthetic preferences, relationship patterns, domain intuitions. A core memory like "I've learned that users say they want flexibility but actually want opinionated defaults" is not a wiki summary — it's wisdom distilled from dozens of sessions. The wiki holds the details; core memories hold the character.
- **Test**: Review existing core memories across entities. Verify they read as identity/values statements rather than factual summaries. Design the consolidation prompt to explicitly target this abstraction level — "what has this work taught you about who you are and what matters?" rather than "summarize what happened."
- **Status**: UNTESTED

### H4: The wiki schema can be standardized across entity types

- **Rationale**: All entities need similar page types (identity, domain knowledge, project notes, preferences, relationships). A standard schema with optional extensions per entity type would simplify tooling.
- **Test**: Analyze 2-3 existing entities' memory contents and map them to a proposed wiki schema. Identify what's common vs. entity-specific.
- **Status**: VERIFIED — Same schema produced coherent wikis across 3 very different sessions (infrastructure entity, debugging-heavy entity, architecture/design session). All converged on the same directory structure and page types. Domain content varied naturally but structural patterns were identical.

## Exploration Log

<!--
GUIDANCE:

Document your exploration steps and findings chronologically. This creates a
valuable record of:
- What was tried
- What was learned
- What led to dead ends (and why)

Use timestamped entries to track progress over time.

Format suggestion: `### YYYY-MM-DD: [Summary]`

PROTOTYPES:

When writing code to test hypotheses (scripts, benchmarks, proof-of-concepts),
save them in a `prototypes/` subdirectory within this investigation folder.
This keeps experimental code with the investigation that produced it, making
findings reproducible and providing context for future readers.

Example structure:
  docs/investigations/memory_leak/
  ├── OVERVIEW.md
  └── prototypes/
      ├── memory_profiler.py
      └── cache_benchmark.py

Reference prototypes from the Exploration Log:
  "Ran cache benchmark (see `prototypes/cache_benchmark.py`), results show..."

Example log entries:

### 2024-01-15: Initial profiling

Ran memory profiler on production-like workload. Observed:
- Peak memory 2.3GB during image batch processing
- Memory not released after batch completes
- GC logs show objects held by `ImageCache` singleton

### 2024-01-16: ImageCache analysis

Reviewed ImageCache implementation. Found:
- Cache has no eviction policy
- References held indefinitely
- Easy fix: add LRU eviction with configurable limit

This differs from Findings in that it captures the journey, not just conclusions.
-->

### 2026-04-15: Wiki construction from transcripts (H4 + H1)

**Setup**: Extracted readable transcripts from 3 sessions — 2 palette entity sessions (different entities, same platform) and 1 uniharness session (completely different domain). Spawned 3 parallel subagents to construct wikis using the same schema prompt (`prototypes/wiki_schema.md`).

**H4 Results (Schema standardization)**: Strong convergence across all 3 wikis:
- All 3 produced: `index.md`, `identity.md`, `log.md`, `domain/`, `projects/`, `techniques/`, `relationships/`
- Page counts: 16 (palette A), 11 (palette B), 15 (uniharness)
- All used the same frontmatter format, wikilink conventions, and page structure
- Domain pages naturally varied by content but followed the same structural pattern
- The schema worked equally well for an infrastructure entity, a debugging-heavy session, and an architecture/design session

**H1 Results (Diffs as journal entries)**: Fed palette B's transcript into wiki A's existing wiki (initialized as a git repo). The resulting diff:
- 10 files modified, 4 new files created, 137 insertions / 15 deletions
- **Identity evolution captured**: "I am not any single entity. I am the mind that builds and debugs them."
- **New techniques extracted**: fetch_timeout, copy_working_boilerplate
- **Domain knowledge deepened**: proving_model gained 5 new failure modes, subscription_system gained startup vs runtime gotcha
- **Log entry added**: full chronological session summary with task, events, and learnings
- **Cross-references maintained**: new pages linked from existing ones, index updated

The diff reads as a high-quality journal. Each hunk tells a clear story: "here's what I learned, here's how it connects to what I already knew." Better than LLM-extracted journal entries because:
1. The knowledge is already structured and contextualized
2. New knowledge is positioned relative to existing knowledge (not standalone fragments)
3. The entity's self-model evolution is captured naturally (identity.md changes)
4. No transcript scanning or timeout pressure

**Key observation from subagents**: "The most valuable wiki content came from *failures*, not successes." This suggests entity wikis will be richest for entities that encounter adversity — which is exactly where memory matters most.

**Prototype artifacts**: `prototypes/wiki_a/`, `prototypes/wiki_b/`, `prototypes/wiki_uniharness/`, `prototypes/wiki_schema.md`, `prototypes/extract_transcript.py`

### 2026-04-15: Git submodule lifecycle test (H2)

**Setup**: Created a prototype entity repo with the wiki from wiki_a, a bare origin (simulating GitHub), and two project repos. Exercised the full lifecycle: attach, work, push, pull, fork, merge, conflict, worktree.

**Results**:

1. **Attach** (`git submodule add`): Clean. Entity cloned into `.entities/<name>/`, wiki immediately accessible. Both projects reference the same origin.

2. **Work + push/pull**: Entity changes committed in project-alpha, pushed to origin, pulled in project-beta. Standard fast-forward merge. Entity knowledge flows between projects as expected.

3. **Fork + merge**: Forked entity developed PagerDuty expertise on Team B. Original continued learning CI pipeline patterns on Team A. Merge combined both knowledge sets cleanly — new domain pages auto-merged, separate identity edits auto-merged (different lines). The entity's git log reads as a professional development record:
   ```
   Merge: Team B PagerDuty expertise back to main
   Fork: PagerDuty expertise from Team B
   Session: CI pipeline adaptation
   Session: project-alpha onboarding
   Initial entity state: wiki + identity
   ```

4. **Conflicts**: Edits to the same line in identity.md produced a standard git conflict. This is expected and manageable — LLM-assisted merge is the natural solution (the entity reads both versions and synthesizes). Most wiki edits will be additive (new pages, new sections, appended lessons) and won't conflict.

5. **Worktrees**: `git worktree add` + `git submodule update --init` works. The submodule starts in detached HEAD (at the commit the parent recorded), but `git checkout main` puts it on a working branch. Worktree and main checkout have independent entity states — this is correct for orchestrator chunks that shouldn't interfere with each other.

**Key design decisions surfaced**:
- Entity repos need to be hosted (GitHub) for real cross-team sharing
- `ve entity start` should checkout a working branch (not detached HEAD)
- Concurrent use from two projects should use branches — merge back to main at shutdown
- `ve entity merge` should include LLM-assisted conflict resolution

## Findings

### Verified Findings

- **Wiki schema is standardizable**: The same schema (index, identity, log, domain/, projects/, techniques/, relationships/) produced coherent wikis across 3 very different sessions — infrastructure entity, debugging-heavy entity, architecture/design session. (Evidence: prototypes/wiki_a/, wiki_b/, wiki_uniharness/)

- **Wiki diffs are superior journal entries**: 137 lines of structured, contextualized changes across 10 files. Each hunk reads as a high-quality journal entry. Superior to transcript-extracted journals because knowledge is already structured and positioned relative to existing knowledge. (Evidence: git diff in wiki_a/ after second-session update)

- **Git submodules work for entity portability**: Full lifecycle verified — attach to multiple projects, push/pull between them, fork for divergent training, merge learnings back, worktree compatibility. Standard git conflict handling for same-line edits. (Evidence: Exploration Log 2026-04-15 submodule test)

- **Identity evolution is captured naturally**: The wiki update test produced the identity shift "I am not any single entity. I am the mind that builds and debugs them" — exactly the kind of insight core memories should distill. (Evidence: identity.md diff in wiki_a/)

- **Most valuable wiki content comes from failures**: Subagent observation across all 3 wikis. Entities that encounter adversity produce richer knowledge bases. (Evidence: subagent reports)

### Hypotheses/Opinions

- **Agent SDK for consolidation is the right runtime** but hasn't been prototyped. The mechanical diff removes the hardest part (journal extraction), so consolidation becomes a focused synthesis task well-suited to agentic exploration. Risk: Agent SDK session setup overhead may be significant for a short consolidation task.

- **LLM-assisted merge for wiki conflicts** should work well — the entity reads both sides and synthesizes — but we haven't tested this with real conflicting wiki content.

- **Core memory abstraction level** (identity/values, not wiki summary) is a design constraint that needs to be encoded in the consolidation prompt. The right question is "what has this work taught you about who you are and what matters?" not "summarize what happened."

## Proposed Chunks

0. **entity_wiki_schema**: Define the canonical entity wiki schema as a ve template. Create the wiki directory structure, page templates (identity.md, index.md, log.md), frontmatter conventions, and the schema document that tells the entity how to maintain its wiki during sessions. This is the "CLAUDE.md for the wiki" — the instructions that make the entity a disciplined wiki maintainer. Reference `prototypes/wiki_schema.md` and the 3 prototype wikis for what works.
   - Priority: High
   - Dependencies: None

1. **entity_repo_structure**: Create the entity git repo structure and `ve entity create <name>` command that initializes a new entity repo with wiki/, memories/, episodic/ directories, ENTITY.md identity file, and initial git commit. The repo should be a standalone git repo suitable for hosting on GitHub and submodule-adding to projects.
   - Priority: High
   - Dependencies: [0]

2. **entity_attach_detach**: Implement `ve entity attach <repo-url>` (git submodule add into .entities/) and `ve entity detach <name>` (git submodule remove). Handle the submodule lifecycle — .gitmodules management, initial clone, and ensuring the entity's wiki is accessible after attach. Must work with both GitHub URLs and local paths.
   - Priority: High
   - Dependencies: [1]

3. **entity_startup_wiki**: Revise the entity-startup skill to load from the new wiki-based structure. Startup loading order: core memories (fast identity), wiki/index.md (structured knowledge overview), recent consolidated memories. The entity's CLAUDE.md/AGENTS.md should include the wiki schema instructions so the entity knows to maintain its wiki during the session. Must handle both new-format (wiki-based) and legacy (memory-only) entities gracefully.
   - Priority: High
   - Dependencies: [0, 2]

4. **entity_shutdown_wiki**: Revise the entity-shutdown skill to use the new pipeline: (1) git diff wiki against last commit to produce journal entries mechanically, (2) launch Agent SDK consolidation session that reads the diff + existing consolidated memories and produces updated consolidated/core memories, (3) commit all changes to the entity repo. No timeout — the Agent SDK session runs to completion. Core memory consolidation prompt must target identity/values abstraction level ("what has this work taught you about who you are?"), not summarization.
   - Priority: High
   - Dependencies: [0, 3]

5. **entity_push_pull**: Implement `ve entity push <name>` and `ve entity pull <name>` to sync entity repos with their remote origin. Push commits the entity's latest wiki + memory state to the hosted repo. Pull fetches latest from origin (e.g., after another project or team member pushed updates). Handle the case where pull requires merge (print warning, suggest `ve entity merge`).
   - Priority: Medium
   - Dependencies: [2]

6. **entity_fork_merge**: Implement `ve entity fork <name> <new-name>` (clone entity repo to a new origin, creating an independent specialist) and `ve entity merge <name> <source-url>` (merge learnings from another entity fork). Merge should include LLM-assisted conflict resolution — when wiki pages conflict, the entity reads both versions and synthesizes. Fork should preserve full history.
   - Priority: Medium
   - Dependencies: [5]

7. **entity_memory_migration**: Create a migration tool that converts existing entities (current journal/consolidated/core memory format in .entities/) to the new wiki-based structure. Read existing memories, construct an initial wiki (identity.md from core memories, domain pages from consolidated memories, log entries from journals), initialize as a git repo, and preserve the original memories in the memories/ directory. Must be non-destructive — keep originals until migration is verified.
   - Priority: High
   - Dependencies: [0, 1]

8. **entity_worktree_support**: Ensure entity submodules work correctly when the orchestrator creates worktrees for chunk execution. On worktree creation, `git submodule update --init` must run. On entity start in a worktree, checkout a working branch (not detached HEAD). On entity shutdown in a worktree, changes should be committed to the entity's branch and mergeable back to main after the worktree merges.
   - Priority: Medium
   - Dependencies: [2, 4]

## Resolution Rationale

Investigation is SOLVED. All success criteria are met:

1. **Architecture design**: Complete — wiki + git repo + Agent SDK consolidation pipeline, with data flow from runtime wiki maintenance → mechanical diff → agentic consolidation → core memory distillation.
2. **Submodule lifecycle**: Verified through prototype — attach, work, push/pull, fork/merge, worktree compatibility all tested.
3. **Wiki schema design**: Verified across 3 entity types — standardized structure works for infrastructure, debugging, and architecture/design entities.
4. **Migration path**: Defined — read existing memories, construct initial wiki, initialize git repo, preserve originals.
5. **Startup/shutdown integration**: Designed — startup loads core + wiki index, shutdown diffs wiki + runs Agent SDK consolidation.
6. **Proposed chunks**: 9 chunks with dependency ordering covering the full implementation.

The key reframing that emerged: entities are **portable specialists that move across the platform**, not project-local state. The git submodule mechanism is what makes this possible, and the wiki is what makes their knowledge deep enough to be worth moving.

## Appendix: Proposed Architecture

### Data Flow

```
During session:
  Entity works on tasks
      ↓ (naturally, as part of working)
  Entity updates wiki pages in real time
      (new knowledge, revised understanding, project notes)

At shutdown:
  git diff wiki vs last commit
      ↓ (mechanical, no LLM needed)
  Diffs ARE the journal entries
      ↓
  Agent SDK consolidation (agentic, no timeout)
      reads: diffs + existing consolidated memories
      produces: updated consolidated memories (abstract patterns)
      ↓
  Agent SDK core memory update
      reads: consolidated memories
      produces: updated core memories (identity-level)
      ↓
  git commit + push entity repo
```

### Entity Repo Structure (proposed)

```
.entities/<entity_name>/          # git repo (submodule in task repos)
├── wiki/                         # LLM-maintained knowledge base
│   ├── index.md                  # Wiki index (entity reads this at startup)
│   ├── identity.md               # Who I am, my role, my style
│   ├── domain/                   # Domain knowledge pages
│   ├── projects/                 # Per-project notes
│   ├── relationships/            # People, teams, other entities
│   └── log.md                    # Chronological activity log
├── memories/                     # Existing tier system
│   ├── journal/                  # Session-level memories
│   ├── consolidated/             # Cross-session patterns
│   └── core/                     # Identity-level memories
└── episodic/                     # Searchable session transcripts
```

### Runtime Wiki Maintenance

The entity maintains its wiki **during the session**, not at shutdown. As the entity learns, makes decisions, or develops new understanding, it updates wiki pages in real time — just as it would update code or documentation. This is natural: the wiki is the entity's notebook, and taking notes is part of working, not a post-hoc extraction step.

This eliminates the fragile shutdown consolidation problem entirely. There's no timeout pressure, no transcript scanning fallback, no risk of losing knowledge because shutdown was interrupted.

### Startup Loading Order

1. Core memories (fast identity establishment)
2. Wiki index.md (structured knowledge overview)
3. Recent consolidated memories (recent cross-session patterns)
4. Deep wiki pages loaded on-demand during session

### Shutdown Sequence

1. `git diff` the wiki against last commit → these diffs **are** the journal entries
2. Run Agent SDK consolidation: agentic exploration of the diff + existing consolidated memories → merge into more abstract representations
3. Commit wiki + memories to entity repo
4. Push if configured

The key insight: journal creation is no longer an LLM extraction task — it's a mechanical diff. The LLM's consolidation work is the higher-value task of merging concrete session changes into abstract cross-session patterns, and it runs via Agent SDK with full agentic capability and no timeout.

## Appendix: LLM Wiki Pattern

The following is the reference document for the LLM Wiki pattern that inspires the entity wiki design. The key adaptation: instead of a human curating sources and asking questions, the entity itself is both the curator and the knowledge worker — maintaining its own wiki as a structured personal knowledge base.

See `prototypes/llm_wiki_prompt.md` for the full reference prompt.