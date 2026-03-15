// Chunk: docs/chunks/leader_board_durable_objects - Cloudflare DO adapter
import { describe, it, expect } from "vitest";
import * as ed from "@noble/ed25519";
import { generateChallenge, verifySignature } from "../src/auth";

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

describe("generateChallenge", () => {
  it("returns a 64-character hex string (32 bytes)", () => {
    const nonce = generateChallenge();
    expect(nonce).toHaveLength(64);
    expect(/^[0-9a-f]{64}$/.test(nonce)).toBe(true);
  });

  it("generates different nonces each time", () => {
    const a = generateChallenge();
    const b = generateChallenge();
    expect(a).not.toBe(b);
  });
});

describe("verifySignature", () => {
  it("accepts a valid signature", async () => {
    const privKey = ed.utils.randomPrivateKey();
    const pubKey = await ed.getPublicKeyAsync(privKey);
    const nonce = generateChallenge();
    const nonceBytes = new Uint8Array(
      nonce.match(/.{2}/g)!.map((h) => parseInt(h, 16))
    );
    const signature = await ed.signAsync(nonceBytes, privKey);

    const valid = await verifySignature(
      bytesToHex(pubKey),
      nonce,
      bytesToHex(signature)
    );
    expect(valid).toBe(true);
  });

  it("rejects a tampered signature", async () => {
    const privKey = ed.utils.randomPrivateKey();
    const pubKey = await ed.getPublicKeyAsync(privKey);
    const nonce = generateChallenge();
    const nonceBytes = new Uint8Array(
      nonce.match(/.{2}/g)!.map((h) => parseInt(h, 16))
    );
    const signature = await ed.signAsync(nonceBytes, privKey);

    // Tamper with signature
    const tampered = new Uint8Array(signature);
    tampered[0] ^= 0xff;

    const valid = await verifySignature(
      bytesToHex(pubKey),
      nonce,
      bytesToHex(tampered)
    );
    expect(valid).toBe(false);
  });

  it("rejects signature from a different key", async () => {
    const privKey1 = ed.utils.randomPrivateKey();
    const privKey2 = ed.utils.randomPrivateKey();
    const pubKey2 = await ed.getPublicKeyAsync(privKey2);
    const nonce = generateChallenge();
    const nonceBytes = new Uint8Array(
      nonce.match(/.{2}/g)!.map((h) => parseInt(h, 16))
    );
    // Sign with key 1, verify with key 2
    const signature = await ed.signAsync(nonceBytes, privKey1);

    const valid = await verifySignature(
      bytesToHex(pubKey2),
      nonce,
      bytesToHex(signature)
    );
    expect(valid).toBe(false);
  });

  it("returns false for malformed hex input", async () => {
    const valid = await verifySignature("not-hex", "also-bad", "definitely-bad");
    expect(valid).toBe(false);
  });
});
