---
discovered_by: audit batch 8a
discovered_at: 2026-04-26T02:12:11
severity: low
status: open
artifacts:
  - docs/chunks/reviewer_decision_schema/GOAL.md
---

## Claim

`docs/chunks/reviewer_decision_schema/GOAL.md` lists six `code_references` for the decision schema models, three pointing at `src/models.py#X` and three at `src/models/reviewer.py#X`:

```yaml
code_references:
  - ref: src/models.py#ReviewerDecision
    implements: "StrEnum for decision outcomes (APPROVE/FEEDBACK/ESCALATE)"
  - ref: src/models.py#FeedbackReview
    implements: "Pydantic model for structured feedback variant of operator review"
  - ref: src/models.py#DecisionFrontmatter
    implements: "Pydantic model for per-file decision frontmatter with union-typed operator_review"
  ...
  - ref: src/models/reviewer.py#ReviewerDecision
    implements: "Per-file decision schema enum (APPROVE/FEEDBACK/ESCALATE)"
  - ref: src/models/reviewer.py#FeedbackReview
    implements: "Structured feedback variant for operator review"
  - ref: src/models/reviewer.py#DecisionFrontmatter
    implements: "Per-file decision frontmatter schema"
```

## Reality

`src/models.py` does not exist as a single file — `src/models/` is a package, with the reviewer schema defined in `src/models/reviewer.py`:

```
$ ls src/models.py
ls: src/models.py: No such file or directory
$ ls src/models/
__init__.py  chunk.py  entity.py  friction.py  investigation.py  narrative.py  references.py  reviewer.py  shared.py  subsystem.py
```

The first three `code_references` (`src/models.py#ReviewerDecision`, `src/models.py#FeedbackReview`, `src/models.py#DecisionFrontmatter`) point at a non-existent file. The latter three (`src/models/reviewer.py#X`) are correct and refer to the same symbols. The frontmatter therefore carries duplicate references — three broken plus three correct — for the same three classes.

The audit fixed the analogous `code_paths: src/models.py` entry in this same audit pass (now `src/models/reviewer.py`), but did not edit `code_references` (out of scope for the per-chunk fix-in-place rule, which is scoped to `code_paths`).

## Workaround

None applied. The correct references are present, so anything reading `code_references` will at worst hit a "missing symbol" error on the broken three before finding the working three. The duplication is metadata noise rather than a code-behavior problem.

## Fix paths

1. **Preferred — dedup `code_references`**: drop the three `src/models.py#X` entries. The `src/models/reviewer.py#X` entries already cover the same symbols with clearer wording.
2. Alternative — flatten the package back to a single `src/models.py` file. Larger restructuring with no upside; the package layout is intentional (`# Chunk: docs/chunks/models_subpackage` backreference at the top of `src/models/reviewer.py`).
