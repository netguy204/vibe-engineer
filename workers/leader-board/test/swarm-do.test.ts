// Chunk: docs/chunks/leader_board_durable_objects - Cloudflare DO adapter
/**
 * Tests for SwarmDO connection lifecycle and auth flow.
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

describe("SwarmDO auth flow", () => {
  it("register_swarm stores key and returns auth_ok", async () => {
    const swarmId = "auth-reg-" + Date.now();
    const privKey = ed.utils.randomPrivateKey();
    const pubKey = await ed.getPublicKeyAsync(privKey);

    const ws = await openWs(swarmId);
    const challenge = await nextMessage(ws);
    expect(challenge.type).toBe("challenge");
    expect(typeof challenge.nonce).toBe("string");

    ws.send(
      JSON.stringify({
        type: "register_swarm",
        swarm: swarmId,
        public_key: bytesToHex(pubKey),
      })
    );

    const result = await nextMessage(ws);
    expect(result.type).toBe("auth_ok");
    ws.close();
  });

  it("valid auth signature returns auth_ok", async () => {
    const swarmId = "auth-valid-" + Date.now();
    const privKey = ed.utils.randomPrivateKey();
    const pubKey = await ed.getPublicKeyAsync(privKey);

    // Register
    const regWs = await openWs(swarmId);
    await nextMessage(regWs); // challenge
    regWs.send(
      JSON.stringify({
        type: "register_swarm",
        swarm: swarmId,
        public_key: bytesToHex(pubKey),
      })
    );
    await nextMessage(regWs); // auth_ok
    regWs.close();

    // Authenticate
    const ws = await openWs(swarmId);
    const challenge = await nextMessage(ws);
    const nonce = challenge.nonce as string;

    const signature = await ed.signAsync(hexToBytes(nonce), privKey);
    ws.send(
      JSON.stringify({ type: "auth", swarm: swarmId, signature: bytesToHex(signature) })
    );

    const result = await nextMessage(ws);
    expect(result.type).toBe("auth_ok");
    ws.close();
  });

  it("invalid signature returns auth_failed error and closes", async () => {
    const swarmId = "auth-invalid-" + Date.now();
    const privKey = ed.utils.randomPrivateKey();
    const pubKey = await ed.getPublicKeyAsync(privKey);

    // Register
    const regWs = await openWs(swarmId);
    await nextMessage(regWs);
    regWs.send(
      JSON.stringify({
        type: "register_swarm",
        swarm: swarmId,
        public_key: bytesToHex(pubKey),
      })
    );
    await nextMessage(regWs);
    regWs.close();

    // Authenticate with bad signature
    const ws = await openWs(swarmId);
    await nextMessage(ws); // challenge

    ws.send(
      JSON.stringify({
        type: "auth",
        swarm: swarmId,
        signature: "00".repeat(64), // invalid signature
      })
    );

    const result = await nextMessage(ws);
    expect(result.type).toBe("error");
    expect(result.code).toBe("auth_failed");
  });

  it("auth on unregistered swarm returns swarm_not_found", async () => {
    const swarmId = "auth-noreg-" + Date.now();

    const ws = await openWs(swarmId);
    await nextMessage(ws); // challenge

    ws.send(
      JSON.stringify({
        type: "auth",
        swarm: swarmId,
        signature: "00".repeat(64),
      })
    );

    const result = await nextMessage(ws);
    expect(result.type).toBe("error");
    expect(result.code).toBe("swarm_not_found");
  });

  it("invalid frame during handshake returns invalid_frame", async () => {
    const swarmId = "auth-badjson-" + Date.now();

    const ws = await openWs(swarmId);
    await nextMessage(ws); // challenge

    ws.send("not valid json {{{");

    const result = await nextMessage(ws);
    expect(result.type).toBe("error");
    expect(result.code).toBe("invalid_frame");
  });
});

describe("SwarmDO non-websocket", () => {
  it("returns 426 for non-WebSocket request", async () => {
    const resp = await SELF.fetch("https://test.local?swarm=test");
    expect(resp.status).toBe(426);
  });
});
