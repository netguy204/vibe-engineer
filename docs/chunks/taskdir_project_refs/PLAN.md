---
status: DRAFT
---
# Plan: taskdir_project_refs

## Overview

Add a "Project References" section to the task CLAUDE.md template that lists key documentation files from each participating project, giving agents clear breadcrumbs to project constraints.

## Implementation Steps

### Step 1: Update the task CLAUDE.md template

**File:** `src/templates/task/CLAUDE.md.jinja2`

Add a new "Project References" section after the existing "Projects" table. The section will:

1. Explain the rule precedence principle: when working within a project, that project's rules take precedence over conflicting rules from other projects
2. For each participating project, list three key files as bullet points:
   - `CLAUDE.md` - Project-specific agent instructions
   - `docs/trunk/GOAL.md` - Project goals and constraints
   - `docs/trunk/TESTING_PHILOSOPHY.md` - Testing approach

**Template logic:**
- Extract repo name from org/repo format using Jinja2's `split` filter: `{{ project.split('/')[-1] }}`
- Use relative paths from task root: `./repo-name/path`

**Example output for a project `anthropics/claude-code`:**
```markdown
### claude-code

- `./claude-code/CLAUDE.md` - Project-specific agent instructions
- `./claude-code/docs/trunk/GOAL.md` - Project goals and constraints
- `./claude-code/docs/trunk/TESTING_PHILOSOPHY.md` - Testing approach
```

### Step 2: Write a test for the template rendering

**File:** Add test to existing task init tests

Verify that:
- The "Project References" section appears in rendered output
- Each project has its three expected file references
- The repo name is correctly extracted from org/repo format
- The rule precedence guidance is present

## Risks and Mitigations

- **Risk:** Template syntax error breaks task init
  - **Mitigation:** Test the template rendering with sample data before committing

## Acceptance Verification

After implementation, run `ve task init` in a test directory with multiple projects and confirm the generated CLAUDE.md includes the Project References section with correct paths.
