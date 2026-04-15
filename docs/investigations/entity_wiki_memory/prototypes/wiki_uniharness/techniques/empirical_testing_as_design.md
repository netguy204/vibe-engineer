---
title: Empirical Testing as Design
created: 2026-03-31
updated: 2026-03-31
---

# Empirical Testing as Design

## What It Is

Using benchmark tests as the primary mechanism for making design decisions, rather than relying on documentation, intuition, or provider claims. In uniharness, no strategy matrix entry is justified without benchmark evidence (DEC-003).

## When to Use

- When the design space involves non-deterministic systems (LLMs)
- When provider documentation says "supports X" but doesn't tell you whether X actually works well for your use case
- When there are multiple viable approaches and the difference is quality, not correctness

## The Uniharness Testing Categories

1. **Unit tests**: Deterministic rendering and parsing. Given this tool definition and this strategy, does the output match expectations?
2. **Benchmark tests**: Quality evaluation with scores. Run the same coding task through multiple strategies, measure: does the code parse? Does it run? Does it produce correct output? Are there escaping artifacts?
3. **Integration tests**: Recorded fixtures. Capture real API responses and replay them to test the full pipeline without live calls.
4. **Comparison tests**: Head-to-head strategy evaluation. The evidence that justifies each matrix entry.

## Key Insight

The benchmark tests are where the hardest open questions get answered. For example: "Is native function calling or fenced code blocks better for code generation on OpenAI?" You cannot answer this from documentation. You must run the experiment.

## Handling Non-Determinism

LLM outputs are non-deterministic. The testing philosophy must account for this:
- Use score-based evaluation rather than exact match
- Run multiple trials
- Focus on structural properties (does it parse? does it execute?) over exact content

## Pitfalls

- Tests are expensive (real LLM API calls cost money)
- Test results may change as models are updated
- Fixture-based tests can become stale; need a refresh cadence
