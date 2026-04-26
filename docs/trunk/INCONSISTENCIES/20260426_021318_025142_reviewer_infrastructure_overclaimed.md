---
discovered_by: audit batch 8d
discovered_at: 2026-04-26T02:13:18Z
severity: medium
status: open
artifacts:
  - docs/chunks/reviewer_infrastructure/GOAL.md
---

## Claim

`docs/chunks/reviewer_infrastructure/GOAL.md` carries success criteria asserting that `docs/reviewers/baseline/DECISION_LOG.md` exists:

- Success Criterion 1: "Directory structure exists: `docs/reviewers/baseline/` contains METADATA.yaml, PROMPT.md, and DECISION_LOG.md"
- Success Criterion 4: "DECISION_LOG.md format documented: Empty file with header comment explaining the expected entry format for decisions"

The same chunk also lists `docs/reviewers/baseline/DECISION_LOG.md` in `code_paths`.

## Reality

`docs/reviewers/baseline/DECISION_LOG.md` does not exist. The baseline reviewer directory currently contains:

```
docs/reviewers/baseline/
  METADATA.yaml
  PROMPT.md
  decisions/         # directory of per-file decision records
```

Per `docs/chunks/reviewer_remove_migration/GOAL.md` and its already-completed work (see `docs/reviewers/baseline/decisions/reviewer_remove_migration_1.md`), the centralized `DECISION_LOG.md` was deleted after entries were migrated to per-file decision records under `decisions/`. The successor architecture is owned by:

- `docs/chunks/reviewer_decision_schema` — per-file decision schema (`DecisionFrontmatter`, `ReviewerDecision`, `FeedbackReview` in `src/models/reviewer.py`)
- `docs/chunks/reviewer_use_decision_files` — chunk-review skill switched from appending to `DECISION_LOG.md` to creating per-file decisions
- `docs/chunks/reviewer_remove_migration` — DECISION_LOG.md deleted from baseline

Additionally, Success Criterion 2 still references `src/models.py` for the Pydantic model, but the project has since restructured `src/models.py` into a `src/models/` package — the reviewer models live in `src/models/reviewer.py`. The frontmatter `code_paths` and `code_references` were updated in this audit pass to point at `src/models/reviewer.py`, but the success-criteria prose still references the flat-file path.

## Workaround

In this audit pass:
- Fixed broken `code_paths` and `code_references` entries pointing at `src/models.py` to instead point at `src/models/reviewer.py` (unambiguous file rename via the `models_subpackage` chunk).
- Left `code_paths: docs/reviewers/baseline/DECISION_LOG.md` untouched because there is no unambiguous successor file (the replacement is a directory of per-file records, a structural change rather than a rename).
- Left success-criteria prose untouched per audit action rules.
- Did not rewrite GOAL.md prose for tense (no rewrite needed; veto would have fired on over-claim regardless).

## Fix paths

1. **Update the chunk** to reflect current reality: rewrite Success Criterion 1 to omit `DECISION_LOG.md` (or replace with `decisions/` directory + `.gitkeep`); rewrite Success Criterion 4 to reference the per-file decision schema instead; update Success Criterion 2's reference from `src/models.py` to `src/models/reviewer.py`; remove `docs/reviewers/baseline/DECISION_LOG.md` from `code_paths`. Note that this would substantively change the chunk's intent, so an operator decision is appropriate.
2. **Historicalize the chunk** — the original intent (a single shared decision log) has been substantially superseded by per-file decisions. However, the `TrustLevel` / `LoopDetectionConfig` / `ReviewerStats` / `ReviewerMetadata` claims are still uniquely held by this chunk (no successor owns them), so historicalization is not safe under Pattern B without first relocating those claims to a successor.
3. **Leave as-is** and accept that the chunk's success criteria are partially aspirational/outdated, with the inconsistency log serving as the durable record of the drift.
