---
discovered_by: audit batch 11b
discovered_at: 2026-04-26T02:38:23
severity: medium
status: open
artifacts:
  - docs/chunks/external_artifact_unpin/GOAL.md
---

# Claim

`docs/chunks/external_artifact_unpin/GOAL.md` makes two assertions that don't match
current code:

1. Success criterion (line 84): "ExternalArtifactRef model no longer has pinned_sha
   field" and Solution step 1 (line 63): "Remove `pinned_sha` field from
   `ExternalArtifactRef` model".
2. `code_paths` lists files that do not exist:
   - `src/models.py` (the project moved `models` to a package — `src/models/` directory)
   - `src/sync.py` (intentionally removed by this chunk's work)
   - `tests/test_sync.py`, `tests/test_sync_cli.py`, `tests/test_sync_integration.py`
     (intentionally removed alongside `src/sync.py`)

# Reality

1. `src/models/references.py:339` defines `ExternalArtifactRef` with the field
   `pinned: str | None = None`. Per the comment at lines 354-356, the field is
   retained for backward compatibility with existing `external.yaml` files but is
   ignored at resolve time. So the model **does** still carry a pinning field — it
   was renamed from `pinned_sha` to `pinned` and made a no-op rather than removed
   outright. The `create_external_yaml` writer at `src/external_refs.py:275` does
   not emit it, and `external_resolve.py` ignores it.
2. The non-existent `code_paths` entries reflect the chunk's removal intent (`sync`
   was removed) and a project-wide refactor (`models.py` → `models/` package). The
   `code_references` correctly point at `src/models/references.py`-style locations
   via the `#ExternalArtifactRef` symbol notation, so the runtime intent is
   discoverable; only the `code_paths` index is stale.

# Workaround

None applied. The chunk's behavioral intent is met (external resolution always uses
HEAD; `external.yaml` no longer carries pinning data), but the literal claims about
the model field and the code_paths file list are inaccurate. Audit batch 11b
applied the veto rule and did not rewrite the GOAL prose to a present-tense form.

# Fix paths

1. **Reconcile criterion to code**: rewrite success criterion #1 to read "the
   `pinned` field on `ExternalArtifactRef` is ignored at resolve time and never
   written by `create_external_yaml`" (or equivalent), and document the retained
   field as a backward-compat shim. Update `code_paths` to drop the removed `sync`
   files and the obsolete `src/models.py`, replacing the latter with
   `src/models/references.py`.
2. **Reconcile code to criterion**: drop the `pinned` field outright from
   `ExternalArtifactRef` and stop accepting it during model validation. This
   requires a migration story for any in-the-wild `external.yaml` files still
   carrying `pinned`. Likely heavier than fix path 1 and not obviously worth it.
