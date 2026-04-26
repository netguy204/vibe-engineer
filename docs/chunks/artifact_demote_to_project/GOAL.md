---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/task/demote.py
- src/task/exceptions.py
- src/task/__init__.py
- src/cli/task.py
- src/cli/chunk.py
- tests/test_task_demote.py
code_references:
  - ref: src/task/demote.py#demote_artifact
    implements: "Core demotion logic: moves external artifact to project-local, validates dependents, copies files, restores created_after, cleans up external references"
  - ref: src/task/demote.py#scan_demotable_artifacts
    implements: "Auto-scan logic: iterates external artifacts, identifies single-dependent candidates eligible for demotion"
  - ref: src/task/demote.py#read_artifact_frontmatter
    implements: "Frontmatter parsing helper for reading dependents and metadata from external artifacts"
  - ref: src/task/exceptions.py#TaskDemoteError
    implements: "Exception class for demotion error handling"
  - ref: src/task/__init__.py
    implements: "Exports demote_artifact, scan_demotable_artifacts, read_artifact_frontmatter, and TaskDemoteError"
  - ref: src/cli/task.py#demote
    implements: "CLI command: ve task demote <artifact>, --auto, --auto --apply modes"
  - ref: src/cli/chunk.py#_complete_task_chunk
    implements: "Chunk completion in task context with auto-demotion for single-project chunks"
  - ref: src/cli/chunk.py#_auto_demote_if_eligible
    implements: "Auto-demotion helper for project context: checks external.yaml and demotes if eligible"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- episodic_ingest_external
---

# Chunk Goal

## Minor Goal

The `ve task demote` command moves task-level artifacts down to project-level
when they only reference a single project. This is the inverse of the
`promote_artifact()` flow (local → external). Demote moves an artifact from the
external artifact repo into the single project that actually uses it,
converting it from an external reference to a native local artifact.

### Why demotion matters

In a task context, all artifacts are created in the external artifact repo by
default, with `external.yaml` pointers in each participating project. In
practice, many chunks and investigations end up touching only one project's
code. Task-level artifacts add indirection without benefit when this happens —
operators must resolve external references to read what is effectively local
work. Demotion collapses that indirection back into the owning project.

### Capabilities

- `ve task demote <artifact>` — Demote a single named artifact. Moves the
  canonical GOAL.md/OVERVIEW.md from the external repo into the single project
  that references it, removes the `external.yaml` pointer, and cleans up the
  dependent entry on the external artifact.

- `ve task demote --auto` — Scan all task-level artifacts and identify those
  whose `code_paths` and `code_references` (non-project-qualified) belong to a
  single project. Report what would be demoted (dry-run by default), then demote
  with `--apply`.

- **Automatic demotion at chunk-complete** — `ve chunk complete` in a task
  context checks whether the completed chunk only references a single project
  and, if so, automatically demotes it and logs what happened.

### Architecture context

- `promote_artifact()` in `src/task/promote.py` is the forward path (local →
  external). Demote is the reverse: external → local.
- `remove_artifact_from_external()` in `src/task/external.py` already handles
  cleaning up `external.yaml` files, removing empty directories, and stripping
  dependent entries. Reuse this.
- `identify_source_project()` in `src/task/promote.py` resolves which project
  an artifact path belongs to — useful for the `--auto` scanner.
- `code_references` use `org/repo::file#symbol` for cross-project refs. A chunk
  with no `::` qualifiers and `code_paths` all within one project is a demotion
  candidate.

## Success Criteria

- `ve task demote my_chunk` moves the chunk from external repo to the owning
  project's `docs/chunks/my_chunk/` directory, replacing external.yaml with
  the actual GOAL.md and PLAN.md
- `ve task demote --auto` scans all external artifacts and identifies
  single-project candidates
- `ve task demote --auto --apply` demotes all candidates in one pass
- Dependent entries are cleaned from the external artifact's frontmatter
- External.yaml files and empty directories are removed from all projects
  that had pointers
- Code backreferences in source files remain valid (paths don't change since
  local `docs/chunks/name/` directory already exists in the owning project)
- `ve chunk complete` in task context auto-demotes single-project chunks
- Tests cover: single artifact demote, auto-scan detection, auto-apply bulk
  demote, multi-project artifact correctly skipped, chunk-complete integration,
  cleanup of dependent entries and external.yaml