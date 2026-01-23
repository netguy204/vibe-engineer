---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/commands/chunk-create.md.jinja2
  - src/templates/commands/chunk-complete.md.jinja2
  - tests/test_friction_workflow.py
code_references:
  - ref: src/templates/commands/chunk-create.md.jinja2
    implements: "Friction entry selection workflow in step 6 - prompts operator to select friction entries, adds to chunk frontmatter, updates FRICTION.md proposed_chunks"
  - ref: src/templates/commands/chunk-complete.md.jinja2
    implements: "Friction resolution reporting in step 12 - detects friction_entries in chunk, reports resolution status for full/partial scope"
  - ref: tests/test_friction_workflow.py#TestFrictionWorkflowIntegration
    implements: "Test helper base class with setup methods for friction log and chunk creation"
  - ref: tests/test_friction_workflow.py#TestChunkCreateWithFriction
    implements: "Tests for /chunk-create friction entry selection - frontmatter and status transitions"
  - ref: tests/test_friction_workflow.py#TestChunkCompleteWithFriction
    implements: "Tests for /chunk-complete friction resolution - RESOLVED status for ACTIVE chunks"
  - ref: tests/test_friction_workflow.py#TestFrictionWorkflowEdgeCases
    implements: "Edge case tests - multi-theme, partial scope, existing proposed_chunks"
narrative: null
investigation: friction_log_artifact
subsystems: []
friction_entries: []
created_after:
- orch_dashboard
- friction_noninteractive
---

# Chunk Goal

## Minor Goal

Integrate friction tracking into the `/chunk-create` and `/chunk-complete` workflows to complete the bidirectional linking between friction entries and chunks. This enables the full friction-to-resolution lifecycle:

```
Experience friction → /friction-log → Pattern accumulation → /chunk-create (with friction) → /chunk-complete → Friction resolved
```

The investigation designed a workflow where:
- `/chunk-create` prompts for friction entries being addressed and updates those entries to ADDRESSED status
- `/chunk-complete` checks if the chunk has `friction_entries` and prompts to mark them as RESOLVED

This completes the friction lifecycle, enabling "why did we do this work?" traceability from implementation back to accumulated pain points.

## Success Criteria

- `/chunk-create` skill prompts operator to specify friction entries being addressed (if any)
- When friction entries are specified, they are added to chunk frontmatter's `friction_entries` array
- `/chunk-create` updates referenced friction entry status from OPEN to ADDRESSED
- `/chunk-complete` skill detects `friction_entries` in chunk frontmatter
- `/chunk-complete` prompts: "Mark these friction entries as RESOLVED?"
- When confirmed, updates friction log entries from ADDRESSED to RESOLVED
- Handles both full and partial scope (entry may be addressed by multiple chunks)
- Integrates with existing skill patterns and validation
- Depends on friction_template_and_cli and friction_chunk_linking chunks being completed first