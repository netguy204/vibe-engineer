---
status: ACTIVE
ticket: null
success_criteria:
- Task CLAUDE.md includes a 'Project References' section listing key files from each
  member project
- Each project entry references CLAUDE.md, docs/trunk/GOAL.md, and docs/trunk/TESTING_PHILOSOPHY.md
- References use relative paths from task root (e.g., ./project-name/CLAUDE.md)
- Template gracefully handles projects that may be missing some files
created_at: '2026-01-22T11:59:20.479769'
---
# taskdir_project_refs

## Goal

When `ve task init` creates a task directory, the generated CLAUDE.md should include references to key documentation files from each participating project. This gives agents strong breadcrumbs to follow when they need to understand the constraints and context of each project involved in the task.

Currently, the task CLAUDE.md lists participating projects by name but doesn't point to their key documentation. An agent starting in the task directory has to discover these files on their own.

## Success Criteria

1. **Task CLAUDE.md includes a "Project References" section** - Lists key files from each participating project, grouped by project with bullet points
2. **Each project entry references three key files:**
   - `CLAUDE.md` - Project-specific agent instructions
   - `docs/trunk/GOAL.md` - Project goals and constraints
   - `docs/trunk/TESTING_PHILOSOPHY.md` - Testing approach
3. **References use relative paths from task root** - e.g., `./vibe-engineer/CLAUDE.md`
4. **Includes rule precedence guidance** - Explains that when working within a project, that project's internal rules take precedence over any conflicting rules from other projects

## Notes

- The template is at `src/templates/task/CLAUDE.md.jinja2`
- Task init happens in `src/task_init.py`
- The template receives `external_artifact_repo` and `projects` as context
- Projects are org/repo strings (e.g., "anthropics/claude-code"), so we need to extract the repo name for the relative path
- Just list expected file locations - all VE-initialized projects will have these files