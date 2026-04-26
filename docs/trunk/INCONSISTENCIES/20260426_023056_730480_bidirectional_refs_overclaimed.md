---
discovered_by: audit batch 10g
discovered_at: 2026-04-26T02:30:56Z
severity: low
status: open
artifacts:
  - docs/chunks/bidirectional_refs/GOAL.md
---

# Claim

`docs/chunks/bidirectional_refs/GOAL.md` Success Criteria #3 ("SubsystemRelationship model") asserts:

> Create Pydantic model (inverse of `ChunkRelationship`) with:
> - `subsystem_id`: string matching `{NNNN}-{short_name}` pattern
> - `relationship`: literal "implements" | "uses"

# Reality

`SubsystemRelationship.subsystem_id` no longer matches the `{NNNN}-{short_name}` pattern. Per `src/models/references.py:29`:

```python
ARTIFACT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")
```

…and `validate_subsystem_id` (line 193) routes `subsystem_id` through `_validate_artifact_id`, which uses `ARTIFACT_ID_PATTERN`. The `{NNNN}-` prefix was removed by the `ordering_remove_seqno` chunk; only the shortname slug is accepted now.

The same prefix-pattern reference appears implicitly in the `code_references` (e.g., `validator updated to accept both legacy and new chunk ID formats`), but those entries are honest about the dual-format reality. The SC text is not.

# Workaround

None needed; the model's actual validator has moved on. The GOAL.md text just hasn't followed.

# Fix paths

1. Sweep stale `{NNNN}-{short_name}` references out of chunk GOAL.md SCs in a post-`ordering_remove_seqno` cleanup chunk (this would also cover `subsystem_status_transitions` and `subsystem_docs_update`).
2. Historicalize this chunk once a successor explicitly owns the bidirectional-reference contract under post-prefix naming.

# Audit context

Detected by `intent_active_audit` batch 10g. The SC describes a now-stale validation pattern, so the veto rule fires on prose rewrites. All other code_references in this chunk's frontmatter resolve correctly (verified by symbol lookup in `src/models/references.py`, `src/chunks.py`, `src/subsystems.py`, `src/cli/chunk.py`, `src/cli/subsystem.py`, `src/chunk_validation.py`, `src/integrity.py`, and `src/templates/chunk/GOAL.md.jinja2`).
