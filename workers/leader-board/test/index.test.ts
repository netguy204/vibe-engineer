// Chunk: docs/chunks/leader_board_durable_objects - Cloudflare DO adapter
/**
 * Tests for the Worker entry point routing.
 */
import { SELF } from "cloudflare:test";
import { describe, it, expect } from "vitest";

describe("Worker routing", () => {
  it("returns 400 when swarm query param is missing", async () => {
    const resp = await SELF.fetch("https://test.local/");
    expect(resp.status).toBe(400);
    const body = await resp.json() as { error: string };
    expect(body.error).toContain("swarm");
  });

  it("routes to DO when swarm param is present (non-WS gets 426)", async () => {
    const resp = await SELF.fetch("https://test.local?swarm=test-swarm");
    // The DO returns 426 for non-WebSocket requests
    expect(resp.status).toBe(426);
  });

  it("routes WebSocket upgrade to DO", async () => {
    const resp = await SELF.fetch("https://test.local?swarm=test-swarm", {
      headers: { Upgrade: "websocket" },
    });
    // Should get a WebSocket back (101 status)
    expect(resp.webSocket).toBeDefined();
  });
});
