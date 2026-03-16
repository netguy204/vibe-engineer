// Chunk: docs/chunks/gateway_token_storage - Gateway key storage routes
/**
 * Tests for the gateway key storage HTTP routes.
 * Exercises the full round-trip: store → retrieve → delete → 404.
 */
import { SELF } from "cloudflare:test";
import { describe, it, expect } from "vitest";

const SWARM_ID = "test-swarm-gw";

describe("Gateway key storage routes", () => {
  it("PUT stores a key blob", async () => {
    const resp = await SELF.fetch(
      `https://test.local/gateway/keys?swarm=${SWARM_ID}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token_hash: "abc123hash",
          encrypted_blob: "encrypted-data-here",
        }),
      }
    );
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as { ok: boolean };
    expect(body.ok).toBe(true);
  });

  it("GET retrieves the blob", async () => {
    // First store a key
    await SELF.fetch(`https://test.local/gateway/keys?swarm=${SWARM_ID}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        token_hash: "retrieve-hash",
        encrypted_blob: "retrieve-blob",
      }),
    });

    const resp = await SELF.fetch(
      `https://test.local/gateway/keys/retrieve-hash?swarm=${SWARM_ID}`
    );
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as {
      token_hash: string;
      encrypted_blob: string;
      created_at: string;
    };
    expect(body.token_hash).toBe("retrieve-hash");
    expect(body.encrypted_blob).toBe("retrieve-blob");
    expect(body.created_at).toBeDefined();
  });

  it("GET returns 404 for unknown hash", async () => {
    const resp = await SELF.fetch(
      `https://test.local/gateway/keys/nonexistent?swarm=${SWARM_ID}`
    );
    expect(resp.status).toBe(404);
    const body = (await resp.json()) as { error: string };
    expect(body.error).toBeDefined();
  });

  it("DELETE removes the blob", async () => {
    // Store first
    await SELF.fetch(`https://test.local/gateway/keys?swarm=${SWARM_ID}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        token_hash: "delete-hash",
        encrypted_blob: "delete-blob",
      }),
    });

    const resp = await SELF.fetch(
      `https://test.local/gateway/keys/delete-hash?swarm=${SWARM_ID}`,
      { method: "DELETE" }
    );
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as { ok: boolean };
    expect(body.ok).toBe(true);
  });

  it("GET after DELETE returns 404", async () => {
    // Store, then delete, then GET
    await SELF.fetch(`https://test.local/gateway/keys?swarm=${SWARM_ID}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        token_hash: "roundtrip-hash",
        encrypted_blob: "roundtrip-blob",
      }),
    });

    await SELF.fetch(
      `https://test.local/gateway/keys/roundtrip-hash?swarm=${SWARM_ID}`,
      { method: "DELETE" }
    );

    const resp = await SELF.fetch(
      `https://test.local/gateway/keys/roundtrip-hash?swarm=${SWARM_ID}`
    );
    expect(resp.status).toBe(404);
  });

  it("DELETE of non-existent hash returns 404", async () => {
    const resp = await SELF.fetch(
      `https://test.local/gateway/keys/never-existed?swarm=${SWARM_ID}`,
      { method: "DELETE" }
    );
    expect(resp.status).toBe(404);
    const body = (await resp.json()) as { error: string };
    expect(body.error).toBeDefined();
  });

  it("PUT with missing fields returns 400", async () => {
    // Missing encrypted_blob
    const resp1 = await SELF.fetch(
      `https://test.local/gateway/keys?swarm=${SWARM_ID}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token_hash: "only-hash" }),
      }
    );
    expect(resp1.status).toBe(400);

    // Missing token_hash
    const resp2 = await SELF.fetch(
      `https://test.local/gateway/keys?swarm=${SWARM_ID}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ encrypted_blob: "only-blob" }),
      }
    );
    expect(resp2.status).toBe(400);

    // Empty body
    const resp3 = await SELF.fetch(
      `https://test.local/gateway/keys?swarm=${SWARM_ID}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      }
    );
    expect(resp3.status).toBe(400);
  });
});
