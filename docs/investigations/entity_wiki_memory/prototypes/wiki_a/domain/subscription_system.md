---
title: Subscription System
created: 2026-03-31
updated: 2026-03-31
---

# Subscription System

The pub/sub mechanism connecting entities in the [[palette_platform]].

## How Subscribers Connect

A downstream entity subscribes by posting to the platform with:
```json
{
  "subscriberId": "<their-entity-id>",
  "publisherId": "58d36632-bf65-4ba3-8f34-481cf64e9701",
  "filterExpression": {
    "type": "channel",
    "channel": "data-integration-notifs",
    "keywords": ["deploy", "outage", "incident"]
  }
}
```

## Filter Expression

- `type: "channel"` — match by channel name
- `channel` — exact channel name (case-sensitive; typos break matching)
- `keywords` — array of keywords for case-insensitive substring match
- If no keywords specified, all messages from the channel match

## Subscription Record

Fields: `id`, `subscriberId`, `publisherId`, `filterExpression` (stored as JSON string), `queueName`, `status`, `createdAt`, `lastMessageAt`

## Gotcha: Channel Name Typos

In the session, Data Load Status subscribed with `"data-integrations-notifs"` (plural 's') while the actual channel was `"data-integration-notifs"`. This silently broke filtering until the subscriber corrected it. The matching is exact string equality — no fuzzy matching.

## Queue Delivery

Matched messages are POSTed to the subscriber's queue: `POST /entities/<subscriberId>/queue/<queueName>`. Subscribers poll their queue with an offset to consume messages.

## Gotcha: Startup vs Runtime Subscriber Detection

When a tool loads subscribers at startup, it only sees subscriptions that existed at that moment. If a subscription is created *after* the tool starts, the tool will miss it unless it re-fetches from the API. The inbound queue notification mechanism for new subscriptions is unreliable.

**Fix**: re-fetch subscribers from `GET /entities/<id>/subscriptions` at the start of every cycle, not just at startup.

## All-Pass Filter

Subscribers can use `{"type":"all"}` as their filter expression to receive every message/event without keyword matching. Used by entities like [[ramp_bar_chart]] that consume all output from their publisher.
