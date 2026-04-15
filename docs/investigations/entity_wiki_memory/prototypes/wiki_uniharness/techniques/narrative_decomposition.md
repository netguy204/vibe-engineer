---
title: Narrative Decomposition
created: 2026-03-31
updated: 2026-03-31
---

# Narrative Decomposition

## What It Is

Breaking a large initiative into ordered chunks with explicit dependency relationships. A narrative captures the overall ambition; chunks are the discrete implementation units.

## When to Use

- When the work is too large for a single chunk
- When there are natural dependency boundaries (foundation must exist before things build on it)
- When parallelizable work exists (chunks 2 and 3 can run concurrently)

## How It Worked in This Session

The MVP agent loop was decomposed into 8 chunks:

```
[1. Conversation model]
    |-> [2. Anthropic adapter] --\
    |-> [3. OpenAI adapter] -----+-> [4. Structured strategy]
                                  |-> [5. Editor/Claude]
                                  |-> [6. Editor/OpenAI]
                                       |-> [7. Agent loop]
                                            |-> [8. Benchmarks]
```

## Decomposition Principles Observed

- **Foundation first**: The conversation model is chunk 1 because everything depends on it
- **Parallel where possible**: Adapters (2, 3) can be built concurrently; strategy chunks (4, 5, 6) can be built concurrently
- **Integration last**: The agent loop (7) wires everything together; benchmarks (8) validate the whole
- **Name by initiative, not artifact**: "conversation_model" not "create_types"

## Pitfalls

- Over-decomposition: too many tiny chunks adds overhead
- Under-decomposition: chunks that are too large lose the benefits of incremental progress
- Missing dependencies: forgetting that strategies depend on both the model and the adapter
