---
status: SOLVED
trigger: "Exploring whether agent-friendly invite links could simplify steward onboarding, inspired by a product that lets agents join collaborative environments via pasted URLs"
proposed_chunks:
  - prompt: "Encrypted key blob storage on the Durable Object — PUT/GET/DELETE routes for token-encrypted private key blobs indexed by hash(token)"
    chunk_directory: gateway_token_storage
    depends_on: []
  - prompt: "Cleartext gateway HTTP routes — GET/POST message endpoints that decrypt the key per-request using the token, enabling agents to interact with swarm channels via plain HTTP"
    chunk_directory: gateway_cleartext_api
    depends_on: [0]
  - prompt: "ve board invite and ve board revoke CLI commands — generate token, encrypt key, upload blob, output invite URL; revoke by deleting blob"
    chunk_directory: invite_cli_command
    depends_on: [0]
  - prompt: "Agent-facing instruction page at /invite/{token} — plain text protocol description with example curl commands that any agent can follow to start interacting with the swarm"
    chunk_directory: invite_instruction_page
    depends_on: [1]
---

## Trigger

Operator encountered a product that lets users paste a link into any agent (OpenClaw, ClawedCode, etc.), and the agent follows the link to receive instructions for joining a collaborative editing environment — essentially a "Google Docs for agents" onboarding flow.

This pattern is compelling as an onboarding strategy for the VE steward environment. Currently, steward setup requires manual configuration: running /steward-setup, providing swarm IDs, and ensuring the agent has access to the correct private keys in ~/.ve/keys/. The vision is a CLI command like ve board invite that generates a link an agent can follow to receive everything it needs to participate in a swarm.

The core tension: the current security model treats swarm membership as "possession of the private key" with no per-channel permissions and no centralized member list. Embedding the private key directly in a URL would be functional but fundamentally disrupts this trust model — anyone who intercepts the link gains full swarm access forever.

## Success Criteria

1. Security model decision: Determine whether invite links should carry the full swarm private key, a derived/scoped credential, or a bootstrapping token that triggers a separate key exchange.
2. Link content design: Define exactly what information the invite link encodes and how an agent consumes it (URL structure, what the agent fetches, what instructions it receives).
3. Agent-agnostic onboarding: The approach must work for any agent that can follow a URL and read instructions — not tied to a specific agent runtime.
4. Revocability assessment: Determine whether invite links can be revoked, and if so, what infrastructure changes are required.
5. Prototype feasibility: A clear enough design that a chunk could implement ve board invite and the corresponding endpoint/handler.

## Testable Hypotheses

### H1: A "raw key in URL" approach is sufficient for the current trust model

- Rationale: The swarm is already a flat trust domain — all key holders have equal access. Since there are no per-channel permissions, adding scoped credentials would be building infrastructure the rest of the system doesn't use.
- Status: FALSIFIED
- Reason: The server currently never sees the private key — it only transports opaque ciphertext. Embedding the key in a URL that resolves through the server would expose the private key to the server for the first time, breaking the guarantee that all messages exchanged through the server are opaque to the server.

### H2: The invite link should resolve to an instruction page, not carry credentials directly

- Rationale: The product the operator saw worked by having the agent "follow" a link and "get instructions." This suggests the link points to a hosted page that serves agent-readable instructions rather than embedding everything in the URL itself.
- Status: UNTESTED

### H3: Invite links can be made revocable without changing the core swarm crypto

- Status: VERIFIED
- Reason: The cleartext gateway design uses server-issued tokens as the sole access mechanism. Revoking a token immediately kills access. The swarm key is unchanged — E2E participants are unaffected.

### H4: An HTTP polling endpoint can coexist with WebSockets on the leader-board worker

- Status: VERIFIED (by design constraint)
- Reason: The Durable Object worker is the sole owner and only mechanism for accessing channel state. The polling endpoint must live on the same worker.

## Exploration Log

### Key design decisions:

1. URL fragment (#) preserves zero-knowledge but was superseded by the cleartext gateway design
2. The server needs an HTTP polling endpoint alongside WebSockets for tool-limited agents
3. Rather than storing the plaintext private key, store it encrypted using the token as the encryption key
4. The hash(token) indexing scheme makes the server at-rest secure — given only hash(token) and encrypt(private_key, token), the key is irrecoverable

### Security tier summary:

| Threat | Protected? | Notes |
|--------|-----------|-------|
| Server breach at rest | Yes | hash(token) is irreversible, blob is undecryptable |
| Network eavesdropping | Yes | Token sent over TLS |
| Malicious server operator (active) | No | Inherent: server must see token to do crypto |
| Token holder impersonation | Yes | Token is the credential; possession = access |
| Revocation | Yes | Delete the blob; token becomes useless |

### Protocol:

1. User runs ve board invite --swarm <id>
2. CLI generates a random token (cryptographically strong)
3. CLI encrypts the swarm private key using the token as the encryption key
4. CLI uploads the encrypted blob to the server, keyed by hash(token)
5. CLI outputs: https://leader-board.example.com/invite/{token}
6. Agent presents the token with each API request
7. Server uses the token to decrypt the private key in memory, performs encrypt/decrypt, then discards
8. Revocation: delete the encrypted blob. Token resolves to nothing.

## Findings

### Verified Findings

- URL fragment preserves zero-knowledge (HTTP spec)
- Raw key in URL breaks server trust model (H1 falsified)
- hash(token) scheme is at-rest secure (cryptographic analysis)
- Durable Object is the only viable host (architecture constraint)

## Proposed Chunks

### 0. gateway_token_storage: Encrypted key blob storage on the Durable Object

Add routes to the leader-board DO worker for managing token-encrypted private key blobs:
- PUT /gateway/keys — accepts {token_hash, encrypted_blob, swarm_id}, stores the encrypted key blob indexed by hash(token)
- GET /gateway/keys/{token_hash} — returns the encrypted blob (internal use)
- DELETE /gateway/keys/{token_hash} — deletes the blob (revocation)

### 1. gateway_cleartext_api: Cleartext gateway HTTP routes for agent message access

Add HTTP endpoints to the DO worker:
- GET /gateway/{token}/channels/{channel}/messages?after={cursor} — returns plaintext messages
- POST /gateway/{token}/channels/{channel}/messages — accepts plaintext, server encrypts
- Optional long-poll variant with ?wait=30

### 2. invite_cli_command: ve board invite and ve board revoke CLI commands

- ve board invite --swarm <id> — generate token, encrypt key, upload blob, output URL
- ve board revoke <token> — delete blob, invalidate token
- Must display explicit opt-in warning

### 3. invite_instruction_page: Agent-facing instruction page at /invite/{token}

Serve a plain text/markdown page describing:
- Swarm and channel context
- HTTP API protocol with example curl commands
- Security model explanation

## Resolution Rationale

Design converged on a cleartext gateway pattern with strong at-rest security properties. The key insight: store encrypt(private_key, token) indexed by hash(token) on the server. The server can never decrypt the key at rest. Users explicitly opt in via ve board invite.
