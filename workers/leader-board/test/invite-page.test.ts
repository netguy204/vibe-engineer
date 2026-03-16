// Chunk: docs/chunks/invite_instruction_page - Invite instruction page tests
/**
 * Tests for the invite instruction page route.
 * Exercises GET /invite/{token}?swarm={swarmId} through SELF.fetch.
 */
import { SELF } from "cloudflare:test";
import { describe, it, expect } from "vitest";
import nacl from "tweetnacl";
import { sha256 } from "@noble/hashes/sha2.js";
import { hkdf } from "@noble/hashes/hkdf.js";
import * as ed from "@noble/ed25519";

// --- Helpers (replicated from gateway-api.test.ts) ---

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

// Chunk: docs/chunks/invite_token_instant_expiry - Fixed to match Python crypto.py
function hashTokenText(tokenHex: string): string {
  const tokenBytes = hexToBytes(tokenHex);
  const hash = sha256(tokenBytes);
  return bytesToHex(hash);
}

function deriveTokenKeyLocal(tokenHex: string): Uint8Array {
  const tokenBytes = hexToBytes(tokenHex);
  const info = new TextEncoder().encode("leader-board-invite-token");
  return hkdf(sha256, tokenBytes, new Uint8Array(0), info, 32);
}

function encryptBlobWithToken(seed: Uint8Array, tokenHex: string): string {
  const key = deriveTokenKeyLocal(tokenHex);
  // Python encrypts seed.hex() as UTF-8, so we encrypt the hex string
  const seedHex = bytesToHex(seed);
  const plaintextBytes = new TextEncoder().encode(seedHex);
  const nonce = nacl.randomBytes(nacl.secretbox.nonceLength);
  const ciphertext = nacl.secretbox(plaintextBytes, nonce, key);
  const combined = new Uint8Array(nonce.length + ciphertext.length);
  combined.set(nonce);
  combined.set(ciphertext, nonce.length);
  return bytesToBase64(combined);
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

  return { privKey, pubKeyHex, seed: privKey };
}

/** Set up a swarm with a gateway token */
async function setupGateway(testId: string): Promise<{
  swarmId: string;
  tokenHex: string;
  tokenHash: string;
  seed: Uint8Array;
  privKey: Uint8Array;
}> {
  const swarmId = `invite-${testId}-${Date.now()}`;
  const { privKey, seed } = await registerSwarm(swarmId);

  const tokenBytes = nacl.randomBytes(32);
  const tokenHex = bytesToHex(tokenBytes);
  const tokenHash = hashTokenText(tokenHex);
  const encryptedBlob = encryptBlobWithToken(seed, tokenHex);

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

  return { swarmId, tokenHex, tokenHash, seed, privKey };
}

// --- Tests ---

describe("Invite instruction page", () => {
  it("GET /invite/{token} returns instruction page for valid token", async () => {
    const { swarmId, tokenHex } = await setupGateway("valid");

    const resp = await SELF.fetch(
      `https://test.local/invite/${tokenHex}?swarm=${swarmId}`
    );
    expect(resp.status).toBe(200);
    expect(resp.headers.get("Content-Type")).toBe("text/plain; charset=utf-8");

    const body = await resp.text();
    expect(body).toContain("# Swarm Invite");
    expect(body).toContain(tokenHex);
    expect(body).toContain("curl");
  });

  it("instruction page lists available channels", async () => {
    const { swarmId, tokenHex } = await setupGateway("channels");

    // Create some channels by posting messages
    for (const channel of ["changelog", "status"]) {
      await SELF.fetch(
        `https://test.local/gateway/${tokenHex}/channels/${channel}/messages?swarm=${swarmId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ body: "seed message" }),
        }
      );
    }

    const resp = await SELF.fetch(
      `https://test.local/invite/${tokenHex}?swarm=${swarmId}`
    );
    expect(resp.status).toBe(200);
    const body = await resp.text();
    expect(body).toContain("changelog");
    expect(body).toContain("status");
  });

  it("instruction page includes working curl command patterns", async () => {
    const { swarmId, tokenHex } = await setupGateway("curl-patterns");

    const resp = await SELF.fetch(
      `https://test.local/invite/${tokenHex}?swarm=${swarmId}`
    );
    const body = await resp.text();

    // Should contain gateway API URL patterns
    expect(body).toContain(`/gateway/${tokenHex}/channels/`);
    expect(body).toContain(`swarm=${swarmId}`);
    expect(body).toContain("curl");
    expect(body).toContain("-X POST");
  });

  it("invalid token returns 404 with clear error", async () => {
    const swarmId = `invite-invalid-${Date.now()}`;
    await registerSwarm(swarmId);

    const fakeToken = bytesToHex(nacl.randomBytes(32));
    const resp = await SELF.fetch(
      `https://test.local/invite/${fakeToken}?swarm=${swarmId}`
    );
    expect(resp.status).toBe(404);
    const body = await resp.text();
    expect(body).toContain("Invalid or expired invite token");
  });

  it("revoked token returns 404", async () => {
    const { swarmId, tokenHex, tokenHash } = await setupGateway("revoked");

    // Revoke the token
    const delResp = await SELF.fetch(
      `https://test.local/gateway/keys/${tokenHash}?swarm=${swarmId}`,
      { method: "DELETE" }
    );
    expect(delResp.status).toBe(200);

    // Try to access invite page
    const resp = await SELF.fetch(
      `https://test.local/invite/${tokenHex}?swarm=${swarmId}`
    );
    expect(resp.status).toBe(404);
  });

  // Chunk: docs/chunks/invite_path_routing_fix - Swarm-less invite routing tests
  it("GET /invite/{token} works without swarm query parameter", async () => {
    const { tokenHex } = await setupGateway("no-swarm-param");

    const resp = await SELF.fetch(
      `https://test.local/invite/${tokenHex}`
    );
    expect(resp.status).toBe(200);
    expect(resp.headers.get("Content-Type")).toBe("text/plain; charset=utf-8");

    const body = await resp.text();
    expect(body).toContain("# Swarm Invite");
    expect(body).toContain(tokenHex);
  });

  it("invalid token without swarm parameter returns 404", async () => {
    const fakeToken = bytesToHex(nacl.randomBytes(32));
    const resp = await SELF.fetch(
      `https://test.local/invite/${fakeToken}`
    );
    expect(resp.status).toBe(404);
    const body = await resp.text();
    expect(body).toContain("Invalid or expired invite token");
  });

  it("revoked token without swarm parameter returns 404", async () => {
    const { swarmId, tokenHex, tokenHash } = await setupGateway("revoked-no-swarm");

    // Revoke the token
    const delResp = await SELF.fetch(
      `https://test.local/gateway/keys/${tokenHash}?swarm=${swarmId}`,
      { method: "DELETE" }
    );
    expect(delResp.status).toBe(200);

    // Try to access invite page without swarm param
    const resp = await SELF.fetch(
      `https://test.local/invite/${tokenHex}`
    );
    expect(resp.status).toBe(404);
  });

  it("non-GET method returns 405", async () => {
    const { swarmId, tokenHex } = await setupGateway("method-not-allowed");

    const resp = await SELF.fetch(
      `https://test.local/invite/${tokenHex}?swarm=${swarmId}`,
      { method: "POST" }
    );
    expect(resp.status).toBe(405);
  });

  it("instruction page shows 'no channels' message when empty", async () => {
    const { swarmId, tokenHex } = await setupGateway("no-channels");

    const resp = await SELF.fetch(
      `https://test.local/invite/${tokenHex}?swarm=${swarmId}`
    );
    expect(resp.status).toBe(200);
    const body = await resp.text();
    expect(body).toContain("No channels exist yet");
  });

  it("instruction page includes security section", async () => {
    const { swarmId, tokenHex } = await setupGateway("security");

    const resp = await SELF.fetch(
      `https://test.local/invite/${tokenHex}?swarm=${swarmId}`
    );
    const body = await resp.text();
    expect(body).toContain("## Security");
    expect(body).toContain("Keep it secret");
    expect(body).toContain("revoke");
  });

  // Chunk: docs/chunks/invite_token_instant_expiry - End-to-end cross-language test
  it("end-to-end: Python-compatible create → fetch cycle works", async () => {
    // Simulate the Python CLI flow with correct crypto:
    // 1. Register a swarm
    const swarmId = `invite-e2e-python-${Date.now()}`;
    const { seed } = await registerSwarm(swarmId);

    // 2. Generate token and compute hash/blob using Python-compatible logic
    const tokenBytes = nacl.randomBytes(32);
    const tokenHex = bytesToHex(tokenBytes);

    // Hash raw bytes (matching Python: hashlib.sha256(token).hexdigest())
    const tokenHash = bytesToHex(sha256(tokenBytes));

    // Derive key via HKDF (matching Python: derive_token_key(token))
    const info = new TextEncoder().encode("leader-board-invite-token");
    const tokenKey = hkdf(sha256, tokenBytes, new Uint8Array(0), info, 32);

    // Encrypt seed.hex() with HKDF-derived key (matching Python: encrypt(seed.hex(), sym_key))
    const seedHex = bytesToHex(seed);
    const plaintextBytes = new TextEncoder().encode(seedHex);
    const nonce = nacl.randomBytes(nacl.secretbox.nonceLength);
    const ciphertext = nacl.secretbox(plaintextBytes, nonce, tokenKey);
    const combined = new Uint8Array(nonce.length + ciphertext.length);
    combined.set(nonce);
    combined.set(ciphertext, nonce.length);
    const encryptedBlob = bytesToBase64(combined);

    // 3. PUT the blob (simulating CLI's HTTP upload)
    const putResp = await SELF.fetch(
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
    expect(putResp.status).toBe(200);

    // 4. GET /invite/{token} without ?swarm= param (using KV routing)
    const inviteResp = await SELF.fetch(
      `https://test.local/invite/${tokenHex}`
    );
    expect(inviteResp.status).toBe(200);
    expect(inviteResp.headers.get("Content-Type")).toBe("text/plain; charset=utf-8");

    const body = await inviteResp.text();
    expect(body).toContain("# Swarm Invite");
    expect(body).toContain(tokenHex);
    expect(body).toContain("curl");
  });
});
