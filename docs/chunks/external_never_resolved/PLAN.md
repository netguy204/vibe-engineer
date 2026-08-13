# Implementation Plan

## Approach

Four small changes along one path — model, writer, reader, docs — plus tests.
Nothing here contacts the network, which is the constraint that keeps this from
reopening the decision in `docs/trunk/EXTERNAL.md` about `org/repo` targets
being unverified rather than checked.

## Sequence

### Step 1: `last_resolved` on `ExternalArtifactRef`

Optional `str`, validated as an ISO-8601 instant, rejected on `tree:` pointers
alongside `track`/`pinned`.

The field validator runs in `before` mode. YAML resolves an unquoted timestamp
to a `datetime`, not a string, so a strict `after` validator rejects a file that
round-tripped through `yaml.dump`. Tolerating a `datetime` on read and
normalizing to `isoformat()` keeps the rule about *time* rather than about
quoting.

### Step 2: `stamp_resolved` in `external_refs.py`

Targeted key update on the raw text, not a re-serialization of the parsed model,
so unknown keys and the author's field order survive. Writes the stamp
**quoted**, so what VE produces is unambiguous even though it tolerates both
forms on read.

Returns `False` for peers and for pointers with no `repo`, so callers do not
pre-check the flavor.

### Step 3: Stamp at the successful resolve, in `external_resolve.py`

Called in `resolve_artifact_single_repo` and `resolve_artifact_task_directory`,
after the target content has been read. Placed in the resolver rather than the
CLI for two reasons: every caller that gets a real read contributes, and the
`raise TaskChunkError` paths above it are skipped naturally, so a failed resolve
cannot advance the timestamp.

In the task-directory path the stamp goes to `artifact_dir` — this tree's
pointer — not `external_artifact_dir`, which is the far side's content.

### Step 4: The finding, in `integrity.py`

`_validate_external_ever_resolved` walks each artifact type's directory, skips
non-external artifacts and peers, and emits one `external→never-resolved`
warning per `repo:` pointer with no stamp, naming the `ve external resolve`
command that clears it.

A malformed `external.yaml` is skipped rather than raised on: it is another
check's business, and letting it propagate here would take down the whole
validation run.

### Step 5: Document it in `docs/trunk/EXTERNAL.md`

In the schema table and as its own section, placed to be read alongside the
"unverified rather than checked" decision it deliberately does not contradict.

## Testing

`tests/test_external_never_resolved.py` — 12 tests across three groups:

- **Model**: default absent, accepts an instant, rejects a non-instant, rejected
  on a peer.
- **Stamping**: stamps a cross-repo pointer, preserves every other field,
  replaces rather than appends on a second resolve, declines to stamp a peer.
- **Validator**: warns for a never-resolved pointer, stays a *warning* so
  validation still passes, goes silent once stamped, silent for peers.

The stamping tests pass explicit `when=` values so the assertions are about
recorded content rather than about wall-clock time.

Per `docs/trunk/TESTING_PHILOSOPHY.md` the behavior under test is the observable
contract — what lands in the file and what the validator reports — not the
internal call sequence.

## Risks and Open Questions

**The finding fires on this repository immediately.** The first run reported 9
never-resolved cross-repo pointers here. That is the feature working, not a
defect, but it means the warning count is non-zero from day one and someone
should walk those pointers.

**A stamp records that a read succeeded, not that it succeeded recently.** Once
a pointer resolves once, this check goes quiet forever. Detecting a target that
existed and later disappeared is a different question, needs network, and is
deliberately out of scope.

**The stamp is a working-tree write during a read-only-looking command.**
`ve external resolve` now modifies `external.yaml`. This is intended — it is how
the fact gets recorded — but it means the command produces a diff, and anyone
scripting around it should expect that.
