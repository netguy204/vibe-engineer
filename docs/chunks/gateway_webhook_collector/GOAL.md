---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- workers/leader-board/src/swarm-do.ts
- workers/leader-board/test/gateway-api.test.ts
code_references:
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::handleWebhookAPI
  implements: "Generic webhook collector endpoint that accepts any content type, base64-encodes the raw body into a JSON envelope, and stores via the encrypted message pipeline"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::resolveTokenKey
  implements: "Shared token-to-symmetric-key resolution extracted from handleGatewayAPI, used by both gateway and webhook endpoints"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- watchmulti_manual_ack
---

# Chunk Goal

## Minor Goal

Add a generic webhook collector endpoint to the cleartext gateway that accepts any payload format and marshals it into a swarm message. This enables external systems (GitHub webhooks, Stripe webhooks, CI systems, etc.) to POST directly to a gateway URL without needing a translation layer.

The current `POST /gateway/{token}/channels/{channel}/messages` endpoint requires a JSON body with a `body` field. External webhook producers send arbitrary formats (form-encoded, XML, plain text, arbitrary JSON) that don't match this schema.

New endpoint: `POST /gateway/{token}/channels/{channel}/webhook`

Behavior:
- Accept ANY content type and payload format
- Marshal the raw payload into an envelope: `{"content_type": "<original Content-Type header>", "raw_body": "<base64 of body>", "source": "webhook"}`
- Encrypt and store via the same token-based encryption path as the existing POST endpoint
- Return 200 with the message position on success

This preserves the security model (token-based encryption) while making the gateway a universal webhook receiver.

## Success Criteria

- `POST /gateway/{token}/channels/{channel}/webhook` accepts any content type
- Raw payload is marshaled into a JSON envelope with content_type and raw_body fields
- Message is encrypted and stored identically to regular POST messages
- Existing `POST .../messages` endpoint unchanged
- Tests cover: JSON webhook, form-encoded webhook, plain text webhook, XML webhook
- CORS headers included on webhook endpoint (per `gateway_cors_and_docs`)