// Chunk: docs/chunks/gateway_cleartext_api - Server-side crypto for cleartext gateway
/**
 * Gateway crypto module — replicates the Python src/board/crypto.py algorithms
 * in TypeScript for server-side use in the cleartext gateway.
 *
 * Algorithms:
 * - SHA-256 token hashing
 * - XSalsa20-Poly1305 (NaCl secretbox) for blob and message encryption
 * - Ed25519 → Curve25519 conversion (SHA-512 + clamping)
 * - HKDF-SHA256 for symmetric key derivation
 */

import nacl from "tweetnacl";
import { hkdf } from "@noble/hashes/hkdf.js";
import { sha256, sha512 } from "@noble/hashes/sha2.js";

// --- Hex / Base64 Utilities ---

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

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function base64ToBytes(b64: string): Uint8Array {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

// --- Public API ---

/**
 * SHA-256 hash of the token, returned as hex string.
 * Used to look up the encrypted key blob in storage.
 */
export function hashToken(token: string): string {
  const tokenBytes = new TextEncoder().encode(token);
  const hash = sha256(tokenBytes);
  return bytesToHex(hash);
}

/**
 * Decrypt the base64-encoded encrypted blob using the token as the
 * NaCl secretbox key. Returns the raw Ed25519 seed (32 bytes).
 *
 * The token is hex-encoded (64 chars = 32 bytes). It's decoded from hex
 * and used directly as the secretbox key.
 *
 * The blob format is: base64(nonce (24 bytes) || ciphertext)
 */
export function decryptBlob(encryptedBlobB64: string, token: string): Uint8Array {
  const key = hexToBytes(token);
  if (key.length !== 32) {
    throw new Error("Token must be 32 bytes (64 hex chars)");
  }

  const raw = base64ToBytes(encryptedBlobB64);
  if (raw.length < nacl.secretbox.nonceLength + nacl.secretbox.overheadLength) {
    throw new Error("Encrypted blob too short");
  }

  const nonce = raw.slice(0, nacl.secretbox.nonceLength);
  const ciphertext = raw.slice(nacl.secretbox.nonceLength);

  const plaintext = nacl.secretbox.open(ciphertext, nonce, key);
  if (!plaintext) {
    throw new Error("Decryption failed — invalid token or corrupted blob");
  }

  return plaintext;
}

/**
 * Derive the 32-byte symmetric encryption key from an Ed25519 seed.
 *
 * Replicates Python crypto.py derive_symmetric_key:
 * 1. SHA-512(seed) → first 32 bytes
 * 2. Clamp for Ed25519 → Curve25519 conversion
 * 3. HKDF-SHA256(ikm=clamped, salt=empty, info="leader-board-message-encryption")
 */
export function deriveSymmetricKey(seed: Uint8Array): Uint8Array {
  // Step 1: SHA-512 of the seed (matches nacl.bindings.crypto_sign_ed25519_sk_to_curve25519)
  const hash = sha512(seed);

  // Step 2: Take first 32 bytes and clamp (Ed25519 → Curve25519)
  const curve25519Private = hash.slice(0, 32);
  curve25519Private[0] &= 248;
  curve25519Private[31] &= 127;
  curve25519Private[31] |= 64;

  // Step 3: HKDF-SHA256
  const info = new TextEncoder().encode("leader-board-message-encryption");
  return hkdf(sha256, curve25519Private, new Uint8Array(0), info, 32);
}

/**
 * Decrypt a message encrypted with NaCl secretbox.
 * Input: base64(nonce (24 bytes) || ciphertext)
 * Returns: plaintext UTF-8 string
 */
export function decryptMessage(ciphertextB64: string, symmetricKey: Uint8Array): string {
  const raw = base64ToBytes(ciphertextB64);
  if (raw.length < nacl.secretbox.nonceLength + nacl.secretbox.overheadLength) {
    throw new Error("Ciphertext too short");
  }

  const nonce = raw.slice(0, nacl.secretbox.nonceLength);
  const ciphertext = raw.slice(nacl.secretbox.nonceLength);

  const plaintext = nacl.secretbox.open(ciphertext, nonce, symmetricKey);
  if (!plaintext) {
    throw new Error("Message decryption failed");
  }

  return new TextDecoder().decode(plaintext);
}

/**
 * Encrypt a plaintext message with NaCl secretbox.
 * Returns: base64(nonce (24 bytes) || ciphertext)
 */
export function encryptMessage(plaintext: string, symmetricKey: Uint8Array): string {
  const plaintextBytes = new TextEncoder().encode(plaintext);
  const nonce = nacl.randomBytes(nacl.secretbox.nonceLength);
  const ciphertext = nacl.secretbox(plaintextBytes, nonce, symmetricKey);

  // Combine nonce + ciphertext (matches Python format)
  const combined = new Uint8Array(nonce.length + ciphertext.length);
  combined.set(nonce);
  combined.set(ciphertext, nonce.length);

  return bytesToBase64(combined);
}
