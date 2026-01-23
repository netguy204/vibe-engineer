---
status: ACTIVE
ticket: null
narrative: task_artifact_discovery
code_paths:
- src/models.py
- src/external_refs.py
- src/external_resolve.py
- src/sync.py
- src/ve.py
- src/task_utils.py
- src/templates/commands/chunk-complete.md.jinja2
- docs/subsystems/cross_repo_operations/OVERVIEW.md
- tests/test_sync.py
- tests/test_sync_cli.py
- tests/test_sync_integration.py
- tests/test_external_refs.py
- tests/test_external_resolve.py
- tests/test_external_resolve_cli.py
code_references:
- ref: src/models.py#ExternalArtifactRef
  implements: "External artifact reference model with optional pinned field for backward compatibility"
- ref: src/external_refs.py#create_external_yaml
  implements: "External.yaml creation without pinned SHA"
- ref: src/external_resolve.py#resolve_artifact_task_directory
  implements: "External resolution always using HEAD (pinned logic removed)"
- ref: src/external_resolve.py#resolve_artifact_single_repo
  implements: "Single-repo resolution always using HEAD/track"
- ref: src/task_utils.py#create_task_chunk
  implements: "Chunk creation without pinned SHA parameter"
- ref: src/task_utils.py#create_task_narrative
  implements: "Narrative creation without pinned SHA parameter"
- ref: src/task_utils.py#create_task_investigation
  implements: "Investigation creation without pinned SHA parameter"
- ref: src/task_utils.py#create_task_subsystem
  implements: "Subsystem creation without pinned SHA parameter"
- ref: src/ve.py#resolve
  implements: "External resolve CLI without --at-pinned option"
- ref: docs/subsystems/cross_repo_operations/OVERVIEW.md
  implements: "Updated subsystem invariant: external refs always resolve to HEAD"
subsystems:
- subsystem_id: cross_repo_operations
  relationship: implements
created_after:
- claudemd_magic_markers
---
# external_artifact_unpin

## Goal

Remove the concept of external artifact pinning from VE. External artifacts should
always resolve to the latest version (HEAD) rather than a pinned SHA.

**Problem**: The current pinning mechanism creates maintenance burden without value:
- `ve sync` creates file noise across all repos with external references
- Pinned versions are always advanced without thought
- "Point at latest" is the actual intent; pinning is ceremony

**Solution**: Remove pinning entirely:
1. Remove `pinned_sha` field from `ExternalArtifactRef` model
2. Remove `ve sync` command (no longer needed)
3. External resolution always fetches/uses HEAD
4. Migrate existing `external.yaml` files to remove `pinned_sha`

**Before** (external.yaml):
```yaml
artifact_type: chunk
artifact_name: some_feature
external_repo: git@github.com:org/external-repo.git
pinned_sha: abc123  # Always advancing this anyway
```

**After** (external.yaml):
```yaml
artifact_type: chunk
artifact_name: some_feature
external_repo: git@github.com:org/external-repo.git
```

## Success Criteria

- ExternalArtifactRef model no longer has pinned_sha field
- external.yaml files no longer contain pinned_sha
- `ve sync` command removed or repurposed (no SHA updating)
- External resolution always uses HEAD of external repo
- Existing external.yaml files migrated (pinned_sha removed)
- Tests updated to reflect unpinned behavior
- cross_repo_operations subsystem docs updated

## Relationship to Narrative

This chunk is part of the `task_artifact_discovery` narrative.

**Advances**: Simplifies the external artifact system, making it easier for agents
to understand and use. Removes the noise that `ve sync` creates.

**Relationship to other chunks**: This simplification affects `external_resolve_enhance`
by removing the need to think about pinned versions - resolution just means "latest".

## Notes

**Key files to modify**:
- `src/models.py` - `ExternalArtifactRef` model (remove pinned_sha)
- `src/external_refs.py` - external reference loading/creation
- `src/external_resolve.py` - resolution logic (always HEAD)
- `src/sync.py` - remove this file
- `src/ve.py` - remove sync CLI command
- `docs/subsystems/cross_repo_operations/OVERVIEW.md` - update invariants

**Migration approach**:
- Could be automatic: on first read of external.yaml, drop pinned_sha if present
- Or explicit: migration command to clean up all external.yaml files

**`ve sync` removal**: The sync command exists only for pinning. Remove it entirely.
