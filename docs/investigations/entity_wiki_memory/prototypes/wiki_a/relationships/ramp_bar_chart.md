---
title: Ramp Bar Chart (Entity)
created: 2026-03-31
updated: 2026-03-31
---

# Ramp Bar Chart

## Identity

- Entity ID: `70440966-0ff5-48bf-bda2-81ad308aae38`
- Role: Downstream consumer of [[linear_ramp_tool]] output
- Status: awake

## Relationship to Linear Ramp

Ramp Bar Chart subscribes to Linear Ramp with a `{"type":"all"}` filter, receiving every tick's `{ currentValue, step, cycle }` payload. Its tool (`consume.js`) is a known-good proving boilerplate that I later copied for the ramp tool itself.

## Subscription Details

```json
{
  "id": "90fb73a8-d60e-4f26-8884-f4978100eaed",
  "subscriberId": "70440966-0ff5-48bf-bda2-81ad308aae38",
  "publisherId": "ecbc0849-71d8-4e01-af3e-0836b198b726",
  "filterExpression": {"type": "all"},
  "queueName": "sub:90fb73a8-d60e-4f26-8884-f4978100eaed"
}
```

## Notable Events

- Subscription existed before the Linear Ramp tool started, but `lastMessageAt` was `null` because the tool loaded subscribers only at startup (before the subscription was created). Fixed by re-fetching subscribers each cycle.
- After fix: 100+ messages flowing, values climbing 1-10 correctly.
