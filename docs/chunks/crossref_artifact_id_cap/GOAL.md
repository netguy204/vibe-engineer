---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/validation.py
- src/models/shared.py
- src/cli/utils.py
- docs/trunk/SPEC.md
- tests/test_validation.py
- tests/test_task_models.py
- tests/test_chunk_start.py
- tests/test_narrative_create.py
code_references:
- ref: src/validation.py
  implements: "MAX_PATH_COMPONENT_LENGTH constant: the named real constraint (255-byte filesystem path-component limit) replacing the arbitrary 31-char cap"
- ref: src/validation.py#validate_identifier
  implements: "Default length cap anchored to MAX_PATH_COMPONENT_LENGTH"
- ref: src/models/shared.py#_require_valid_dir_name
  implements: "ExternalArtifactRef.artifact_id length bounded by path legality, making long descriptive artifact names representable"
- ref: src/cli/utils.py#validate_short_name
  implements: "Creation-side names accept the same grammar pointers accept, so both validators agree by construction"
- ref: tests/test_validation.py#TestDefaultLengthCap
  implements: "Default-cap boundary coverage: 36-char descriptive name and 255 pass, 256 rejected naming the limit"
- ref: tests/test_task_models.py#TestExternalArtifactRef::test_external_artifact_ref_accepts_long_descriptive_artifact_id
  implements: "Field-defect regression test: 36-char artifact_id validates"
- ref: tests/test_task_models.py#TestExternalArtifactRef::test_external_artifact_ref_accepts_artifact_id_at_path_component_limit
  implements: "artifact_id accepted at the 255-char filesystem limit"
- ref: tests/test_task_models.py#TestExternalArtifactRef::test_external_artifact_ref_rejects_artifact_id_over_path_component_limit
  implements: "artifact_id over the filesystem limit rejected with the limit named"
- ref: tests/test_chunk_start.py#TestShortNameValidation
  implements: "ve chunk create accepts descriptive names beyond 31 chars, rejects over 255"
- ref: tests/test_chunk_start.py#TestCombinedNameLengthValidation
  implements: "Chunk directory-name length boundary moved to the 255-char path-component limit"
- ref: tests/test_narrative_create.py#TestNarrativeShortNameValidation
  implements: "ve narrative create accepts descriptive names beyond 31 chars, rejects over 255"
narrative: reference_integrity
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- crossref_rename_integrity
- validation_backref_allowlist
---

# Chunk Goal

## Minor Goal

Identifier length validation is anchored to the real constraint — path legality — rather than an arbitrary cap. `validate_identifier` (src/validation.py) defaults its length limit to `MAX_PATH_COMPONENT_LENGTH` (255, the per-component byte limit on APFS/ext4/NTFS, which equals characters for the ASCII identifier charset), and both `ExternalArtifactRef.artifact_id` (src/models/references.py, via `_require_valid_dir_name`) and the creation-side `validate_short_name` inherit that default. Ordinary descriptive artifact names like `database_and_sagemaker_savings_plans` (36 chars, previously 3 unrepresentable field defects) are expressible in external pointers and creatable locally, so a pointer can never name an artifact that local creation refuses. Charset validation and caps derived from genuine external constraints (GitHub's 39-char org / 100-char repo limits) are unchanged.

## Success Criteria

- `ExternalArtifactRef(artifact_type="chunk", artifact_id="database_and_sagemaker_savings_plans", repo=...)` validates successfully (36-character id, the field-defect case).
- Identifier validation is anchored to a real constraint: the filesystem path-component limit (255 bytes for the ASCII identifier charset), expressed as a named constant in `src/validation.py`, not a magic number at call sites.
- Charset validation is unchanged: identifiers still reject spaces, `/`, `:` and other characters outside `[a-zA-Z0-9_.-]` (dots only where `allow_dot=True`).
- A 256-character identifier is still rejected, with an error message naming the actual limit.
- Same-origin caps are lifted consistently: `validate_short_name` (governing `ve chunk create`, `ve narrative create`, `ve investigation create`, `ve subsystem discover`) accepts the same names `ExternalArtifactRef.artifact_id` accepts, so a pointer can never reference a name that local creation refuses.
- Caps derived from genuine external constraints are untouched: GitHub's 39-char org and 100-char repo limits in `_require_valid_repo_ref`.
- docs/trunk/SPEC.md's `^[a-zA-Z0-9_-]{1,31}$` patterns and Limits table reflect the new limit.
- All existing tests pass; tests asserting rejection of 32-40 character names are updated to assert acceptance, with new boundary tests at 255/256.