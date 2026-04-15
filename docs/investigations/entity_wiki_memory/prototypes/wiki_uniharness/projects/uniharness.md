---
title: Uniharness Project
created: 2026-03-31
updated: 2026-03-31
---

# Uniharness

## What It Is

A library that mediates between agent code and LLM APIs for tool calling. It accepts model-agnostic tool definitions, selects a representation strategy based on tool context and target model, renders into the model's API format, and parses responses back into structured tool-call results.

**Repository**: `/Users/btaylor/Projects/uniharness`

## Project Status

Greenfield. Documentation phase complete (trunk docs written). MVP narrative decomposed into 8 chunks. No code yet. Autoplan review was initiated but transcript was truncated before completion.

## Trunk Documents

All four trunk documents were authored in this session:
- **GOAL.md**: Problem statement, 6 required properties, constraints, success criteria
- **SPEC.md**: Terminology, tool contexts, API surface (DRAFT), entity lifecycle, native schema strategies
- **DECISIONS.md**: 5 ADRs (DEC-001 through DEC-005)
- **TESTING_PHILOSOPHY.md**: Testing as design tool, 4 test categories

## Required Properties (from GOAL.md)

1. Multi-model support
2. Context-aware strategy selection
3. Empirically grounded (benchmark evidence required)
4. Extensible (Custom context as escape hatch)
5. Bidirectional abstraction (outbound tools + inbound results)
6. Native schema pass-through

## Architectural Decisions

| ID | Decision | Key Rationale |
|---|---|---|
| DEC-001 | Two-axis strategy selection (model family x tool context) | Captures the two independent dimensions that determine optimal strategy |
| DEC-002 | Three initial contexts (Structured, Editor, Custom) | Custom exists as design pressure to keep architecture extensible |
| DEC-003 | Empirical testing drives strategy selection | No matrix entry without benchmark evidence |
| DEC-004 | Bundle outbound + inbound in single strategy; static/entity split | Keeps matrix manageable, ensures consistency |
| DEC-005 | Prefer native schemas over constructed strategies | Lowest-common-denominator leaves quality on the table |

## MVP Narrative: Agent Loop

8 chunks with dependency ordering:

1. Conversation model and message types (foundation)
2. Anthropic adapter (depends on 1)
3. OpenAI adapter (depends on 1)
4. Structured context strategy (depends on 1-3)
5. Editor context strategy -- Claude (depends on 1-3)
6. Editor context strategy -- OpenAI (depends on 1-3)
7. Agent loop and tools (depends on 4-6)
8. Benchmark tests (depends on 7)

The MVP agent loop writes and debugs a small Python program, exercising both tool contexts against both model families.

## Constraints

- Library, not framework (caller owns the loop)
- Small team
- Expensive tests (LLM calls cost money and are non-deterministic)

## Out of Scope

- Agent orchestration / multi-step reasoning
- Prompt engineering / system prompt management
- Model hosting / inference
- Concurrent tool calls (MVP)
