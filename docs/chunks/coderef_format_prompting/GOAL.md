---
status: HISTORICAL
ticket: null
parent_chunk: null
code_paths:
- src/models.py
- src/chunks.py
- src/task_utils.py
- src/templates/chunk/GOAL.md.jinja2
- tests/test_models.py
- tests/test_chunks.py
code_references:
  - ref: src/models.py#SymbolicReference::validate_ref
    implements: "Improved org/repo format error messages with contextual details"
  - ref: src/chunks.py#Chunks::parse_chunk_frontmatter_with_errors
    implements: "Frontmatter parsing that surfaces validation error details"
  - ref: src/chunks.py#Chunks::create_chunk
    implements: "Projects parameter for task-context template rendering"
  - ref: src/task_utils.py#create_task_chunk
    implements: "Pass projects to chunk template in task context"
  - ref: src/templates/chunk/GOAL.md.jinja2
    implements: "Full org/repo format examples in task context"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: implementation
created_after:
- taskdir_context_cmds
---

# Chunk Goal

## Minor Goal

Fix the mismatch between the chunk template's code reference examples and the
`SymbolicReference` validator's requirements in task context.

**The bug:** The GOAL.md template (`src/templates/chunk/GOAL.md.jinja2` lines
54-61) shows examples with short repo names:
```yaml
- ref: dotter::xr#worktrees
- ref: vibe-engineer::src/chunks.py#Chunks::create
```

But the `SymbolicReference.validate_ref()` method (`src/models.py:422`) requires
full `org/repo::` format, rejecting short names like `pybusiness::`.

Agents follow the template examples exactly, then `ve chunk validate` fails with
an unhelpful "Could not parse frontmatter" error that doesn't explain the actual
format requirement.

**Three fixes needed:**

1. **Template fix**: Update examples to use full `org/repo::` format and add
   guidance telling agents where to find project names
2. **Template expansion**: During `ve task init` (or chunk create in task
   context), expand template examples using actual project names from
   `.ve-task.yaml` so agents see real examples like `cloudcapitalco/pybusiness::`
   instead of generic `acme/dotter::`
3. **Validator fix**: Improve error message to explain the required format so
   agents (and chunk-complete) can self-correct

## Success Criteria

- Template examples in `src/templates/chunk/GOAL.md.jinja2` use full `org/repo::`
  format and include guidance: "See `.ve-task.yaml` projects list for org/repo names"
- When rendering chunk GOAL.md in task context, examples use actual project names
  from the task config (e.g., `cloudcapitalco/pybusiness::` not `acme/dotter::`)
- `SymbolicReference.validate_ref()` error message explicitly states:
  "project qualifier must be in 'org/repo' format (e.g., 'acme/project::path'),
  got 'pybusiness'"
- Error message includes the actual invalid value to help debugging
- `parse_chunk_frontmatter()` surfaces the validation error detail instead of
  returning generic "Could not parse frontmatter"
- Existing tests pass; new tests cover template expansion and improved error message

