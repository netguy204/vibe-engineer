// Chunk: docs/chunks/leader_board_durable_objects - Cloudflare DO adapter
/**
 * End-to-end integration tests — full WebSocket lifecycle.
 *
 * Tests verify wire protocol compatibility with the spec and
 * exercise the complete flow: register → auth → send → watch → receive.
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

async function openWs(swarmId: string): Promise<WebSocket> {
  const resp = await SELF.fetch(`https://test.local?swarm=${swarmId}`, {
    headers: { Upgrade: "websocket" },
  });
  const ws = resp.webSocket!;
  ws.accept();
  return ws;
}

async function registerSwarm(
  swarmId: string
): Promise<{
  privKey: Uint8Array;
  pubKeyHex: string;
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

  return { privKey, pubKeyHex };
}

async function authenticateWs(
  swarmId: string,
  privKey: Uint8Array
): Promise<WebSocket> {
  const ws = await openWs(swarmId);
  const challenge = await nextMessage(ws);
  expect(challenge.type).toBe("challenge");

  const nonce = challenge.nonce as string;
  const sig = await ed.signAsync(hexToBytes(nonce), privKey);
  ws.send(
    JSON.stringify({ type: "auth", swarm: swarmId, signature: bytesToHex(sig) })
  );

  const res = await nextMessage(ws);
  expect(res.type).toBe("auth_ok");
  return ws;
}

describe("E2E: Full lifecycle", () => {
  it("register → auth → send → watch → receive message", async () => {
    const swarmId = "e2e-lifecycle-" + Date.now();
    const { privKey } = await registerSwarm(swarmId);
    const ws = await authenticateWs(swarmId, privKey);

    // Send a message
    ws.send(
      JSON.stringify({
        type: "send",
        channel: "steward",
        swarm: swarmId,
        body: "aGVsbG8gd29ybGQ=",
      })
    );
    const ack = await nextMessage(ws);
    expect(ack.type).toBe("ack");
    expect(ack.channel).toBe("steward");
    expect(ack.position).toBe(1);

    // Watch from cursor 0 — should get the message immediately
    ws.send(
      JSON.stringify({
        type: "watch",
        channel: "steward",
        swarm: swarmId,
        cursor: 0,
      })
    );
    const msg = await nextMessage(ws);
    expect(msg.type).toBe("message");
    expect(msg.channel).toBe("steward");
    expect(msg.position).toBe(1);
    expect(msg.body).toBe("aGVsbG8gd29ybGQ=");
    expect(typeof msg.sent_at).toBe("string");

    ws.close();
  });

  it("wire protocol frame fields match spec exactly", async () => {
    const swarmId = "e2e-wire-" + Date.now();
    const { privKey } = await registerSwarm(swarmId);
    const ws = await authenticateWs(swarmId, privKey);

    // Verify ack frame structure
    ws.send(
      JSON.stringify({
        type: "send",
        channel: "test-ch",
        swarm: swarmId,
        body: "dGVzdA==",
      })
    );
    const ack = await nextMessage(ws);
    expect(Object.keys(ack).sort()).toEqual(["channel", "position", "type"]);
    expect(ack.type).toBe("ack");
    expect(typeof ack.channel).toBe("string");
    expect(typeof ack.position).toBe("number");

    // Verify message frame structure
    ws.send(
      JSON.stringify({ type: "watch", channel: "test-ch", swarm: swarmId, cursor: 0 })
    );
    const msg = await nextMessage(ws);
    expect(Object.keys(msg).sort()).toEqual([
      "body",
      "channel",
      "position",
      "sent_at",
      "type",
    ]);
    expect(msg.type).toBe("message");

    // Verify channels_list frame structure
    ws.send(JSON.stringify({ type: "channels", swarm: swarmId }));
    const chList = await nextMessage(ws);
    expect(chList.type).toBe("channels_list");
    expect(Array.isArray(chList.channels)).toBe(true);
    const ch = (chList.channels as Array<Record<string, unknown>>)[0];
    expect(Object.keys(ch).sort()).toEqual([
      "head_position",
      "name",
      "oldest_position",
    ]);

    // Verify swarm_info frame structure
    ws.send(JSON.stringify({ type: "swarm_info", swarm: swarmId }));
    const info = await nextMessage(ws);
    expect(info.type).toBe("swarm_info");
    expect(typeof info.swarm).toBe("string");
    expect(typeof info.created_at).toBe("string");

    ws.close();
  });

  it("concurrent connections: watcher receives message from sender", async () => {
    const swarmId = "e2e-concurrent-" + Date.now();
    const { privKey } = await registerSwarm(swarmId);

    const sender = await authenticateWs(swarmId, privKey);
    const watcher = await authenticateWs(swarmId, privKey);

    // Sender sends a message to create the channel
    sender.send(
      JSON.stringify({
        type: "send",
        channel: "shared",
        swarm: swarmId,
        body: "Zmlyc3Q=",
      })
    );
    const ack1 = await nextMessage(sender);
    expect(ack1.position).toBe(1);

    // Watcher watches from cursor 1 (blocking wait for next)
    watcher.send(
      JSON.stringify({ type: "watch", channel: "shared", swarm: swarmId, cursor: 1 })
    );

    // Sender sends another message
    sender.send(
      JSON.stringify({
        type: "send",
        channel: "shared",
        swarm: swarmId,
        body: "c2Vjb25k",
      })
    );
    const ack2 = await nextMessage(sender);
    expect(ack2.position).toBe(2);

    // Watcher should receive the message
    const watchMsg = await nextMessage(watcher);
    expect(watchMsg.type).toBe("message");
    expect(watchMsg.position).toBe(2);
    expect(watchMsg.body).toBe("c2Vjb25k");

    sender.close();
    watcher.close();
  });

  it("reconnection: resumes from last cursor", async () => {
    const swarmId = "e2e-reconnect-" + Date.now();
    const { privKey } = await registerSwarm(swarmId);

    // First connection: send 2 messages, read 1
    const ws1 = await authenticateWs(swarmId, privKey);
    ws1.send(
      JSON.stringify({ type: "send", channel: "ch", swarm: swarmId, body: "bXNnMQ==" })
    );
    await nextMessage(ws1); // ack
    ws1.send(
      JSON.stringify({ type: "send", channel: "ch", swarm: swarmId, body: "bXNnMg==" })
    );
    await nextMessage(ws1); // ack

    ws1.send(
      JSON.stringify({ type: "watch", channel: "ch", swarm: swarmId, cursor: 0 })
    );
    const msg1 = await nextMessage(ws1);
    expect(msg1.position).toBe(1);
    ws1.close();

    // Second connection: resume from cursor 1
    const ws2 = await authenticateWs(swarmId, privKey);
    ws2.send(
      JSON.stringify({ type: "watch", channel: "ch", swarm: swarmId, cursor: 1 })
    );
    const msg2 = await nextMessage(ws2);
    expect(msg2.type).toBe("message");
    expect(msg2.position).toBe(2);
    expect(msg2.body).toBe("bXNnMg==");
    ws2.close();
  });

  it("watch on non-existent channel returns channel_not_found", async () => {
    const swarmId = "e2e-nofound-" + Date.now();
    const { privKey } = await registerSwarm(swarmId);
    const ws = await authenticateWs(swarmId, privKey);

    ws.send(
      JSON.stringify({
        type: "watch",
        channel: "nonexistent",
        swarm: swarmId,
        cursor: 0,
      })
    );
    const err = await nextMessage(ws);
    expect(err.type).toBe("error");
    expect(err.code).toBe("channel_not_found");

    ws.close();
  });

  it("swarm_info returns created_at timestamp", async () => {
    const swarmId = "e2e-info-" + Date.now();
    const { privKey } = await registerSwarm(swarmId);
    const ws = await authenticateWs(swarmId, privKey);

    ws.send(JSON.stringify({ type: "swarm_info", swarm: swarmId }));
    const info = await nextMessage(ws);
    expect(info.type).toBe("swarm_info");
    expect(info.swarm).toBe(swarmId);
    expect(typeof info.created_at).toBe("string");
    // Verify ISO 8601 format
    expect(new Date(info.created_at as string).toISOString()).toBeTruthy();

    ws.close();
  });

  it("invalid frame after auth returns invalid_frame error", async () => {
    const swarmId = "e2e-badframe-" + Date.now();
    const { privKey } = await registerSwarm(swarmId);
    const ws = await authenticateWs(swarmId, privKey);

    ws.send("{not valid json");
    const err = await nextMessage(ws);
    expect(err.type).toBe("error");
    expect(err.code).toBe("invalid_frame");

    ws.close();
  });

  it("error codes match spec exactly", async () => {
    const swarmId = "e2e-errcodes-" + Date.now();
    const { privKey } = await registerSwarm(swarmId);
    const ws = await authenticateWs(swarmId, privKey);

    // channel_not_found
    ws.send(
      JSON.stringify({ type: "watch", channel: "nope", swarm: swarmId, cursor: 0 })
    );
    const err1 = await nextMessage(ws);
    expect(err1.code).toBe("channel_not_found");

    // invalid_frame
    ws.send("}}bad{{");
    const err2 = await nextMessage(ws);
    expect(err2.code).toBe("invalid_frame");

    ws.close();
  });
});
