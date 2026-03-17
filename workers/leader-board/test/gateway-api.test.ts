// Chunk: docs/chunks/gateway_cleartext_api - Cleartext gateway API tests
/**
 * Tests for the cleartext gateway HTTP routes.
 * Exercises the full cleartext API through SELF.fetch.
 */
import { SELF } from "cloudflare:test";
import { describe, it, expect, beforeAll } from "vitest";
import nacl from "tweetnacl";
import { hkdf } from "@noble/hashes/hkdf.js";
import { sha256 } from "@noble/hashes/sha2.js";
import { sha512 } from "@noble/hashes/sha2.js";
import * as ed from "@noble/ed25519";

// --- Helpers (replicate crypto for test setup) ---

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function hexToBytes(hex: string): Uint8Array {
  return new Uint8Array(hex.match(/.{2}/g)!.map((h) => parseInt(h, 16)));
}

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function base64ToBytes(b64: string): Uint8Array {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

// Chunk: docs/chunks/gateway_message_read_fix - Hash raw token bytes, not hex string
function hashTokenText(tokenHex: string): string {
  const tokenBytes = hexToBytes(tokenHex);
  const hash = sha256(tokenBytes);
  return bytesToHex(hash);
}

// Chunk: docs/chunks/gateway_message_read_fix - HKDF key derivation matching production deriveTokenKey
function deriveTokenKeyLocal(tokenHex: string): Uint8Array {
  const tokenBytes = hexToBytes(tokenHex);
  const info = new TextEncoder().encode("leader-board-invite-token");
  return hkdf(sha256, tokenBytes, new Uint8Array(0), info, 32);
}

// Chunk: docs/chunks/gateway_message_read_fix - Encrypt hex-encoded seed string (matching Python CLI)
function encryptBlobWithToken(seed: Uint8Array, tokenHex: string): string {
  const key = deriveTokenKeyLocal(tokenHex);
  const seedHex = bytesToHex(seed);
  const plaintextBytes = new TextEncoder().encode(seedHex);
  const nonce = nacl.randomBytes(nacl.secretbox.nonceLength);
  const ciphertext = nacl.secretbox(plaintextBytes, nonce, key);
  const combined = new Uint8Array(nonce.length + ciphertext.length);
  combined.set(nonce);
  combined.set(ciphertext, nonce.length);
  return bytesToBase64(combined);
}

function deriveSymmetricKey(seed: Uint8Array): Uint8Array {
  const hash = sha512(seed);
  const curve25519Private = hash.slice(0, 32);
  curve25519Private[0] &= 248;
  curve25519Private[31] &= 127;
  curve25519Private[31] |= 64;
  const info = new TextEncoder().encode("leader-board-message-encryption");
  return hkdf(sha256, curve25519Private, new Uint8Array(0), info, 32);
}

function encryptMessageForWs(plaintext: string, symmetricKey: Uint8Array): string {
  const plaintextBytes = new TextEncoder().encode(plaintext);
  const nonce = nacl.randomBytes(nacl.secretbox.nonceLength);
  const ciphertext = nacl.secretbox(plaintextBytes, nonce, symmetricKey);
  const combined = new Uint8Array(nonce.length + ciphertext.length);
  combined.set(nonce);
  combined.set(ciphertext, nonce.length);
  return bytesToBase64(combined);
}

function decryptWsMessage(ciphertextB64: string, symmetricKey: Uint8Array): string {
  const raw = base64ToBytes(ciphertextB64);
  const nonce = raw.slice(0, nacl.secretbox.nonceLength);
  const ciphertext = raw.slice(nacl.secretbox.nonceLength);
  const plaintext = nacl.secretbox.open(ciphertext, nonce, symmetricKey);
  if (!plaintext) throw new Error("Decryption failed");
  return new TextDecoder().decode(plaintext);
}

/** WebSocket helpers */
function nextMessage(ws: WebSocket): Promise<Record<string, unknown>> {
  return new Promise((resolve) => {
    ws.addEventListener("message", (e) => resolve(JSON.parse(e.data as string)), {
      once: true,
    });
  });
}

async function openWs(swarmId: string): Promise<WebSocket> {
  const resp = await SELF.fetch(`https://test.local?swarm=${swarmId}`, {
    headers: { Upgrade: "websocket" },
  });
  const ws = resp.webSocket!;
  ws.accept();
  return ws;
}

async function registerSwarm(swarmId: string): Promise<{
  privKey: Uint8Array;
  pubKeyHex: string;
  seed: Uint8Array;
}> {
  const privKey = ed.utils.randomPrivateKey();
  const pubKey = await ed.getPublicKeyAsync(privKey);
  const pubKeyHex = bytesToHex(pubKey);

  const ws = await openWs(swarmId);
  await nextMessage(ws); // challenge
  ws.send(
    JSON.stringify({
      type: "register_swarm",
      swarm: swarmId,
      public_key: pubKeyHex,
    })
  );
  const res = await nextMessage(ws);
  expect(res.type).toBe("auth_ok");
  ws.close();

  // The privKey from noble/ed25519 IS the 32-byte seed
  return { privKey, pubKeyHex, seed: privKey };
}

async function authenticateWs(
  swarmId: string,
  privKey: Uint8Array
): Promise<WebSocket> {
  const ws = await openWs(swarmId);
  const challenge = await nextMessage(ws);
  const nonce = challenge.nonce as string;
  const sig = await ed.signAsync(hexToBytes(nonce), privKey);
  ws.send(
    JSON.stringify({ type: "auth", swarm: swarmId, signature: bytesToHex(sig) })
  );
  const res = await nextMessage(ws);
  expect(res.type).toBe("auth_ok");
  return ws;
}

/** Set up a swarm with a gateway token, returning the token and swarm info */
async function setupGateway(testId: string): Promise<{
  swarmId: string;
  tokenHex: string;
  tokenHash: string;
  seed: Uint8Array;
  symmetricKey: Uint8Array;
  privKey: Uint8Array;
}> {
  const swarmId = `gw-${testId}-${Date.now()}`;
  const { privKey, seed } = await registerSwarm(swarmId);

  // Generate a token
  const tokenBytes = nacl.randomBytes(32);
  const tokenHex = bytesToHex(tokenBytes);
  const tokenHash = hashTokenText(tokenHex);

  // Encrypt the seed with the token
  const encryptedBlob = encryptBlobWithToken(seed, tokenHex);

  // Store via PUT /gateway/keys
  const resp = await SELF.fetch(
    `https://test.local/gateway/keys?swarm=${swarmId}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        token_hash: tokenHash,
        encrypted_blob: encryptedBlob,
      }),
    }
  );
  expect(resp.status).toBe(200);

  const symmetricKey = deriveSymmetricKey(seed);

  return { swarmId, tokenHex, tokenHash, seed, symmetricKey, privKey };
}

// --- Tests ---

describe("Gateway cleartext API", () => {
  it("POST stores an encrypted message, returns position", async () => {
    const { swarmId, tokenHex } = await setupGateway("post-basic");

    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/changelog/messages?swarm=${swarmId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body: "hello gateway" }),
      }
    );
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as { position: number; channel: string };
    expect(body.position).toBe(1);
    expect(body.channel).toBe("changelog");
  });

  it("GET retrieves decrypted messages", async () => {
    const { swarmId, tokenHex } = await setupGateway("get-basic");

    // POST a message first
    await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/changelog/messages?swarm=${swarmId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body: "hello get test" }),
      }
    );

    // GET messages
    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/changelog/messages?after=0&swarm=${swarmId}`
    );
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as {
      messages: Array<{ position: number; body: string; sent_at: string }>;
    };
    expect(body.messages).toHaveLength(1);
    expect(body.messages[0].position).toBe(1);
    expect(body.messages[0].body).toBe("hello get test");
    expect(body.messages[0].sent_at).toBeDefined();
  });

  it("full round-trip: POST cleartext → GET cleartext", async () => {
    const { swarmId, tokenHex } = await setupGateway("roundtrip");

    const messages = ["first message", "second message", "third message"];
    for (const msg of messages) {
      await SELF.fetch(
        `https://test.local/gateway/${tokenHex}/channels/test-ch/messages?swarm=${swarmId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ body: msg }),
        }
      );
    }

    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/test-ch/messages?after=0&swarm=${swarmId}`
    );
    const body = (await resp.json()) as {
      messages: Array<{ position: number; body: string }>;
    };
    expect(body.messages).toHaveLength(3);
    expect(body.messages[0].body).toBe("first message");
    expect(body.messages[1].body).toBe("second message");
    expect(body.messages[2].body).toBe("third message");
    expect(body.messages[0].position).toBe(1);
    expect(body.messages[1].position).toBe(2);
    expect(body.messages[2].position).toBe(3);
  });

  it("WebSocket client reads what gateway POST wrote (encryption compatibility)", async () => {
    const { swarmId, tokenHex, symmetricKey, privKey } =
      await setupGateway("ws-reads-gw");

    // POST via gateway
    await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/shared/messages?swarm=${swarmId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body: "from gateway to ws" }),
      }
    );

    // Read via WebSocket
    const ws = await authenticateWs(swarmId, privKey);
    ws.send(
      JSON.stringify({
        type: "watch",
        channel: "shared",
        swarm: swarmId,
        cursor: 0,
      })
    );
    const msg = await nextMessage(ws);
    expect(msg.type).toBe("message");
    expect(msg.position).toBe(1);

    // The WebSocket receives ciphertext; decrypt client-side
    const decrypted = decryptWsMessage(msg.body as string, symmetricKey);
    expect(decrypted).toBe("from gateway to ws");
    ws.close();
  });

  it("gateway GET reads what WebSocket client wrote", async () => {
    const { swarmId, tokenHex, symmetricKey, privKey } =
      await setupGateway("gw-reads-ws");

    // Send encrypted via WebSocket
    const ws = await authenticateWs(swarmId, privKey);
    const ciphertext = encryptMessageForWs("from ws to gateway", symmetricKey);
    ws.send(
      JSON.stringify({
        type: "send",
        channel: "shared",
        swarm: swarmId,
        body: ciphertext,
      })
    );
    const ack = await nextMessage(ws);
    expect(ack.type).toBe("ack");
    ws.close();

    // GET via gateway — should get plaintext
    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/shared/messages?after=0&swarm=${swarmId}`
    );
    const body = (await resp.json()) as {
      messages: Array<{ position: number; body: string }>;
    };
    expect(body.messages).toHaveLength(1);
    expect(body.messages[0].body).toBe("from ws to gateway");
  });

  it("invalid token returns 401", async () => {
    const swarmId = `gw-invalid-${Date.now()}`;
    await registerSwarm(swarmId);

    const fakeToken = bytesToHex(nacl.randomBytes(32));
    const resp = await SELF.fetch(
      `https://test.local/gateway/${fakeToken}/channels/ch/messages?swarm=${swarmId}`
    );
    expect(resp.status).toBe(401);
    const body = (await resp.json()) as { error: string };
    expect(body.error).toContain("Invalid or revoked token");
  });

  it("revoked token returns 401", async () => {
    const { swarmId, tokenHex, tokenHash } = await setupGateway("revoked");

    // Revoke the token
    const delResp = await SELF.fetch(
      `https://test.local/gateway/keys/${tokenHash}?swarm=${swarmId}`,
      { method: "DELETE" }
    );
    expect(delResp.status).toBe(200);

    // Try to use it
    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/ch/messages?swarm=${swarmId}`
    );
    expect(resp.status).toBe(401);
  });

  it("long-poll returns immediately if messages exist", async () => {
    const { swarmId, tokenHex } = await setupGateway("longpoll-immediate");

    // POST a message
    await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/ch/messages?swarm=${swarmId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body: "already here" }),
      }
    );

    // GET with ?wait=5 — should return immediately since messages exist
    const start = Date.now();
    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/ch/messages?after=0&wait=5&swarm=${swarmId}`
    );
    const elapsed = Date.now() - start;
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as {
      messages: Array<{ body: string }>;
    };
    expect(body.messages).toHaveLength(1);
    expect(body.messages[0].body).toBe("already here");
    // Should have returned very quickly (well under 5 seconds)
    expect(elapsed).toBeLessThan(3000);
  });

  it("long-poll blocks then returns on new message", async () => {
    const { swarmId, tokenHex } = await setupGateway("longpoll-block");

    // Start long-poll (no messages yet on this channel, but need to create channel first)
    // POST to create the channel
    await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/poll-ch/messages?swarm=${swarmId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body: "seed message" }),
      }
    );

    // Start long-poll waiting for messages after position 1
    const pollPromise = SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/poll-ch/messages?after=1&wait=10&swarm=${swarmId}`
    );

    // Give the poll a moment to register
    await new Promise((r) => setTimeout(r, 100));

    // POST a new message
    await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/poll-ch/messages?swarm=${swarmId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body: "wakeup message" }),
      }
    );

    const resp = await pollPromise;
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as {
      messages: Array<{ body: string; position: number }>;
    };
    expect(body.messages.length).toBeGreaterThan(0);
    expect(body.messages[0].body).toBe("wakeup message");
  });

  it("long-poll returns empty on timeout", async () => {
    const { swarmId, tokenHex } = await setupGateway("longpoll-timeout");

    // GET with ?wait=1 on a channel with no messages after cursor 999
    // First create the channel
    await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/empty-ch/messages?swarm=${swarmId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body: "seed" }),
      }
    );

    const start = Date.now();
    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/empty-ch/messages?after=999&wait=1&swarm=${swarmId}`
    );
    const elapsed = Date.now() - start;
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as { messages: unknown[] };
    expect(body.messages).toHaveLength(0);
    // Should have waited approximately 1 second
    expect(elapsed).toBeGreaterThanOrEqual(800);
  }, 10000);

  it("GET with no messages and no wait returns empty immediately", async () => {
    const { swarmId, tokenHex } = await setupGateway("empty-no-wait");

    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/empty/messages?after=0&swarm=${swarmId}`
    );
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as { messages: unknown[] };
    expect(body.messages).toHaveLength(0);
  });

  it("invalid channel name returns 400", async () => {
    const { swarmId, tokenHex } = await setupGateway("bad-channel");

    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/bad channel!/messages?swarm=${swarmId}`
    );
    expect(resp.status).toBe(400);
  });

  it("POST with missing body field returns 400", async () => {
    const { swarmId, tokenHex } = await setupGateway("bad-body");

    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/ch/messages?swarm=${swarmId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      }
    );
    expect(resp.status).toBe(400);
  });

  // Chunk: docs/chunks/gateway_webhook_collector - Webhook collector endpoint tests

  it("webhook: JSON payload is stored as envelope with base64 raw_body", async () => {
    const { swarmId, tokenHex, symmetricKey } = await setupGateway("wh-json");
    const jsonPayload = JSON.stringify({ event: "push", ref: "refs/heads/main" });

    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/hooks/webhook?swarm=${swarmId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonPayload,
      }
    );
    expect(resp.status).toBe(200);
    const result = (await resp.json()) as { position: number; channel: string };
    expect(result.position).toBe(1);
    expect(result.channel).toBe("hooks");

    // Read back via messages endpoint and verify envelope
    const getResp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/hooks/messages?after=0&swarm=${swarmId}`
    );
    const body = (await getResp.json()) as {
      messages: Array<{ position: number; body: string }>;
    };
    expect(body.messages).toHaveLength(1);
    const envelope = JSON.parse(body.messages[0].body);
    expect(envelope.content_type).toBe("application/json");
    expect(envelope.source).toBe("webhook");
    // Decode the base64 raw_body and verify it matches the original payload
    const decoded = new TextDecoder().decode(base64ToBytes(envelope.raw_body));
    expect(decoded).toBe(jsonPayload);
  });

  it("webhook: form-encoded payload is stored as envelope", async () => {
    const { swarmId, tokenHex } = await setupGateway("wh-form");
    const formData = "key=value&foo=bar";

    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/hooks/webhook?swarm=${swarmId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData,
      }
    );
    expect(resp.status).toBe(200);

    const getResp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/hooks/messages?after=0&swarm=${swarmId}`
    );
    const body = (await getResp.json()) as {
      messages: Array<{ body: string }>;
    };
    const envelope = JSON.parse(body.messages[0].body);
    expect(envelope.content_type).toBe("application/x-www-form-urlencoded");
    expect(envelope.source).toBe("webhook");
    const decoded = new TextDecoder().decode(base64ToBytes(envelope.raw_body));
    expect(decoded).toBe(formData);
  });

  it("webhook: plain text payload is stored as envelope", async () => {
    const { swarmId, tokenHex } = await setupGateway("wh-text");
    const textPayload = "Hello, this is a plain text webhook";

    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/hooks/webhook?swarm=${swarmId}`,
      {
        method: "POST",
        headers: { "Content-Type": "text/plain" },
        body: textPayload,
      }
    );
    expect(resp.status).toBe(200);

    const getResp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/hooks/messages?after=0&swarm=${swarmId}`
    );
    const body = (await getResp.json()) as {
      messages: Array<{ body: string }>;
    };
    const envelope = JSON.parse(body.messages[0].body);
    expect(envelope.content_type).toBe("text/plain");
    expect(envelope.source).toBe("webhook");
    const decoded = new TextDecoder().decode(base64ToBytes(envelope.raw_body));
    expect(decoded).toBe(textPayload);
  });

  it("webhook: XML payload is stored as envelope", async () => {
    const { swarmId, tokenHex } = await setupGateway("wh-xml");
    const xmlPayload = '<?xml version="1.0"?><event><type>deploy</type></event>';

    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/hooks/webhook?swarm=${swarmId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/xml" },
        body: xmlPayload,
      }
    );
    expect(resp.status).toBe(200);

    const getResp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/hooks/messages?after=0&swarm=${swarmId}`
    );
    const body = (await getResp.json()) as {
      messages: Array<{ body: string }>;
    };
    const envelope = JSON.parse(body.messages[0].body);
    expect(envelope.content_type).toBe("application/xml");
    expect(envelope.source).toBe("webhook");
    const decoded = new TextDecoder().decode(base64ToBytes(envelope.raw_body));
    expect(decoded).toBe(xmlPayload);
  });

  it("webhook: OPTIONS returns 204 with CORS headers", async () => {
    const { swarmId, tokenHex } = await setupGateway("wh-cors");

    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/hooks/webhook?swarm=${swarmId}`,
      { method: "OPTIONS" }
    );
    expect(resp.status).toBe(204);
    expect(resp.headers.get("Access-Control-Allow-Origin")).toBe("*");
    expect(resp.headers.get("Access-Control-Allow-Methods")).toContain("POST");
    expect(resp.headers.get("Access-Control-Allow-Methods")).toContain("OPTIONS");
    expect(resp.headers.get("Access-Control-Allow-Headers")).toContain("Content-Type");
  });

  it("webhook: POST response includes CORS headers", async () => {
    const { swarmId, tokenHex } = await setupGateway("wh-cors-post");

    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/hooks/webhook?swarm=${swarmId}`,
      {
        method: "POST",
        headers: { "Content-Type": "text/plain" },
        body: "cors test",
      }
    );
    expect(resp.status).toBe(200);
    expect(resp.headers.get("Access-Control-Allow-Origin")).toBe("*");
  });

  it("webhook: invalid token returns 401", async () => {
    const swarmId = `gw-wh-invalid-${Date.now()}`;
    await registerSwarm(swarmId);

    const fakeToken = bytesToHex(nacl.randomBytes(32));
    const resp = await SELF.fetch(
      `https://test.local/gateway/${fakeToken}/channels/hooks/webhook?swarm=${swarmId}`,
      {
        method: "POST",
        headers: { "Content-Type": "text/plain" },
        body: "should fail",
      }
    );
    expect(resp.status).toBe(401);
    const body = (await resp.json()) as { error: string };
    expect(body.error).toContain("Invalid or revoked token");
  });

  it("webhook: oversized payload returns 400", async () => {
    const { swarmId, tokenHex } = await setupGateway("wh-oversize");

    // Create a payload that will exceed 1MB after base64 encoding + envelope
    const largePayload = "x".repeat(1_048_577);
    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/hooks/webhook?swarm=${swarmId}`,
      {
        method: "POST",
        headers: { "Content-Type": "text/plain" },
        body: largePayload,
      }
    );
    expect(resp.status).toBe(400);
    const body = (await resp.json()) as { error: string };
    expect(body.error).toContain("too large");
  });

  it("webhook: missing Content-Type defaults to application/octet-stream", async () => {
    const { swarmId, tokenHex } = await setupGateway("wh-no-ct");

    // Use a Blob with no type to avoid the fetch runtime auto-setting Content-Type
    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/hooks/webhook?swarm=${swarmId}`,
      {
        method: "POST",
        body: new Blob([new Uint8Array([0x00, 0x01, 0x02])]),
      }
    );
    expect(resp.status).toBe(200);

    const getResp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/hooks/messages?after=0&swarm=${swarmId}`
    );
    const body = (await getResp.json()) as {
      messages: Array<{ body: string }>;
    };
    const envelope = JSON.parse(body.messages[0].body);
    expect(envelope.content_type).toBe("application/octet-stream");
  });

  it("webhook: non-POST method returns 405", async () => {
    const { swarmId, tokenHex } = await setupGateway("wh-method");

    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/hooks/webhook?swarm=${swarmId}`,
      { method: "GET" }
    );
    expect(resp.status).toBe(405);
  });

  // Chunk: docs/chunks/gateway_cors_and_docs - CORS header tests
  it("OPTIONS /gateway/{token}/channels/{channel}/messages returns 204 with CORS headers", async () => {
    const { swarmId, tokenHex } = await setupGateway("options-cors");

    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/changelog/messages?swarm=${swarmId}`,
      { method: "OPTIONS" }
    );
    expect(resp.status).toBe(204);
    expect(resp.headers.get("Access-Control-Allow-Origin")).toBe("*");
    expect(resp.headers.get("Access-Control-Allow-Methods")).toContain("GET");
    expect(resp.headers.get("Access-Control-Allow-Methods")).toContain("POST");
    expect(resp.headers.get("Access-Control-Allow-Methods")).toContain("OPTIONS");
    expect(resp.headers.get("Access-Control-Allow-Headers")).toContain("Content-Type");
  });

  it("GET gateway response includes CORS headers", async () => {
    const { swarmId, tokenHex } = await setupGateway("get-cors");

    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/ch/messages?after=0&swarm=${swarmId}`
    );
    expect(resp.status).toBe(200);
    expect(resp.headers.get("Access-Control-Allow-Origin")).toBe("*");
  });

  it("POST gateway response includes CORS headers", async () => {
    const { swarmId, tokenHex } = await setupGateway("post-cors");

    const resp = await SELF.fetch(
      `https://test.local/gateway/${tokenHex}/channels/changelog/messages?swarm=${swarmId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body: "cors test" }),
      }
    );
    expect(resp.status).toBe(200);
    expect(resp.headers.get("Access-Control-Allow-Origin")).toBe("*");
  });
});
