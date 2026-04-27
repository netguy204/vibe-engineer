---
status: ACTIVE
ticket: null
parent_chunk: skill_chunk_execute
code_paths:
- src/templates/commands/chunk-execute.md.jinja2
code_references:
  - ref: src/templates/commands/chunk-execute.md.jinja2
    implements: "Review → implement feedback loop in chunk-execute skill template (steps 5-7)"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- landing_page_umami_events
- pip_publish_workflow
- skill_chunk_create_improve
- skill_chunk_execute
- skill_narrative_execute
- skill_orchestrator_inject
---

# Chunk Goal

## Minor Goal

Extend the `/chunk-execute` skill template with a review → implement
feedback loop. The skill runs plan → implement → review → complete; when
`/chunk-review` finds issues, the skill loops back to `/chunk-implement`
with the review feedback, then re-reviews, iterating until the review is
clean.

The correct workflow is:

```
plan → implement → review
                     ↓
              issues found? → implement (with feedback) → review → ...
                     ↓
              clean? → complete
```

This was identified as a required behavior from real-world usage (~15 chunk
executions in the gsr-model-migration task), where every chunk went through
at least one review iteration catching real bugs (train/serve skew, missing
parameter threading, type mismatches, circular imports).

The template is at `src/templates/commands/chunk-execute.md.jinja2`. Read it,
understand the current flow, and add the review loop.

## Success Criteria

- `/chunk-execute` loops review → implement when review finds issues
- The loop has a reasonable max iteration limit (e.g., 5) to prevent infinite loops
- Review feedback is passed to the next implement step so the agent knows what to fix
- Clean review proceeds to complete as before
- The rendered `.claude/commands/chunk-execute.md` reflects the updated template
  (run `ve init` to re-render)

## Relationship to Parent

Parent chunk `skill_chunk_execute` created the initial `/chunk-execute` skill.
The overall structure (accept chunk name, plan, implement, complete) remains
valid. The deficiency is the missing review → implement feedback loop — the
skill runs review once but doesn't iterate on findings.