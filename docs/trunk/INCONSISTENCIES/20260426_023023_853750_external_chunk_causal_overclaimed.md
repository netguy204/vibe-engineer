---
discovered_by: audit batch 10e
discovered_at: 2026-04-26T02:30:23
severity: low
status: open
artifacts:
  - docs/chunks/external_chunk_causal/GOAL.md
---

## Claim

`docs/chunks/external_chunk_causal/GOAL.md` body and Context section name a class
and file path that no longer exist:

- Line 49 (Minor Goal): "This chunk adds `created_after: list[str]` to the `ExternalChunkRef` model"
- Success Criterion 1 (line 59): "**ExternalChunkRef model updated**: `created_after: list[str] = []` field added to `ExternalChunkRef` in `src/models.py`"
- Context lines 83-86: "src/artifact_ordering.py lines 276-280", "src/artifact_ordering.py lines 313-318", "src/models.py lines 215-226: Current `ExternalChunkRef` structure"

## Reality

The class is named `ExternalArtifactRef` (not `ExternalChunkRef`) and lives in
`src/models/references.py` (not `src/models.py`). The chunk's own
`code_references` correctly point at `src/models/references.py#ExternalArtifactRef`,
which carries `created_after: list[str] = []` at line 340 — so the feature was
implemented; only the prose names of the class and file are stale.

```
$ grep -n "ExternalChunkRef\|ExternalArtifactRef" src/models/references.py
327:class ExternalArtifactRef(BaseModel):
332:    replacement for ExternalChunkRef that supports all workflow artifact types.
340:    created_after: list[str] = []  # Local causal ordering
```

`src/models.py` does not exist as a file:

```
$ ls src/models.py
ls: src/models.py: No such file or directory
```

The successor chunk `consolidate_ext_refs` renamed `ExternalChunkRef` to
`ExternalArtifactRef` and the models module was split into `src/models/`
package (with `references.py`, `chunk.py`, etc.) — both changes happened
after this chunk landed.

The retrospective tell at line 47 ("Currently, external chunks (referenced via
`external.yaml`) are invisible to `ArtifactIndex`...") describes a true
pre-state, but a tense rewrite would substitute the stale class/file names
into a present-tense claim, replacing one stale fact with another. Veto fires.

## Workaround

None. The chunk's `code_references` frontmatter is correct, so cross-reference
tooling does not break. Only human readers of the prose are misled.

## Fix paths

1. (Preferred) Update the GOAL.md prose to reference `ExternalArtifactRef` and
   `src/models/references.py`, and rewrite the "Currently, ..." paragraph in
   present tense (the post-state holds: `_enumerate_artifacts` reads
   `external.yaml`, `_TIP_ELIGIBLE_STATUSES` includes `EXTERNAL`,
   `find_tips`/`get_ordered`/`get_ancestors` handle external chunks). This is a
   prose-only fix; the implementation already matches the success criteria.
2. (Alternative) Mark this chunk HISTORICAL once the prose-fix successor lands,
   since `consolidate_ext_refs` already owns the rename and the
   present-tense system description belongs in the
   `workflow_artifacts`/`cross_repo_operations` subsystem docs rather than in
   this chunk's GOAL.
