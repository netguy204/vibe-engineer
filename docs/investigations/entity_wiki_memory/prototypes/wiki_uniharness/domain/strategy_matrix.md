---
title: Strategy Matrix - Model x Context Selection
created: 2026-03-31
updated: 2026-03-31
---

# Strategy Matrix

## Core Concept

The optimal way to communicate a tool to an LLM and parse its response depends on two axes:
1. **What kind of tool** (the context)
2. **Which model family** (Claude, OpenAI, etc.)

This creates a matrix where each cell contains a **strategy** -- the specific representation and parsing approach for that combination. See [[tool_contexts]] for the context axis and [[model_adapters]] for the model axis.

## The Two-Axis Selection Model (DEC-001)

A strategy is selected by looking up (model_family, tool_context) in the matrix. This is the fundamental dispatch mechanism.

## Strategy Spectrum

Strategies are not all constructed from primitives. They exist on a spectrum:
- **Fully constructed**: The library builds the tool representation from scratch (e.g., XML-delimited blocks, fenced code blocks)
- **Native pass-through**: The library maps onto a model's built-in schema and gets out of the way (e.g., Anthropic's text editor tool)

Native schemas are the default when they exist (DEC-005). The strategy interface must accommodate both ends of this spectrum.

## MVP Matrix (4 cells)

| | Structured Context | Editor Context |
|---|---|---|
| **Claude** | Native tool_use (straightforward) | Anthropic text editor tool schema (native pass-through) |
| **OpenAI** | Native function calling (straightforward) | Constructed strategy (TBD empirically: fenced code blocks vs JSON-escaped function calling) |

The asymmetry in the Editor row is exactly what the library exists to handle. Claude has a native schema; OpenAI does not.

## Bidirectionality (DEC-004)

Each strategy covers both directions:
- **Outbound**: How to present the tool to the model
- **Inbound**: How to represent the tool's result back into the conversation

Bundling both directions in one strategy keeps the matrix manageable and ensures consistency. A strategy that renders tools as XML blocks should render results in a compatible way.

## Open Questions

- What is the best Editor strategy for OpenAI? (Requires benchmark testing)
- How do entity-based results (mutable, refreshable) map onto each API's conversation format?
- Will the matrix need per-model entries (e.g., GPT-4 vs GPT-3.5) or is per-family sufficient?
