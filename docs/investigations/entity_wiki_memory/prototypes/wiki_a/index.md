---
title: Wiki Index — Palette Entity Agent
created: 2026-03-31
updated: 2026-03-31
---

# Wiki Index

Personal knowledge base for a palette entity agent, built across multiple sessions operating different entities (Slack Watcher, Linear Ramp).

## Core

| Page | Summary |
|------|---------|
| [[identity]] | Who I am, my role, working style, values, and hard-won lessons |
| [[log]] | Chronological session log with key events and learnings |

## Domain Knowledge

| Page | Summary |
|------|---------|
| [[domain/palette_platform]] | The runtime platform: architecture, APIs, directory layout |
| [[domain/tool_runner]] | Process supervisor for mechanical tools: spawning, proving, heartbeats |
| [[domain/proving_model]] | How tools graduate from Proving to Stable via repeated exit-0 cycles |
| [[domain/slack_integration]] | Slack API usage: auth, channels, rate limiting, message delivery |
| [[domain/subscription_system]] | Pub/sub mechanism: filters, queues, subscriber lifecycle |

## Projects

| Page | Summary |
|------|---------|
| [[projects/slack_watcher_tool]] | The poll.sh/poll-worker.js tool: architecture, evolution, safety measures |
| [[projects/linear_ramp_tool]] | The ramp.js tool: continuous interpolation, proving battle, boilerplate copy strategy |

## Techniques

| Page | Summary |
|------|---------|
| [[techniques/single_cycle_tools]] | Design pattern for tools that prove: do work, persist, exit 0 |
| [[techniques/nuclear_exit_safety]] | Defense-in-depth strategy for guaranteed clean exits in Node.js |
| [[techniques/background_heartbeat]] | setInterval heartbeat to survive slow cycles; must init at top-level |
| [[techniques/shell_wrapper_for_tools]] | Bash wrapper for unconditional exit 0, worker outside tools/ |
| [[techniques/fetch_timeout]] | AbortController timeout on fetch() to prevent blocking heartbeat |
| [[techniques/copy_working_boilerplate]] | Copy proven tool structure when proving resists iteration |

## Relationships

| Page | Summary |
|------|---------|
| [[relationships/brian_taylor]] | The operator who directs my work |
| [[relationships/data_load_status]] | Subscriber entity, watches #data-integration-notifs |
| [[relationships/ramp_bar_chart]] | Subscriber entity, consumes Linear Ramp output |
| [[relationships/palette_entities]] | All entities in the palette and their topology |
