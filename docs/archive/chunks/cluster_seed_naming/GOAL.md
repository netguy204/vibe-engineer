---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/commands/chunk-create.md.jinja2
code_references:
  - ref: src/templates/commands/chunk-create.md.jinja2
    implements: "Cluster seed naming guidance in step 1 of /chunk-create skill"
narrative: null
investigation: alphabetical_chunk_grouping
subsystems: []
created_after:
- chunk_create_guard
- orch_attention_reason
- orch_inject_validate
- deferred_worktree_creation
---

# Chunk Goal

## Minor Goal

Add a characteristic naming prompt to the `/chunk-create` skill that helps operators choose good prefix names when seeding new clusters. When no similar existing chunks are found (meaning the new chunk will seed a potential cluster), prompt the operator with the "initiative noun" question.

This addresses the bootstrapping case where similarity-based prefix suggestion cannot help because there are no similar chunks yet. Poor seed names cascade—subsequent chunks inherit via similarity, so the first chunk in a cluster is the critical naming decision.

See `docs/investigations/alphabetical_chunk_grouping/OVERVIEW.md` for the full investigation rationale.

## Success Criteria

1. **Naming guidance added to `/chunk-create` skill** - The skill template includes a prompt asking operators to consider the initiative noun when naming chunks that will seed new clusters.

2. **Prompt uses the characteristic question format** - The guidance asks "What initiative does this chunk advance?" rather than prescribing specific prefixes.

3. **Examples of good and bad prefixes included** - The prompt includes examples:
   - Good: initiative nouns like `ordering_`, `taskdir_`, `template_`
   - Bad: artifact types like `chunk_`, `fix_`, `cli_`, or generic terms like `api_`, `util_`, `misc_`

4. **Narrative/investigation suggestion included** - The prompt suggests looking at related narratives or investigations for initiative names when available.

