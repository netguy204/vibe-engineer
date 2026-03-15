// Chunk: docs/chunks/leader_board_durable_objects - Cloudflare DO adapter
/**
 * Ed25519 authentication utilities for the leader board protocol.
 *
 * Uses @noble/ed25519 for signature verification. The CF Workers runtime
 * may not fully support Ed25519 via Web Crypto API, so noble/ed25519
 * provides a reliable pure-JS implementation.
 */

import * as ed from "@noble/ed25519";

/**
 * Generate a random 32-byte challenge nonce as a hex string.
 */
export function generateChallenge(): string {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return bytesToHex(bytes);
}

/**
 * Verify an Ed25519 signature over a nonce.
 *
 * @param publicKeyHex - Hex-encoded 32-byte Ed25519 public key
 * @param nonceHex - Hex-encoded nonce that was signed
 * @param signatureHex - Hex-encoded 64-byte Ed25519 signature
 * @returns true if the signature is valid, false otherwise
 */
export async function verifySignature(
  publicKeyHex: string,
  nonceHex: string,
  signatureHex: string
): Promise<boolean> {
  try {
    const signature = hexToBytes(signatureHex);
    const message = hexToBytes(nonceHex);
    const publicKey = hexToBytes(publicKeyHex);

    return await ed.verifyAsync(signature, message, publicKey);
  } catch {
    return false;
  }
}

// --- Hex utilities ---

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function hexToBytes(hex: string): Uint8Array {
  if (hex.length % 2 !== 0) {
    throw new Error("Invalid hex string length");
  }
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substring(i, i + 2), 16);
  }
  return bytes;
}
