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
