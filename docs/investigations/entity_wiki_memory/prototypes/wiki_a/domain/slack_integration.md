---
title: Slack Integration
created: 2026-03-31
updated: 2026-03-31
---

# Slack Integration

My core function: connecting to Slack via a bot app and monitoring channels for keyword-matched messages.

## Authentication

- Uses `SLACK_BOT_TOKEN` from the platform's secret store
- Other available secrets: `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SLACK_SIGNING_SECRET`
- Bot must be **invited** to channels to see them via `conversations.list`

## API Calls

- `conversations.list` — discover channels the bot has joined (cursor-paginated)
- `conversations.history` — fetch messages from a channel since a timestamp (cursor-paginated, up to 200 per page)
- `auth.test` — verify bot token and get identity

## Rate Limiting

- Slack returns `429 Too Slow Down` with `Retry-After` header
- Retry capped at 5 seconds per attempt to avoid heartbeat timeout
- Multiple concurrent tool instances cause rate limit storms — keep to one instance

## Monitored Channels (as of session)

| Channel ID | Name |
|-----------|------|
| C073DT565D5 | data-integration-notifs |
| C07N051GBGW | cloud-analyst |
| C0AGC3889DF | skippy-test2 |
| C0AGCQ97QS0 | u072y0569ee |
| C0AGTCMKVA4 | skippy-test |

## Message Delivery

Messages matching subscriber filters are delivered to subscriber queues via the platform API with payload:
```json
{
  "channel": "<channel-name>",
  "text": "<message-text>",
  "user": "<user-id>",
  "ts": "<timestamp>",
  "matchedKeyword": "<keyword>"
}
```
