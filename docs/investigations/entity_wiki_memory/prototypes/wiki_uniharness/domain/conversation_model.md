---
title: Conversation Model
created: 2026-03-31
updated: 2026-03-31
---

# Conversation Model

## Purpose

A unified representation of conversation state that supports the message types all models need and can be rendered into each model's API format. This is the foundation layer -- everything else (adapters, strategies, agent loop) builds on it.

## Message Types

The abstraction supports these core message roles:
- **System**: System prompt / instructions
- **User**: Human input
- **Assistant**: Model output
- **Tool-call**: Model requesting a tool invocation (outbound)
- **Tool-result**: Tool response going back to the model (inbound), with static and entity variants

## Conversation State

The conversation state container manages the ordered sequence of messages and supports:
- Appending new messages
- Entity refresh (replacing a previous entity-type tool result with updated content)
- Rendering into each model's native API format via the adapter layer

## Design Principle

The conversation model is the **caller's** responsibility to manage. The library provides the types and rendering, but the agent loop (or whatever orchestrates the interaction) owns the state. This keeps uniharness as a library, not a framework.

## Rendering Interface

Each message type has a rendering interface that adapters implement. The rendering is not a simple serialization -- it must account for the active strategy, since (for example) an editor-context tool call might be rendered as a native content block for Claude but as a fenced code block for OpenAI.
