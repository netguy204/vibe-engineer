---
discovered_by: audit batch 10g
discovered_at: 2026-04-26T02:30:56Z
severity: medium
status: open
artifacts:
  - docs/chunks/ordering_remove_seqno/GOAL.md
---

# Claim

`docs/chunks/ordering_remove_seqno/GOAL.md` `code_references` lists:

```yaml
- ref: src/models/shared.py#extract_short_name
  implements: "Utility to extract short_name from directory names (handles both legacy and new formats)"
```

The implication: a public helper `extract_short_name` lives in `src/models/shared.py` and is responsible for stripping `{NNNN}-` prefixes off directory names so old and new naming schemes can coexist.

# Reality

There is no `extract_short_name` function in the codebase:

```
$ grep -rn "def extract_short_name\|extract_short_name" src/ tests/
(no matches)
```

`src/models/shared.py` contains `_require_valid_dir_name` and `_require_valid_repo_ref` but no `extract_short_name`. The "handles both legacy and new formats" affordance the chunk describes is not implemented as a named utility — directory parsing in `src/subsystems.py` (`is_subsystem_dir`), `src/chunks.py` (`find_duplicates`, `resolve_chunk_id`), etc., now treats the directory name *as* the short name without a stripping step, because the legacy `{NNNN}-` directories were renamed wholesale during the migration.

The chunk's other code_references resolve correctly (verified `ARTIFACT_ID_PATTERN`, `ChunkRelationship.validate_chunk_id`, `SubsystemRelationship.validate_subsystem_id`, `Chunks.find_duplicates`, `Chunks.create_chunk`, `Chunks.resolve_chunk_id`, `Chunks.find_overlapping_chunks`, `Subsystems.find_by_shortname`, `Subsystems.is_subsystem_dir`, `external_refs.create_external_yaml`, `task.artifact_ops.create_task_chunk`, `ArtifactIndex.get_ancestors`, and `scripts/migrate_artifact_names.py`).

Success Criteria #5 ("Both patterns supported during transition") is also stale in the same direction: the dual-format support was a transitional contract, and the migration step (SC #3) eliminated the legacy directories, so the "transition" framing no longer matches reality. The criteria are framed as in-flight work but the work has shipped.

# Workaround

None — the chunk's actual outcome is shipped. The `code_references` entry just points at a function that was never created (or was inlined and never named).

# Fix paths

1. **Drop the `extract_short_name` `code_references` entry.** Either remove it (if the function was never created) or replace it with the actual location of the parsing logic (currently distributed across `is_subsystem_dir`, `find_duplicates`, etc.).
2. Tighten SC #5 in a follow-up to acknowledge the dual-format support was transitional and is no longer required.

# Audit context

Detected by `intent_active_audit` batch 10g. Symmetric verification (Step 5 of the audit protocol) caught this — declared code_references didn't match the named symbols. Veto fires on prose rewrite for this chunk because the over-claim is in the metadata + SC, so any tense rewrite would substitute one false claim for another.
