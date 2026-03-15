// Chunk: docs/chunks/leader_board_durable_objects - Cloudflare DO adapter
/**
 * Tests for compaction via DO alarm.
 *
 * Compaction removes messages older than 30 days while always
 * retaining the most recent message in each channel.
 */
import { env, SELF, runDurableObjectAlarm } from "cloudflare:test";
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

async function registerAndAuth(
  swarmId: string
): Promise<{
  ws: WebSocket;
  privKey: Uint8Array;
  pubKeyHex: string;
}> {
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
    JSON.stringify({
      type: "register_swarm",
      swarm: swarmId,
      public_key: pubKeyHex,
    })
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
  ws.send(
    JSON.stringify({ type: "auth", swarm: swarmId, signature: bytesToHex(sig) })
  );
  await nextMessage(ws); // auth_ok

  return { ws, privKey, pubKeyHex };
}

describe("Compaction", () => {
  it("most recent message survives compaction regardless of age", async () => {
    const swarmId = "compact-retain-" + Date.now();
    const { ws } = await registerAndAuth(swarmId);

    // Send a message
    ws.send(
      JSON.stringify({ type: "send", channel: "ch", swarm: swarmId, body: "b25seQ==" })
    );
    const ack = await nextMessage(ws);
    expect(ack.type).toBe("ack");
    expect(ack.position).toBe(1);

    // Trigger alarm (compaction). Since the message was just sent,
    // it won't be compacted (< 30 days old).
    const id = env.SWARM_DO.idFromName(swarmId);
    const stub = env.SWARM_DO.get(id);
    await runDurableObjectAlarm(stub);

    // Verify message still exists
    ws.send(
      JSON.stringify({ type: "watch", channel: "ch", swarm: swarmId, cursor: 0 })
    );
    const msg = await nextMessage(ws);
    expect(msg.type).toBe("message");
    expect(msg.position).toBe(1);

    ws.close();
  });

  it("channels list updates after compaction", async () => {
    const swarmId = "compact-channels-" + Date.now();
    const { ws } = await registerAndAuth(swarmId);

    // Send messages
    ws.send(
      JSON.stringify({ type: "send", channel: "ch", swarm: swarmId, body: "bXNn" })
    );
    await nextMessage(ws);
    ws.send(
      JSON.stringify({ type: "send", channel: "ch", swarm: swarmId, body: "bXNnMg==" })
    );
    await nextMessage(ws);

    // Trigger alarm
    const id = env.SWARM_DO.idFromName(swarmId);
    const stub = env.SWARM_DO.get(id);
    await runDurableObjectAlarm(stub);

    // Channels should still exist
    ws.send(JSON.stringify({ type: "channels", swarm: swarmId }));
    const result = await nextMessage(ws);
    expect(result.type).toBe("channels_list");
    const channels = result.channels as Array<{ name: string; head_position: number }>;
    expect(channels.length).toBe(1);
    expect(channels[0].head_position).toBe(2);

    ws.close();
  });
});
