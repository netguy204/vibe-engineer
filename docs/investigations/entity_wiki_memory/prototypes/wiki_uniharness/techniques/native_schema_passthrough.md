---
title: Native Schema Pass-Through Pattern
created: 2026-03-31
updated: 2026-03-31
---

# Native Schema Pass-Through

## What It Is

When a model provider offers a purpose-built schema for a specific tool type (e.g., Anthropic's text editor tool), the abstraction layer should map onto it directly rather than constructing an alternative representation. The strategy becomes "translate the caller's definition into the native schema and get out of the way."

## When to Use

- When a provider has a native schema that matches the tool context
- When the native schema is likely optimized (the provider trained the model to use it well)
- As the default before considering constructed alternatives

## The Uniharness Decision (DEC-005)

A lowest-common-denominator abstraction that ignores native schemas leaves quality on the table. The strategy interface must accommodate both constructed and pass-through strategies.

## Mapping Requirements

For a native pass-through strategy:
1. Translate the caller's tool definition into the native schema format
2. Preserve caller semantics (the caller shouldn't need to know which strategy was selected)
3. Parse the model's native response format back into the unified result type

## Example

Claude's Editor context: The Anthropic SDK provides a built-in text editor tool schema. Uniharness's Claude x Editor strategy maps directly onto this schema rather than constructing XML blocks or other alternatives.

OpenAI has no equivalent, so its Editor strategy must be constructed from primitives.

## Pitfalls

- Native schemas may have constraints the generic abstraction doesn't model. The pass-through must handle these gracefully.
- The abstraction must not leak native schema details to the caller.
- Native schemas can change between API versions.
