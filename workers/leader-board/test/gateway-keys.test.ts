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

  // Chunk: docs/chunks/invite_list_revoke - List and bulk-delete tests

  it("GET /gateway/keys returns empty list when no keys exist", async () => {
    const resp = await SELF.fetch(
      `https://test.local/gateway/keys?swarm=empty-swarm`
    );
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as { keys: unknown[] };
    expect(body.keys).toEqual([]);
  });

  it("GET /gateway/keys returns all stored keys", async () => {
    const listSwarm = "list-swarm";
    // Store 3 keys
    for (const hash of ["hash-aaa", "hash-bbb", "hash-ccc"]) {
      await SELF.fetch(
        `https://test.local/gateway/keys?swarm=${listSwarm}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            token_hash: hash,
            encrypted_blob: `blob-${hash}`,
          }),
        }
      );
    }

    const resp = await SELF.fetch(
      `https://test.local/gateway/keys?swarm=${listSwarm}`
    );
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as {
      keys: { token_hash: string; created_at: string; hint: string }[];
    };
    expect(body.keys).toHaveLength(3);
    const hashes = body.keys.map((k) => k.token_hash);
    expect(hashes).toContain("hash-aaa");
    expect(hashes).toContain("hash-bbb");
    expect(hashes).toContain("hash-ccc");
    // Each key should have created_at and hint
    for (const key of body.keys) {
      expect(key.created_at).toBeDefined();
      expect(key.hint).toBeDefined();
    }
  });

  it("GET /gateway/keys includes correct hint (first 8 chars of token_hash)", async () => {
    const hintSwarm = "hint-swarm";
    const longHash = "abcdef1234567890deadbeef";
    await SELF.fetch(
      `https://test.local/gateway/keys?swarm=${hintSwarm}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token_hash: longHash,
          encrypted_blob: "blob-hint",
        }),
      }
    );

    const resp = await SELF.fetch(
      `https://test.local/gateway/keys?swarm=${hintSwarm}`
    );
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as {
      keys: { token_hash: string; hint: string }[];
    };
    expect(body.keys[0].hint).toBe("abcdef12");
  });

  it("DELETE /gateway/keys removes all keys (bulk delete)", async () => {
    const bulkSwarm = "bulk-swarm";
    // Store 3 keys
    for (const hash of ["bulk-a", "bulk-b", "bulk-c"]) {
      await SELF.fetch(
        `https://test.local/gateway/keys?swarm=${bulkSwarm}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            token_hash: hash,
            encrypted_blob: `blob-${hash}`,
          }),
        }
      );
    }

    const delResp = await SELF.fetch(
      `https://test.local/gateway/keys?swarm=${bulkSwarm}`,
      { method: "DELETE" }
    );
    expect(delResp.status).toBe(200);
    const delBody = (await delResp.json()) as { ok: boolean; deleted: number };
    expect(delBody.ok).toBe(true);
    expect(delBody.deleted).toBe(3);

    // Verify list is now empty
    const listResp = await SELF.fetch(
      `https://test.local/gateway/keys?swarm=${bulkSwarm}`
    );
    const listBody = (await listResp.json()) as { keys: unknown[] };
    expect(listBody.keys).toHaveLength(0);
  });

  it("DELETE /gateway/keys on empty returns zero", async () => {
    const resp = await SELF.fetch(
      `https://test.local/gateway/keys?swarm=empty-bulk-swarm`,
      { method: "DELETE" }
    );
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as { ok: boolean; deleted: number };
    expect(body.ok).toBe(true);
    expect(body.deleted).toBe(0);
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
