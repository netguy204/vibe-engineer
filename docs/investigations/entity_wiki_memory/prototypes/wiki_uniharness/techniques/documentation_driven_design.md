---
title: Documentation-Driven Design
created: 2026-03-31
updated: 2026-03-31
---

# Documentation-Driven Design

## What It Is

Writing project documentation (GOAL, SPEC, DECISIONS, TESTING_PHILOSOPHY) as the primary design activity, before any code. The documents serve as both design artifacts and contracts.

## When to Use

- Greenfield projects where the problem space needs exploration
- Projects with multiple axes of complexity (like uniharness's model x context matrix)
- When the team needs alignment on what to build before building it

## How It Worked in This Session

1. Operator provided a verbal description of the problem and vision
2. I read existing template documents to understand the structure
3. Filled in all four trunk docs in a single pass
4. Operator identified missing dimensions (result representation, native schemas)
5. I updated all affected documents consistently in each round
6. Once docs stabilized, decomposed the work into a narrative with 8 chunks

## Key Patterns

- **GOAL.md captures WHAT and WHY, never HOW**: The how belongs in SPEC.md and chunks
- **SPEC.md is the contract**: Precise enough to write conformance tests against
- **DECISIONS.md is append-only**: Never delete old decisions; add new entries that reference old ones
- **Mark uncertainty as DRAFT**: Better to be explicit about what's not yet solidified than to guess

## Pitfalls

- Temptation to over-specify before implementation experience. The DRAFT marker is the escape valve.
- Documents can drift apart if you update one without updating the others. Always update all affected docs in the same pass.
- The operator may not state all requirements upfront. Build in rounds of refinement.

## Connection to Testing

In uniharness, [[empirical_testing_as_design]] makes testing itself a design tool -- benchmark results determine which strategy occupies each matrix cell.
