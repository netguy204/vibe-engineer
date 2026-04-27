---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/chunk/GOAL.md.jinja2
- tests/test_chunks.py
code_references:
- ref: src/templates/chunk/GOAL.md.jinja2
  implements: Jinja2 template using default filter to render null for missing ticket_id
- ref: tests/test_chunks.py#TestTicketFrontmatter
  implements: Unit tests verifying ticket field renders correctly in frontmatter
- ref: tests/test_chunks.py#TestTicketFrontmatter::test_ticket_renders_null_when_ticket_id_is_none
  implements: Test that None ticket_id renders as YAML null
- ref: tests/test_chunks.py#TestTicketFrontmatter::test_ticket_renders_value_when_ticket_id_provided
  implements: Test that provided ticket_id renders correctly
narrative: null
created_after:
- subsystem_schemas_and_model
---

# Chunk Goal

## Minor Goal

The chunk GOAL.md template outputs valid YAML `null` instead of Python's `None` when no ticket ID is provided.

`src/templates/chunk/GOAL.md.jinja2` renders `ticket: {{ ticket_id | default('null', true) }}`, so a missing `ticket_id` produces YAML `null` rather than the literal string `None`. The `default` filter with `true` as its second argument treats `None` as undefined and substitutes the `null` literal.

This advances the trunk goal's **Required Properties** by keeping generated artifacts immediately valid without manual correction—a prerequisite for maintaining document health over time.

## Success Criteria

1. **Template uses Jinja2 filter** to convert Python `None` to YAML `null`:
   - Change `ticket: {{ ticket_id }}` to `ticket: {{ ticket_id | default('null', true) }}` or equivalent
   - The `default` filter with `true` as second argument treats `None` as undefined

2. **New chunks render valid YAML**:
   - Running `ve chunk start test_chunk` produces `ticket: null` (not `ticket: None`)
   - Running `ve chunk start test_chunk TICKET-123` produces `ticket: TICKET-123`

3. **Unit test** verifies both cases:
   - Template renders `null` when ticket_id is None
   - Template renders the ticket ID when provided