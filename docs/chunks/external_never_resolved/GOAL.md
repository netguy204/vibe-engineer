---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models/references.py
- src/external_refs.py
- src/external_resolve.py
- src/integrity.py
- docs/trunk/EXTERNAL.md
- tests/test_external_never_resolved.py
code_references:
- ref: src/models/references.py#ExternalArtifactRef
  implements: The last_resolved field, validated as an ISO-8601 instant and rejected
    on peer pointers. Validation runs in before mode because YAML resolves an unquoted
    timestamp to a datetime rather than a string.
- ref: src/external_refs.py#stamp_resolved
  implements: Records a successful read on a cross-repo pointer, by targeted key update
    so unknown keys and author field order survive. Returns False for peers and for
    pointers with no repo target, so callers need not pre-check the flavor.
- ref: src/external_resolve.py#resolve_artifact_single_repo
  implements: 'Stamps only after the target content has been read, so a raised TaskChunkError
    skips it: a failed resolve never advances the timestamp.'
- ref: src/integrity.py#IntegrityValidator::_validate_external_ever_resolved
  implements: 'Reports a repo: pointer with no last_resolved as a warning. Reads only
    local files, so the finding needs no network and does not reopen the decision
    that org/repo targets are unverified rather than checked.'
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- priorart_subject_search
---
# Chunk Goal

## Minor Goal

A cross-repository external pointer records **whether it has ever resolved**, so
a pointer that has never once been verified is distinguishable from one that is
merely unverified right now.

`ExternalArtifactRef` carries `last_resolved`, a UTC timestamp that
`ve external resolve` writes into `external.yaml` on every successful read of a
`repo:` target. `ve validate` reports a `repo:` pointer with no `last_resolved`
as a **never-verified** finding, naming the command that would settle it.

**Why this does not reopen a settled decision.** `docs/trunk/EXTERNAL.md` states
that `org/repo` targets are reported as *unverified* rather than checked,
"because resolving them needs network or cache state, and a gate whose verdict
depends on a warm cache is not a gate." That stands, and this chunk does not
touch it: the finding here needs **no network**. "This pointer has never been
read, by anyone, since it was written" is a local fact stored in the file. VE
still declines to say whether a target exists; it now says whether anybody has
ever looked.

**The failure this closes.** A pointer whose far side was never committed dangles
from birth, and nothing distinguishes it from a healthy pointer that simply has
not been resolved this week. Such a directory is worse than absent when it is
named for the subject under investigation: it is the most on-target hit a search
returns, and it answers "someone already looked at this and it went nowhere"
with more authority than an empty result — see [[priorart_subject_search]],
whose directive sends agents to exactly these hits.

The finding is a **warning, not an error**. A pointer is never-verified from the
moment it is written until someone resolves it, so an error would fail
validation on correctly-created pointers and teach people to route around the
gate.

## Success Criteria

- `ExternalArtifactRef` accepts an optional `last_resolved` UTC timestamp, and
  rejects a value that is not an ISO-8601 instant.
- `last_resolved` is meaningful only for `repo:` targets. A `tree:` pointer that
  carries one is rejected, matching how `track`/`pinned` are already rejected
  for peers: a peer resolves through the manifest against the same commit, so
  "when did this last resolve" has no content.
- A successful `ve external resolve` of a `repo:` target writes `last_resolved`
  back to that pointer's `external.yaml`, preserving every other field and the
  file's field order.
- A failed resolve leaves `last_resolved` untouched — a failure must never
  advance the timestamp.
- `ve validate` emits one warning per `repo:` pointer with no `last_resolved`,
  naming the artifact and the `ve external resolve <id>` command that clears it.
- The warning does not fire for `tree:` pointers, which `ve workspace validate`
  already checks structurally via the `missing-target` fix class.
- `ve validate` performs **no network access** to produce this finding.
- Existing `external.yaml` files without the field keep loading, and every
  existing test passes.

## Rejected Ideas

### Have `ve validate` resolve `repo:` targets and report whether they exist

Rejected because: it contradicts a decision already recorded in
`docs/trunk/EXTERNAL.md` — resolution needs network or cache state, and "a gate
whose verdict depends on a warm cache is not a gate." A validator that passes on
a warm cache and fails on a cold one trains people to re-run it rather than fix
anything. This chunk deliberately reports a *local* fact instead.

### Make the never-verified finding an error

Rejected because: every pointer is never-verified at the instant it is created,
so an error fails validation on correct work. The signal belongs at the volume
that survives being read every day.

### Age the finding — warn only after N days unverified

Rejected because: it makes the validator's verdict depend on the wall clock, so
the same tree passes today and fails next month with no change to its contents.
Deterministic output matters more than the extra precision, and "never verified"
is already the sharp end of the distinction.

### Record the resolution result (found / not found) rather than a timestamp

Rejected because: storing "not found" would put a network-derived verdict in the
file, where it goes stale silently and starts answering questions VE has decided
not to answer. A timestamp records only that a read succeeded, which is exactly
the fact being claimed.
