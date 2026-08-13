

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

`external.yaml` already is VE's interest edge; today the only address it can
carry is `repo: <org>/<repo>`, which drags a repo cache and a track→SHA
resolution behind it. This chunk adds a second, strictly simpler address —
`tree: <member>` — and keeps the two flavors from contaminating each other:

- **The schema is the gate.** `ExternalArtifactRef` grows `tree` and `why`, and
  a model validator enforces `tree` xor `repo` and rejects `track` alongside
  `tree`. Because `repo` becomes optional, every reader of `ref.repo` must
  either be peer-aware or be unreachable for peer refs; the model exposes
  `is_peer` and `target_display` so display code needs no branching.
- **Resolution reuses the manifest, not the cache.** A peer ref resolves with
  `load_workspace(pointer_dir)` → `Workspace.resolve(tree)` →
  `<member_path>/docs/<type>/<id>` → read the file. No SHA: the target is in the
  same working copy by construction, which is exactly why `track` is invalid.
  Wave 1's loader (unique-key YAML, longest-prefix nesting) is used as-is; no
  manifest parsing is re-derived here.
- **Errors are the product.** The case study's damage was *silent*
  misresolution and born-dangling refs. So each failure mode gets its own
  message: no manifest above the pointer, member not registered (listing the
  registered names, which `Workspace.resolve` already does), member registered
  but the artifact directory absent, artifact directory present but the main
  document missing. `ve external point` refuses to create a pointer at a target
  that does not resolve — a born-dangling ref should be impossible to mint by
  accident — with `--force` for the deliberate case.
- **Existing cross-repo behavior is untouched.** `create_external_yaml`,
  `repo_cache`, task-mode resolution, promote/demote keep their current code
  paths. Peer support is added as sibling functions and an early delegation
  branch, not as conditionals threaded through the repo logic.

Predicate choice (per the chunk's constraint not to unify them): resolution uses
neither `is_ve_tree` nor `has_trunk` as a gate. A registered member is
authoritative — the manifest is the registry — so a pointer naming a registered
member fails only on the *artifact* being missing. That keeps pointer-only member
trees (`federation_template_pointers`) usable as targets and leaves predicate
reconciliation to `federation_global_validator`.

DEC-002 ("external references always resolve to HEAD") is not weakened: a peer
ref has no HEAD to resolve *to*, it reads the working copy, which is that rule
taken to its limit.

Testing per docs/trunk/TESTING_PHILOSOPHY.md: schema rejections and resolution
errors are behavior (write them first); the two-tree fixture is a real
filesystem fixture in `tmp_path`; CLI coverage goes through `CliRunner`. The
`make_tree` / `write_workspace` helpers currently local to
`tests/test_workspace_manifest.py` move to `conftest.py` before a second file
uses them, as the philosophy's "Check Before You Copy" section requires.

## Subsystem Considerations

- **docs/subsystems/cross_repo_operations** (DOCUMENTED): this chunk EXTENDS the
  subsystem's addressing model with an intra-workspace flavor. `create_peer_yaml`
  and the peer resolver sit beside the existing cross-repo functions and get
  registered in the subsystem's code_references at completion. No deviations
  discovered; the repo-cache path is untouched.
- **docs/subsystems/workflow_artifacts** (DOCUMENTED): USES it — pointer
  directories remain the uniform representation of "an artifact whose content
  lives elsewhere", which is why `is_external_artifact` must stay flavor-blind.

## Sequence

### Step 1: Promote workspace test helpers to conftest

Move `make_tree`, `write_workspace`, and `make_workspace` from
`tests/test_workspace_manifest.py` into `tests/conftest.py` as `make_ve_tree`,
`write_workspace_manifest`, and `make_workspace`; import them back into
`test_workspace_manifest.py` (aliased to its current local names so its tests
are unchanged). Verify `uv run pytest tests/test_workspace_manifest.py` still
passes before continuing.

### Step 2: Schema — `tree` and `why` on `ExternalArtifactRef`

Location: `src/models/references.py`.

- `repo: str | None = None`, `tree: str | None = None`, `why: str | None = None`.
- The `repo` validator only runs when a value is present (keeps
  `_require_valid_repo_ref` semantics for repo refs).
- The `tree` validator delegates to `models.workspace.validate_member_name` so a
  member name in `external.yaml` is held to the same grammar the manifest uses
  (imports stay acyclic: `models.workspace` imports nothing from `models`).
- `why` validator: reject empty/whitespace-only, reject embedded newlines (an
  interest note is one line so reverse-interest output can tabulate it), strip
  surrounding whitespace. `why` is allowed on both flavors — an interest edge is
  an interest edge — which `federation_reverse_interest` will rely on.
- `model_validator(mode="after")`: exactly one of `repo`/`tree` (distinct
  messages for neither and for both); `track`/`pinned` rejected with `tree`, with
  a message that says why — same working copy, nothing to track.
- Properties: `is_peer` and `target_display` (`repo`, or `tree:<member>`).

Tests first, in `tests/test_external_peer_refs.py`: both keys → error; neither →
error; `tree` + `track` → error naming `track`; bad member name → error
mentioning the grammar; multiline and empty `why` → error; and a regression case
that a legacy `repo` + `track` document still loads through `load_external_ref`.

### Step 3: Creation — `create_peer_yaml`

Location: `src/external_refs.py`.

Add `create_peer_yaml(project_path, short_name, member, external_artifact_id,
artifact_type, why=None, created_after=None) -> Path` mirroring
`create_external_yaml`'s directory handling. Build the payload through
`ExternalArtifactRef` validation before writing so an invalid pointer cannot
reach disk, then dump the same key set the repo flavor uses minus `track`, plus
`tree` and (when given) `why`. `create_external_yaml` keeps its exact current
signature and output.

Tests: the created file loads back through `load_external_ref` with `tree`/`why`
intact and no `track` key; `is_external_artifact` reports True for the created
directory for every artifact type (success criterion: detection stays uniform).

### Step 4: Resolution — the peer path

Location: `src/external_resolve.py`.

- `ResolveResult`: `repo: str | None`, `track: str | None`,
  `resolved_sha: str | None`, new `tree: str | None = None` and
  `why: str | None = None`, plus a `target_display` property. All existing
  construction sites are keyword-based, so the field changes are safe.
- `resolve_artifact_peer(project_path, local_artifact_id, artifact_type)`:
  locate the pointer directory with `find_artifact_in_project`, confirm
  `is_external_artifact`, `load_external_ref`, then `_resolve_peer_ref`.
- `_resolve_peer_ref(pointer_dir, ref, artifact_type)` does the manifest work and
  raises `TaskChunkError` (the module's existing error type) with the four
  distinct messages listed in Approach. Reads main + secondary documents,
  `local_path`, `directory_contents`; `context_mode =
  "workspace_peer (same working copy)"`, `resolved_sha = None`.
- Delegation: in both `resolve_artifact_single_repo` and
  `resolve_artifact_task_directory`, once the ref is loaded, if `ref.is_peer`
  hand off to `_resolve_peer_ref`. A peer pointer inside a task project resolves
  against its own workspace, so one branch serves both modes and
  `ve external resolve` needs no new argument.

Tests (two-tree fixture: workspace root with `.ve-workspace.yaml`, members
`owner` and `consumer`): create → load → resolve returns the owner's document
content, a `local_path` under the owner tree, and the `why` note; unregistered
member, missing artifact directory, missing main document, and absent manifest
each produce their own actionable message; and **mutual interest** — owner points
at a consumer chunk while consumer points at an owner subsystem — resolves in
both directions (interest edges may cycle; only `created_after` stays acyclic).

### Step 5: Peer-awareness for `repo`-reading callers

- `src/chunks.py#resolve_chunk_location`: add a peer branch before the
  repo-cache logic so a peer chunk pointer resolves to the member tree's chunk
  directory (`is_external=True`, `external_repo=None`) instead of handing `None`
  to `repo_cache.resolve_ref`. On any workspace failure, return the location
  without content rather than raising — the same degradation the cache-miss path
  already uses.
- `src/cli/formatters.py#format_chunk_list_entry`: display
  `EXTERNAL: {ref.target_display}` (unchanged text for repo refs).
- `src/cli/chunk.py` JSON listing: emit `tree` alongside `repo`.

Tests: `ve chunk list` (text and `--json`) over a tree in a workspace holding one
peer chunk pointer shows the member as the target and does not crash.

### Step 6: `ve external point`

Location: `src/cli/external.py`.

```
ve external point <member> <artifact> [--why TEXT] [--name NAME]
                  [--force] [--project-dir DIR]
```

Behavior: load the workspace above `--project-dir` (which
`cli/tree_discovery.py` has already resolved to the nearest enclosing tree);
resolve the member (unknown → exit 1 listing registered members); normalize
`<artifact>` with `normalize_artifact_path(search_path=<member tree>)` so
`docs/subsystems/x`, `subsystems/x`, and bare `x` all work; refuse if the target
artifact does not exist unless `--force` (born-dangling prevention); refuse if
the local pointer directory already exists; write with `create_peer_yaml`; echo
the created path and the resolved target path.

Also extend `_display_resolve_result` to print the pointer's target and `why`
(`Target: tree:owner` / `Why: ...`), so a resolved peer ref shows the interest
note rather than dropping it.

Tests via `CliRunner`: point → resolve round trip; unknown member exits 1;
missing target exits 1 while `--force` succeeds; existing directory exits 1.

### Step 7: Documentation

- `src/templates/trunk/EXTERNAL.md.jinja2`: a "Peer references (same
  repository)" section — the `tree:`/`why:` fields in the schema table (with
  `repo`/`track` marked required only for cross-repo refs), a worked two-tree
  example, `ve external point` usage, the statement that peer refs are trackless
  and cache-free, and the design rule **point when readers multiply; promote when
  writers change** with promotion named as an ownership transfer.
- `src/templates/trunk/ARTIFACTS.md.jinja2` (`#external-artifacts` section): two
  sentences introducing peer refs and the point-vs-promote rule, pointing at
  EXTERNAL.md.
- Mirror both edits by hand into `docs/trunk/EXTERNAL.md` and
  `docs/trunk/ARTIFACTS.md` (these rendered files already carry repo-local
  content the templates lack, and a full `ve init` here triggers an unrelated
  legacy-layout migration — see Risks). Verify by diff that only the intended
  sections differ.

### Step 8: Backreferences, frontmatter, validation

Add `# Chunk: docs/chunks/federation_peer_refs - <what>` comments at each new
function and branch, fill `code_paths`/`code_references` in this chunk's
GOAL.md, and run `uv run ve chunk validate federation_peer_refs` plus the full
`uv run pytest tests/` (baseline 4288 passed, 0 failed).

## Dependencies

- `federation_workspace_manifest` (ACTIVE): `load_workspace`,
  `Workspace.resolve`, `validate_member_name`. No other wave-1 chunk is
  required — the qualified-comment grammar in `src/backreferences.py` is a
  separate layer, matched here only in terminology (member/`tree` vs `repo`).

## Risks and Open Questions

- **`repo` becoming optional is this chunk's blast radius.** Mitigation:
  enumerate every `ref.repo` reader (`src/chunks.py`, `src/cli/chunk.py`,
  `src/cli/formatters.py`, `src/task/{demote,external,promote}.py`,
  `src/task/artifact_ops.py`) and confirm each is either peer-aware after Step 5
  or unreachable for peer refs; task-mode promote/demote operate on cross-repo
  pointers and stay repo-only for now.
- **Template re-rendering.** Do not run `uv run ve init` in this repository: it
  triggers a legacy-layout migration unrelated to this work. Hand-mirror the
  rendered trunk docs and verify by diff.
- **`created_after` on peer pointers.** `ve external point` does not populate
  causal tips: an interest edge is not a work item. `ArtifactIndex` reads
  `created_after` from `external.yaml` opportunistically, so its absence
  degrades to "unordered" rather than an error. If chunk-flavored peer pointers
  later need ordering, that is a follow-up.
- **Deferred by design**: whether a peer pointer naming an *unregistered* but
  existing tree should be auto-registrable. That is a fix class for
  `federation_validate_fix_skill`, not a resolution-time behavior.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->
