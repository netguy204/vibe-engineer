---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/entity.py
- src/entity_repo.py
- src/entity_merge.py
code_references:
  - ref: src/entity_repo.py#EntityRepoMetadata
    implements: "Fork lineage tracking via forked_from field"
  - ref: src/entity_repo.py#ForkResult
    implements: "Result type for fork_entity operation"
  - ref: src/entity_repo.py#MergeResult
    implements: "Result type for a clean merge_entity operation"
  - ref: src/entity_repo.py#ConflictResolution
    implements: "LLM-resolved conflict pending operator approval"
  - ref: src/entity_repo.py#MergeConflictsPending
    implements: "Result type when merge halts due to conflicts requiring resolution"
  - ref: src/entity_repo.py#fork_entity
    implements: "Clones entity repo with updated name and fork lineage metadata"
  - ref: src/entity_repo.py#merge_entity
    implements: "Fetches and merges learnings from source entity with LLM conflict resolution"
  - ref: src/entity_repo.py#commit_resolved_merge
    implements: "Writes resolved conflict content and completes the merge commit"
  - ref: src/entity_repo.py#abort_merge
    implements: "Aborts an in-progress merge and restores pre-merge state"
  - ref: src/entity_merge.py#ConflictHunk
    implements: "Parsed git conflict hunk (ours/theirs)"
  - ref: src/entity_merge.py#parse_conflict_markers
    implements: "Parses git conflict markers from file content"
  - ref: src/entity_merge.py#resolve_wiki_conflict
    implements: "LLM-assisted synthesis of conflicting wiki page versions via Anthropic API"
  - ref: src/cli/entity.py#fork
    implements: "CLI command: ve entity fork <name> <new-name>"
  - ref: src/cli/entity.py#merge
    implements: "CLI command: ve entity merge <name> <source> with operator approval gate"
narrative: null
investigation: entity_wiki_memory
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_push_pull
created_after:
- board_watch_reconnect_fix
---
# Chunk Goal

## Minor Goal

Implement `ve entity fork <name> <new-name>` and `ve entity merge <name> <source>` to enable entities to diverge for specialized training and recombine learnings — like code branches but for specialist knowledge.

Entities fork and merge regularly as they're shared across team members and projects. A team member forks an entity specialist, trains it further on their project (developing new domain expertise), and can merge those learnings back to the original. The entity's git history becomes a record of its professional development across contexts.

### Context for implementing agent

**Read the investigation first**: `docs/investigations/entity_wiki_memory/OVERVIEW.md` — especially the H2 exploration log where fork/merge was prototyped, including the conflict test.

**The big picture**: Entities are portable specialists whose git history is a record of professional development. Fork/merge treats entity knowledge the way git treats code — diverge for specialized training, recombine to share learnings. A team member forks a "database specialist" entity, trains it on their specific PostgreSQL migration project, then merges those learnings back so the original entity gains PostgreSQL expertise without losing its existing knowledge. The entity's git log reads like a career history.

**Existing code**: `src/cli/entity.py` has the entity CLI group. No fork/merge commands exist yet. The LLM-assisted conflict resolution is new — there's no existing merge tooling to build on, but `src/orchestrator/agent.py` shows how to use the `claude_agent_sdk` for LLM-driven tasks. Wiki pages are markdown files with YAML frontmatter and wikilinks — conflicts in these files are knowledge synthesis problems, not code conflicts.

**The LLM Wiki pattern** is relevant here: when two wiki versions conflict, the merge is a knowledge synthesis operation. The entity reads both versions (e.g., "Version A says the proving model requires exit 0; Version B says SIGTERM handling also works") and synthesizes them into a single version that preserves all valuable knowledge from both contexts.

Fork/merge was tested in the investigation's H2 prototype:
- Fork developed PagerDuty expertise independently
- Original continued learning CI pipeline patterns
- Merge combined both knowledge sets cleanly — new domain pages auto-merged
- Same-line edits to identity.md produced standard git conflicts (expected, manageable)

### What to build

1. **`ve entity fork <name> <new-name>`**:
   - Clones the entity's repo to a new directory with the new name
   - Updates ENTITY.md with the new name and records the fork origin
   - Optionally creates a new remote repo (if a remote template/host is configured)
   - Makes an initial commit recording the fork: "Forked from <name>"
   - The fork is a fully independent entity with its own history going forward

2. **`ve entity merge <name> <source>`**:
   - `<source>` can be a repo URL, a local path, or the name of another attached entity
   - Fetches the source's history into a temporary remote
   - Attempts to merge source's main branch into the target entity
   - **If clean merge**: commits with message "Merge learnings from <source>"
   - **If conflicts**: launches LLM-assisted conflict resolution:
     - For each conflicting wiki file, read both versions
     - Use the entity's own judgment to synthesize (the entity reads both sides and decides what's true)
     - Present the resolution to the operator for approval before committing
   - Reports what was gained: new pages, updated pages, merged identity changes

3. **LLM-assisted conflict resolution** (`entity_merge.py`):
   - Parse git conflict markers in wiki markdown files
   - For each conflict, format both versions with context
   - Prompt the LLM: "You are merging two versions of your wiki page. Version A reflects your experience in context X. Version B reflects your experience in context Y. Synthesize both into a single version that preserves all valuable knowledge."
   - Write the resolved version and stage it
   - This is the key innovation: wiki conflicts are knowledge synthesis problems, not code conflicts

### Design constraints

- Fork creates a fully independent entity — changes to the fork don't affect the original (and vice versa) until explicitly merged
- Merge should be conservative — always show the operator what will change before committing
- LLM-assisted conflict resolution should handle wiki pages (markdown) — binary files or non-wiki files use standard git conflict resolution
- Fork should preserve full history (not a shallow clone) so the entity's professional development record is intact
- ENTITY.md should track fork lineage (forked_from field)

## Success Criteria

- `ve entity fork specialist new-specialist` creates an independent clone with updated metadata
- `ve entity merge specialist https://github.com/user/other-specialist.git` merges learnings
- Clean merges auto-complete with a summary of what was gained
- Conflicting wiki pages trigger LLM-assisted resolution
- LLM resolution produces coherent synthesized content (not just concatenation)
- Operator must approve conflict resolutions before commit
- Fork lineage is tracked in ENTITY.md
- Tests cover: fork, clean merge, conflicting merge, LLM resolution quality
