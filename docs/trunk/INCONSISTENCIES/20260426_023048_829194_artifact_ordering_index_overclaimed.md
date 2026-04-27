---
discovered_by: audit batch 10i (intent_active_audit)
discovered_at: 2026-04-26T02:30:48Z
severity: medium
status: open
artifacts:
  - docs/chunks/artifact_ordering_index/GOAL.md
---

## Claim

`docs/chunks/artifact_ordering_index/GOAL.md` describes the `ArtifactIndex`
implementation as using git-hash-based staleness detection. Specifically:

- Minor Goal (lines 39-40): "Implement `ArtifactIndex` - a cached ordering
  system for workflow artifacts that uses git-hash-based staleness detection
  and topological sorting."
- Minor Goal bullet (line 43): "**Detect staleness via git hashes** -
  Reliable across merges, checkouts, and parallel work"
- Success Criteria (line 58): "Git-hash-based staleness detection via batched
  `git hash-object`"
- Reference Implementation (line 71): cites
  `docs/investigations/0001-artifact_sequence_numbering/prototypes/git_hash_staleness.py`
  as the validated prototype.
- Key design decisions (line 73): "**Git hashes over mtimes**: Mtimes
  unreliable across merges/checkouts"
- Key design decisions (line 75): "**Batched hash-object**: Single git command
  for all files reduces overhead"

## Reality

The current `src/artifact_ordering.py` does not perform git-hash-based
staleness detection. The successor chunk
`docs/chunks/artifact_index_no_git/` (parent: `artifact_ordering_index`)
removed the git dependency in favor of directory-set enumeration:

```
$ grep -nE "hash-object|_get_git_hash|_get_all_artifact_hashes|subprocess" src/artifact_ordering.py
(no matches)
```

The actual staleness mechanism is `_enumerate_artifacts` (line 77) plus
`ArtifactIndex._is_index_stale` (line 279) comparing directory-name sets, not
content hashes.

The chunk's success criteria therefore describe a state of the system that no
longer exists. The veto rule from `intent_active_audit/PLAN.md` (Step 4)
applies: do not rewrite the prose to a present-tense form, because no
truthful present-tense restatement of "git-hash-based staleness detection via
batched `git hash-object`" exists in current code.

This is undeclared over-claim — `code_references` carry no `status: partial`
flag, but the named approach is contradicted by current implementation.

## Workaround

None applied. The chunk's GOAL.md is left untouched per the veto rule.
Readers must consult `docs/chunks/artifact_index_no_git/GOAL.md` to learn the
current staleness-detection approach.

## Fix paths

1. **Preferred — narrow this chunk's claims to what survives.** Update the
   prose to describe only the still-true claims: `ArtifactIndex` class
   structure, `get_ordered`, `find_tips`, `rebuild`, multi-parent topological
   sort, gitignored JSON index format. Move the git-hash-staleness language
   into a "Superseded by" pointer to `artifact_index_no_git`. Do this in a
   focused follow-up chunk so the rewrite is reviewable on its own.
2. **Alternative — historicalize.** If on closer inspection every load-bearing
   claim in this chunk is now owned by a successor (artifact_index_no_git for
   staleness; some other chunk for the `ArtifactIndex` API), set status to
   HISTORICAL per Pattern B in `intent_active_audit/PLAN.md`. Audit batch 10i
   did not historicalize because the `ArtifactIndex` class structure, public
   API, topological sort, and JSON index format still appear to be uniquely
   owned here.

## Related

While verifying, the `code_references` block also carries a broken entry:
`src/models.py#ArtifactType` (file does not exist; correct location is
`src/models/references.py#ArtifactType`, which is also already listed
separately as a duplicate entry). See companion inconsistency entry for that
metadata defect.
