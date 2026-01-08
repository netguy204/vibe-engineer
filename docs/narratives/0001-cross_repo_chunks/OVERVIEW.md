---
status: ACTIVE
advances_trunk_goal: "Required Properties: It must be possible to perform the workflow outside the context of a Git repository."
chunks:
  - prompt: "Cross-repo schemas: Define Pydantic models for .ve-task.yaml, external.yaml, and extended chunk GOAL.md frontmatter with dependents list. Add utility functions to detect task directories and external vs local chunks."
    chunk_directory: "0007-cross_repo_schemas"
  - prompt: "Git local utilities: Create utility functions for working with local git worktrees. Implement get_current_sha and resolve_ref to operate on local worktrees within the task directory."
    chunk_directory: "0008-git_local_utilities"
  - prompt: "ve task init command: Implement ve task init --external <dir> --project <dir> to initialize a task directory. Validate directories exist and are VE-initialized git repos, create .ve-task.yaml, and report success."
    chunk_directory: "0009-task_init"
---

## Advances Trunk Goal

**Required Properties** from trunk GOAL.md states:

> "It must be possible to perform the workflow outside the context of a Git repository."

This narrative extends that property to its logical conclusion: work that spans multiple repositories needs chunks that live outside any single repo, while still maintaining the versioning and archaeological properties that make chunks valuable.

## Driving Ambition

When engineering work spans multiple repositories, the current Vibe Engineering workflow breaks down. Chunks live in `docs/chunks/` within a single repo, but cross-repo work has no natural home. The current workaround—creating a task folder with git worktrees and ad-hoc planning documents—works for guiding agents but fails to capture those documents as durable artifacts.

This narrative introduces **task directories** and **external chunks** to formalize cross-repo work:

- A **task directory** is a parent folder containing git worktrees for all participating repositories plus an external chunk repository. A configuration file (`.ve-task.yaml`) declares the structure.
- **External chunks** live in the external chunk repository and are referenced from each participating repo via `external.yaml` files.
- **Bidirectional references** allow traversal of the full dependency graph: external chunks list their dependents, and participating repos point to the external chunk.

The key insight is that external references are always **living**—they track the evolving external chunk—but each repo captures point-in-time snapshots via a `pinned` field that's updated by `ve sync` and committed alongside code changes. This preserves archaeological capability: checking out any historical commit reveals what the external chunk looked like when that code was written.

A single command (`ve chunk create <name>`) run from the task directory creates the chunk in the external repo and the references in all participating repos simultaneously.

## Data Model

### Task Directory

A task directory is the coordination point for cross-repo work. It contains git worktrees and a configuration file:

```
auth-token-work/                    # Task directory
  .ve-task.yaml                     # Task configuration
  acme-chunks/                      # Worktree: external chunk repo
  service-a/                        # Worktree: consumer repo
  service-b/                        # Worktree: consumer repo
```

The `.ve-task.yaml` file:

```yaml
external_chunk_repo: acme-chunks
projects:
  - service-a
  - service-b
```

- **external_chunk_repo**: Directory name of the external chunk repository worktree
- **projects**: List of participating repository worktree directories

When `ve` commands run from a task directory (detected by presence of `.ve-task.yaml`), they operate in task-aware mode:
- `ve chunk list` shows chunks from the external chunk repo
- `ve chunk create` creates in the external repo and references in all projects
- "Current chunk" means the highest-numbered chunk in the external repo

### External Chunk Repository

A dedicated git repository (e.g., `acme-chunks`) that stores cross-repo chunks. This repo uses standard `ve` structure:

```
acme-chunks/
  docs/
    trunk/
      GOAL.md          # Purpose of this chunk repository
    chunks/
      0001-auth_token_format/
        GOAL.md        # Includes dependents in frontmatter
        PLAN.md
    narratives/
      0001-cross_service_auth/
        OVERVIEW.md
```

External chunk GOAL.md frontmatter includes **dependents**—back-references to repos that consume this chunk:

```yaml
---
status: IMPLEMENTING
dependents:
  - repo: service-a
    local_chunk: 0003-auth_token_format
  - repo: service-b
    local_chunk: 0007-auth_token_format
---
```

This enables traversal of the full dependency graph from either direction.

Team access is managed via normal git hosting (GitHub, GitLab, etc.).

### External Chunk Reference

In each participating repository, external chunks appear as directories in the normal chunk sequence:

```
my-service/
  docs/
    chunks/
      0001-local_feature/        # Local chunk
        GOAL.md
        PLAN.md
      0002-auth_token_format/    # External chunk reference
        external.yaml
```

The `external.yaml` file:

```yaml
repo: acme/acme-chunks
chunk: 0001-auth_token_format    # Chunk ID in the remote repo
track: main                      # Branch to follow
pinned: a1b2c3d4e5f6            # SHA at last sync
```

- **repo**: The external chunk repository (can be URL or org/repo shorthand)
- **chunk**: The chunk identifier in the remote repository (may differ from local ID)
- **track**: The branch or ref to follow for living references
- **pinned**: The resolved commit SHA, updated by `ve sync`

### Resolution Semantics

| Context | Query | Resolution |
|---------|-------|------------|
| Task directory | "What's the current chunk?" | Read from external chunk repo worktree at HEAD |
| Task directory | "What was the chunk at commit X?" | Checkout commit X in project repo, read `pinned`, checkout that SHA in external repo |
| Single repo | "What's the current chunk?" | Resolve `track` in external repo (may require fetch) |
| Single repo | "What was the chunk at commit X?" | Checkout commit X, read `pinned` from that commit's `external.yaml` |

In a task directory, all worktrees are local, so resolution is fast and doesn't require network access. Outside a task directory, `ve` may need to fetch from remote repos.

## Chunks

### Dependency Graph

```
[1. Schemas] ───────┬──> [3. task init]
                    │
                    ├──> [4. chunk create task-aware]
                    │
                    ├──> [5. chunk list task-aware]
                    │
[2. Git utilities] ─┼──> [4. chunk create task-aware]
                    │
                    ├──> [6. sync]
                    │
                    └──> [7. resolve]
```

Chunks 1 and 2 are foundational and can be done in parallel. Chunks 3-7 depend on them.

### Chunk Prompts

1. **Cross-repo schemas**: Define Pydantic models for: (a) `.ve-task.yaml` with `external_chunk_repo` and `projects` fields, (b) `external.yaml` with `repo`, `chunk`, `track`, and `pinned` fields, (c) extended chunk GOAL.md frontmatter with optional `dependents` list. Include validation (e.g., `pinned` must be valid SHA format, `track` defaults to `main`). Add utility functions to detect task directories and external vs local chunks.

2. **Git local utilities**: Create utility functions for working with local git worktrees. Implement `get_current_sha(repo_path) -> sha` to get HEAD SHA of a local repo, and `resolve_ref(repo_path, ref) -> sha` to resolve a branch/tag to SHA. These operate on local worktrees within the task directory, not remote repos.

3. **ve task init command**: Implement `ve task init --external <dir> --project <dir> [--project <dir>...]` to initialize a task directory. The command should: validate that specified directories exist and are git repos, create `.ve-task.yaml` with the configuration, and report success. Running from an existing task directory should error or offer to update.

4. **ve chunk create task-aware**: Extend `ve chunk create <short-name>` to detect task directory context. When in a task directory: create the chunk in the external chunk repo with `dependents` metadata, create `external.yaml` references in each project repo (using next sequential local ID per repo), resolve and populate `pinned` fields, and report all created paths. Preserve existing single-repo behavior when not in a task directory.

5. **ve chunk list task-aware**: Extend `ve chunk list` to detect task directory context. When in a task directory: list chunks from the external chunk repo, show dependent repos for each chunk, `--latest` returns highest chunk from external repo. Preserve existing single-repo behavior when not in a task directory.

6. **ve sync command**: Implement `ve sync` to update `pinned` fields in external chunk references. When run from a task directory: iterate all projects, find `external.yaml` files, resolve current SHA from external chunk repo, update `pinned` if changed. When run from a single repo: update only that repo's external references. Report which references were updated.

7. **ve external resolve command**: Implement `ve external resolve <local-chunk-id> [--at-pinned]` to display an external chunk's content. Locate the `external.yaml`, resolve the external chunk location, display GOAL.md and PLAN.md. By default show content at current HEAD of external repo; with `--at-pinned` show content at the pinned SHA. Works from both task directory and single repo contexts.

## Completion Criteria

When complete, a team can:

1. **Set up a task directory** via `ve task init`, declaring the external chunk repo and participating projects in a single configuration file

2. **Create cross-repo chunks with one command** via `ve chunk create` from the task directory, which simultaneously creates the chunk in the external repo and references in all participating projects with bidirectional metadata

3. **List chunks at the task level** via `ve chunk list`, seeing the external repo's chunks and their dependents, with "current chunk" resolving to the highest in the external repo

4. **Keep references synchronized** via `ve sync`, ensuring the `pinned` field captures point-in-time state for archaeological queries

5. **Resolve external chunk content** via `ve external resolve`, viewing the GOAL.md and PLAN.md from the external repo

6. **Traverse the dependency graph** in either direction: from an external chunk to its dependent repos, or from a participating repo's external reference back to the canonical chunk

The archaeological property is preserved: checking out any historical commit of a participating repo allows resolution of external chunks to their state at that point in history via the `pinned` field.