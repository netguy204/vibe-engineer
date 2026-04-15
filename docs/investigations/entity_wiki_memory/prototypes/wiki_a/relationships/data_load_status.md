---
title: Data Load Status (Entity)
created: 2026-03-31
updated: 2026-03-31
---

# Data Load Status

## Identity

- Entity ID: `ca7eeea2-3ed8-4473-8613-4f89f81c974e`
- Role: Downstream consumer of my Slack messages
- Status: awake (no subscribers of its own)

## Relationship to Me

Data Load Status is my **subscriber**. It watches `#data-integration-notifs` for all messages (no keyword filter — matches everything).

## Notable Events

- Initially subscribed with a typo: `"data-integrations-notifs"` (plural 's') instead of `"data-integration-notifs"`. This silently broke filtering until corrected.
- After the fix and 24-hour rescan, received 111 messages in its subscriber queue.

## Subscription Details

```json
{
  "subscriberId": "ca7eeea2-3ed8-4473-8613-4f89f81c974e",
  "publisherId": "58d36632-bf65-4ba3-8f34-481cf64e9701",
  "filterExpression": {"type": "channel", "channel": "data-integration-notifs"},
  "queueName": "sub:a78898a4-2e48-416b-a104-4cc2ac5edddf"
}
```
