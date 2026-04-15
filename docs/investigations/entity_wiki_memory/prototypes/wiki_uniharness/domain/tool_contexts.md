---
title: Tool Contexts
created: 2026-03-31
updated: 2026-03-31
---

# Tool Contexts

## What is a Context?

A context describes the *kind of work* a tool does, which determines how it should be communicated to the model. Three contexts are defined (DEC-002):

## 1. Structured Context

Named structured arguments, structured output. The standard "function calling" pattern. JSON-based tool-calling APIs work well here because the arguments are simple key-value pairs.

**Example**: An "execute Python" tool that takes a file path and returns stdout/stderr/exit code.

## 2. Editor Context

Tools that produce substantial text output (code, documents) where JSON escaping and whitespace representation degrade quality. The name "Editor" is acknowledged as potentially too narrow -- the abstraction is more general: any tool where the output is large text that must preserve formatting.

This is the context where the library adds the most value. Native tool-calling APIs often fail here because JSON escaping makes writing code difficult. Different strategies are needed:
- Claude: Anthropic's native text editor tool schema
- OpenAI: A constructed alternative (fenced blocks, XML, etc.)

**Example**: A "write file" tool that produces Python code.

**Key insight**: File state is a natural **entity** (mutable, refreshed on each edit), not a static result. See [[result_representation]].

## 3. Custom Context

An escape hatch for defining new mechanisms. No concrete use cases yet, but its existence as a design pressure forces the Structured and Editor implementations to be more maintainable and extensible.

The Custom context ensures the architecture doesn't over-fit to just two cases.

## Naming

The "Editor" name is flagged as not quite right. The docs frame it as "substantial text output where JSON escaping is harmful," which may suggest a better name as the abstraction solidifies through implementation experience.
