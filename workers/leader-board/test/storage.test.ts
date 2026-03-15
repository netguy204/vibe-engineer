// Chunk: docs/chunks/leader_board_durable_objects - Cloudflare DO adapter
/**
 * Storage adapter contract tests — TypeScript port of
 * tests/test_leader_board_adapter_contract.py
 *
 * Tests verify the storage layer indirectly through the DO WebSocket interface,
 * observing correct positions, channel listings, and compaction behavior.
 */
import { SELF } from "cloudflare:test";
import { describe, it, expect } from "vitest";
import * as ed from "@noble/ed25519";

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function hexToBytes(hex: string): Uint8Array {
  return new Uint8Array(hex.match(/.{2}/g)!.map((h) => parseInt(h, 16)));
}

function nextMessage(ws: WebSocket): Promise<Record<string, unknown>> {
  return new Promise((resolve) => {
    ws.addEventListener("message", (e) => resolve(JSON.parse(e.data as string)), {
      once: true,
    });
  });
}

async function registerAndAuth(swarmId: string): Promise<WebSocket> {
  const privKey = ed.utils.randomPrivateKey();
  const pubKey = await ed.getPublicKeyAsync(privKey);
  const pubKeyHex = bytesToHex(pubKey);

  // Register
  const regResp = await SELF.fetch(`https://test.local?swarm=${swarmId}`, {
    headers: { Upgrade: "websocket" },
  });
  const regWs = regResp.webSocket!;
  regWs.accept();
  await nextMessage(regWs); // challenge
  regWs.send(
    JSON.stringify({ type: "register_swarm", swarm: swarmId, public_key: pubKeyHex })
  );
  await nextMessage(regWs); // auth_ok
  regWs.close();

  // Auth
  const resp = await SELF.fetch(`https://test.local?swarm=${swarmId}`, {
    headers: { Upgrade: "websocket" },
  });
  const ws = resp.webSocket!;
  ws.accept();
  const challenge = await nextMessage(ws);
  const nonce = challenge.nonce as string;
  const sig = await ed.signAsync(hexToBytes(nonce), privKey);
  ws.send(JSON.stringify({ type: "auth", swarm: swarmId, signature: bytesToHex(sig) }));
  await nextMessage(ws); // auth_ok

  return ws;
}

describe("SwarmStorage contract (via WebSocket integration)", () => {
  it("assigns monotonic positions starting at 1", async () => {
    const swarmId = "contract-mono-" + Date.now();
    const ws = await registerAndAuth(swarmId);

    ws.send(JSON.stringify({ type: "send", channel: "ch", swarm: swarmId, body: "YQ==" }));
    const ack1 = await nextMessage(ws);
    expect(ack1.type).toBe("ack");
    expect(ack1.position).toBe(1);

    ws.send(JSON.stringify({ type: "send", channel: "ch", swarm: swarmId, body: "Yg==" }));
    const ack2 = await nextMessage(ws);
    expect(ack2.position).toBe(2);

    ws.send(JSON.stringify({ type: "send", channel: "ch", swarm: swarmId, body: "Yw==" }));
    const ack3 = await nextMessage(ws);
    expect(ack3.position).toBe(3);

    ws.close();
  });

  it("read_after cursor 0 returns first message (via watch)", async () => {
    const swarmId = "contract-read0-" + Date.now();
    const ws = await registerAndAuth(swarmId);

    ws.send(JSON.stringify({ type: "send", channel: "ch", swarm: swarmId, body: "Zmlyc3Q=" }));
    await nextMessage(ws); // ack

    ws.send(JSON.stringify({ type: "watch", channel: "ch", swarm: swarmId, cursor: 0 }));
    const msg = await nextMessage(ws);
    expect(msg.type).toBe("message");
    expect(msg.position).toBe(1);

    ws.close();
  });

  it("read_after cursor at head returns nothing (watch blocks)", async () => {
    const swarmId = "contract-head-" + Date.now();
    const ws = await registerAndAuth(swarmId);

    ws.send(JSON.stringify({ type: "send", channel: "ch", swarm: swarmId, body: "b25seQ==" }));
    const ack = await nextMessage(ws);
    expect(ack.position).toBe(1);

    // Watch from cursor 1 — should block until next message
    ws.send(JSON.stringify({ type: "watch", channel: "ch", swarm: swarmId, cursor: 1 }));

    // Send another message to unblock the watcher
    ws.send(JSON.stringify({ type: "send", channel: "ch", swarm: swarmId, body: "bmV4dA==" }));

    const responses: Record<string, unknown>[] = [];
    for (let i = 0; i < 2; i++) {
      responses.push(await nextMessage(ws));
    }

    const ack2 = responses.find((r) => r.type === "ack");
    const watchMsg = responses.find((r) => r.type === "message");
    expect(ack2).toBeDefined();
    expect(ack2!.position).toBe(2);
    expect(watchMsg).toBeDefined();
    expect(watchMsg!.position).toBe(2);

    ws.close();
  });

  it("list channels returns correct head/oldest positions", async () => {
    const swarmId = "contract-list-" + Date.now();
    const ws = await registerAndAuth(swarmId);

    ws.send(JSON.stringify({ type: "send", channel: "alpha", swarm: swarmId, body: "YTE=" }));
    await nextMessage(ws);
    ws.send(JSON.stringify({ type: "send", channel: "alpha", swarm: swarmId, body: "YTI=" }));
    await nextMessage(ws);
    ws.send(JSON.stringify({ type: "send", channel: "beta", swarm: swarmId, body: "YjE=" }));
    await nextMessage(ws);

    ws.send(JSON.stringify({ type: "channels", swarm: swarmId }));
    const result = await nextMessage(ws);
    expect(result.type).toBe("channels_list");

    const channels = result.channels as Array<{
      name: string;
      head_position: number;
      oldest_position: number;
    }>;
    const byName = Object.fromEntries(channels.map((c) => [c.name, c]));

    expect(byName["alpha"]).toBeDefined();
    expect(byName["alpha"].head_position).toBe(2);
    expect(byName["alpha"].oldest_position).toBe(1);
    expect(byName["beta"]).toBeDefined();
    expect(byName["beta"].head_position).toBe(1);

    ws.close();
  });

  it("multiple channels are independent", async () => {
    const swarmId = "contract-indep-" + Date.now();
    const ws = await registerAndAuth(swarmId);

    ws.send(JSON.stringify({ type: "send", channel: "ch-a", swarm: swarmId, body: "YQ==" }));
    const ack_a = await nextMessage(ws);
    ws.send(JSON.stringify({ type: "send", channel: "ch-b", swarm: swarmId, body: "Yg==" }));
    const ack_b = await nextMessage(ws);

    expect(ack_a.position).toBe(1);
    expect(ack_b.position).toBe(1);

    ws.send(JSON.stringify({ type: "watch", channel: "ch-a", swarm: swarmId, cursor: 0 }));
    const msg_a = await nextMessage(ws);
    expect(msg_a.type).toBe("message");
    expect(msg_a.body).toBe("YQ==");

    ws.send(JSON.stringify({ type: "watch", channel: "ch-b", swarm: swarmId, cursor: 0 }));
    const msg_b = await nextMessage(ws);
    expect(msg_b.type).toBe("message");
    expect(msg_b.body).toBe("Yg==");

    ws.close();
  });
});
