---
title: Model Adapters
created: 2026-03-31
updated: 2026-03-31
---

# Model Adapters

## Role

Model adapters wrap provider SDKs in the unified conversation abstraction. They handle mechanical translation between uniharness message types and each provider's API format.

## MVP Adapters

### Anthropic (Claude)

- Uses the Messages API
- Structured context: native `tool_use` content blocks
- Editor context: Anthropic's built-in text editor tool schema (native pass-through, DEC-005)
- Result rendering: `tool_result` content blocks

### OpenAI

- Uses the Chat Completions API
- Structured context: native function calling
- Editor context: constructed strategy (no native schema equivalent). Candidates to benchmark: fenced code blocks in message content vs function calling with JSON-escaped code
- Result rendering: function response messages

## Architecture Notes

- Adapters are chunk 2 (Anthropic) and chunk 3 (OpenAI) in the [[mvp_agent_loop]] narrative
- Both depend on chunk 1 (conversation model)
- The adapter layer is purely mechanical translation; strategy selection happens at a higher level

## Key Asymmetry

The Anthropic adapter can use native pass-through for the Editor context. The OpenAI adapter cannot -- it must construct an alternative representation. This asymmetry is the core justification for the [[strategy_matrix]].
