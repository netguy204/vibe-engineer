---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: ["src/templates/chunk/GOAL.md.jinja2"]
code_references:
  - ref: src/templates/chunk/GOAL.md.jinja2
    implements: "CREATED_AFTER documentation in chunk GOAL.md template"
narrative: null
investigation: null
subsystems: []
created_after:
- narrative_backreference_support
- orch_inject_path_compat
- orch_submit_future_cmd
---

# Chunk Goal

## Minor Goal

Clarify the semantics of the `created_after` field in chunk GOAL.md templates to prevent agents from confusing **causal ordering** (what has shipped) with **implementation dependencies** (what must exist for this chunk to work).

**The problem**: Agents commonly misinterpret `created_after` as "chunks that must be implemented before this one can work" and incorrectly set it to reference FUTURE chunks. This happened when creating `orch_conflict_oracle` - it was incorrectly set to `["orch_attention_queue"]` (a FUTURE chunk) instead of the actual tips.

**The fix**: Update the GOAL.md template's comment block to explicitly contrast these concepts and guide agents to the correct behavior.

## Success Criteria

1. **Template updated**: The GOAL.md Jinja2 template (`src/templates/chunks/GOAL.md.jinja2`) includes clear documentation distinguishing:
   - `created_after` = causal ordering (the tips when this chunk was created; always references ACTIVE/shipped chunks)
   - Implementation dependencies = tracked elsewhere (investigation `proposed_chunks` order, design docs, narrative sequencing)

2. **Anti-pattern documented**: The template explicitly warns against setting `created_after` to FUTURE chunks

3. **Guidance on where to track design dependencies**: The template points agents to the correct places for sequencing future work

4. **Regenerated files updated**: Running `ve init` propagates the template changes to rendered GOAL.md files

