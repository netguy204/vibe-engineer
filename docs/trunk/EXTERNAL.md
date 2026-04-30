<!-- Chunk: docs/chunks/claudemd_external_prompt - Full External Artifacts documentation -->
<!-- Chunk: docs/chunks/progressive_disclosure_external - Comprehensive external artifacts documentation -->
# External Artifacts Reference

External artifacts enable multi-repository workflows by providing pointers to artifacts that live in other repositories. This is useful when work spans multiple codebases but needs coordinated documentation.

## What External Artifacts Are

When work spans multiple repositories, artifact directories may contain an `external.yaml` file instead of the usual GOAL.md or OVERVIEW.md. These files are pointers to artifacts in other repositories—they tell VE where to find the actual artifact content.

**Example scenario:** A task directory spans three repositories. Each repo has `docs/chunks/shared_feature/external.yaml` pointing to a single canonical chunk GOAL.md in one repository.

## File Structure

External artifact files follow this schema:

```yaml
artifact_id: some_feature
artifact_type: chunk          # chunk, narrative, investigation, or subsystem
repo: org/other-repo          # Repository containing the actual artifact
track: main                   # Branch to follow
```

**Fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `artifact_id` | Yes | The artifact's directory name in the external repo |
| `artifact_type` | Yes | One of: `chunk`, `narrative`, `investigation`, `subsystem` |
| `repo` | Yes | GitHub repository path (e.g., `org/repo-name`) |
| `track` | Yes | Branch name to follow (usually `main`) |

## Resolving External Artifacts

Use the `ve external resolve` command to view the actual artifact content:

```bash
ve external resolve <artifact_id>
```

This fetches the current HEAD of the specified branch from the external repository and displays the artifact content. You don't need to clone the external repo—VE handles the fetch for you.

## Common Scenarios

### Task Directories Spanning Multiple Projects

When a feature touches multiple codebases, create the canonical chunk in one repository and use `external.yaml` pointers in the others:

```
# In repo-a (canonical)
docs/chunks/shared_feature/GOAL.md
docs/chunks/shared_feature/PLAN.md

# In repo-b (pointer)
docs/chunks/shared_feature/external.yaml
```

Each repository's codebase can reference the chunk using local paths (`docs/chunks/shared_feature`), while the actual documentation lives in a single location.

### Shared Narratives Across Codebases

Multi-repo initiatives can use a shared narrative:

```yaml
# docs/narratives/cross_repo_initiative/external.yaml
artifact_id: cross_repo_initiative
artifact_type: narrative
repo: org/planning-repo
track: main
```

All participating repositories can reference the narrative in chunk frontmatter using the local path.

### Cross-Repository Investigations

When investigating issues that span repositories:

```yaml
# docs/investigations/api_latency/external.yaml
artifact_id: api_latency
artifact_type: investigation
repo: org/core-services
track: main
```

The investigation findings and proposed chunks live in one place, but all affected repos can reference it.

## Code Backreferences with External Artifacts

When adding code backreferences, always use the **local path** within the current repository:

```python
# Chunk: docs/chunks/shared_feature - Implements the shared feature
```

Even if the chunk is external, the local `docs/chunks/shared_feature/` directory exists (containing `external.yaml`), so the path is valid. This keeps backreferences consistent regardless of whether the artifact is local or external.

## Directory Layout

An external artifact directory contains only the `external.yaml` file:

```
docs/chunks/external_feature/
└── external.yaml
```

Contrast with a local artifact:

```
docs/chunks/local_feature/
├── GOAL.md
└── PLAN.md
```

VE commands recognize both patterns and handle them appropriately.

## When to Use External Artifacts

**Use external artifacts when:**
- Work spans multiple repositories
- You need a single source of truth for documentation
- Teams coordinate across codebases on shared initiatives
- Task directories cross project boundaries

**Avoid external artifacts when:**
- Work is contained within a single repository
- The overhead of cross-repo coordination isn't justified
- You need offline access to all documentation

## Demoting External Artifacts

Over time a cross-repo chunk's scope may collapse — the implementation ended up
landing entirely in one repository. When that happens, carrying the architecture
source directory and all the pointer directories is unnecessary overhead. The
demotion commands let you collapse this bookkeeping.

### Two demotion commands

| Command | When to use | What it does |
|---------|-------------|--------------|
| `ve task demote <name>` | Standard demotion — scope may still span multiple repos | Copies artifact to target project, removes the target's pointer, updates the `dependents` list in the architecture source. Architecture source stays in place. |
| `ve chunk demote <name> <target>` | Full-collapse — scope has definitively landed in one repo | Strips `org/repo::` prefixes from `code_paths` and `code_references`, removes the `dependents` block, deletes pointer dirs in all other participating projects, and removes the architecture source directory entirely. |

### When to use `ve chunk demote`

Use `ve chunk demote` when **all** of the following are true:

1. The chunk is implemented — `status` is `ACTIVE` or `IMPLEMENTING` and the
   work is known to be single-project.
2. Every `code_path` in the chunk's GOAL.md references only the target project
   (or carries no cross-repo prefix at all).
3. All other participating projects only have `external.yaml` pointer directories
   (not real GOAL.md content).

The command **refuses** with a clear error if any `code_path` references a repo
other than the target, pointing at the offending entries. This prevents silent
corruption of frontmatter.

### What `ve chunk demote` does

Running `ve chunk demote <chunk_name> <target_project>` from a task directory:

1. Validates the architecture source exists and the target project has a pointer.
2. Verifies all `code_paths` are scoped to the target (or bare).
3. Copies `GOAL.md` and `PLAN.md` to `<target_project>/docs/chunks/<chunk_name>/`.
4. Rewrites frontmatter in the target:
   - Strips `org/repo::` prefix from `code_paths` and `code_references[].ref`
   - Removes the `dependents` block entirely
5. Deletes `external.yaml` pointer directories in every other participating project.
6. Removes `architecture/docs/chunks/<chunk_name>/` from the filesystem.

Decision documents at `architecture/docs/reviewers/baseline/decisions/<chunk_name>_*.md`
are **preserved** — these are review-history artifacts, not chunk artifacts.

### Invariants enforced

- No dangling pointer directories left after demotion.
- No `org/repo::` prefix pollution in the demoted chunk's frontmatter.
- No silent demotion when scope hasn't actually collapsed (scope validator rejects it).
- The operation is **idempotent**: re-running a partially-completed demotion
  finishes the remaining steps rather than failing or duplicating state.

### After demotion: commit changes

`ve chunk demote` makes filesystem changes only — it does not run `git` commands.
After a successful demotion, commit the changes in each affected repository:

```bash
# In the target project
git add docs/chunks/<chunk_name>/
git commit -m "Demote <chunk_name> from architecture (full-collapse)"

# In each other participating project
git rm -r docs/chunks/<chunk_name>/
git commit -m "Remove external pointer for demoted chunk <chunk_name>"

# In the architecture repo
git rm -r docs/chunks/<chunk_name>/   # or verify it's already absent
git commit -m "Remove architecture source for demoted chunk <chunk_name>"
```

### When NOT to use `ve chunk demote`

- When implementation is **not yet complete** and scope is still uncertain.
- When any `code_path` references more than one repository — use `ve task demote`
  (which leaves the architecture source intact) or split the chunk first.
- When another participating project has real GOAL.md content (not a pointer) — the
  command will refuse and tell you which project has conflicting content.
