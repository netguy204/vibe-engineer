#!/usr/bin/env python3
"""Generate cross-language test vectors for gateway crypto compatibility testing.

Outputs JSON with known seed, symmetric key, plaintext, ciphertext, token, and encrypted blob
that can be embedded in TypeScript tests to verify wire compatibility.
"""
import base64
import hashlib
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.board.crypto import derive_symmetric_key, encrypt, decrypt, _hkdf_sha256
import nacl.signing
import nacl.bindings
import nacl.utils
from nacl.secret import SecretBox


def generate_vectors():
    # Use a fixed seed for reproducibility (32 bytes)
    seed = bytes.fromhex("a" * 64)  # 32 bytes of 0xaa

    # Derive symmetric key
    symmetric_key = derive_symmetric_key(seed)

    # Show the intermediate Curve25519 private key for debugging
    signing_key = nacl.signing.SigningKey(seed)
    sk_bytes = signing_key.encode() + signing_key.verify_key.encode()
    curve25519_private = nacl.bindings.crypto_sign_ed25519_sk_to_curve25519(sk_bytes)

    # Encrypt a known message with a fixed nonce for deterministic test
    plaintext = "hello from python"
    # Use SecretBox with a known nonce for deterministic output
    box = SecretBox(symmetric_key)
    fixed_nonce = b"\x01" * SecretBox.NONCE_SIZE  # 24 bytes of 0x01
    ciphertext_with_nonce = box.encrypt(plaintext.encode("utf-8"), fixed_nonce)
    ciphertext_b64 = base64.b64encode(ciphertext_with_nonce).decode("ascii")

    # Also generate a random-nonce ciphertext that we can test decryption of
    random_ciphertext_b64 = encrypt(plaintext, symmetric_key)

    # Token and blob for blob decryption testing
    token = bytes.fromhex("b" * 64)  # 32 bytes of 0xbb
    token_hash = hashlib.sha256(token.hex().encode()).hexdigest()
    # Encrypt the seed using the token as key (same as invite flow)
    blob_box = SecretBox(token)
    blob_fixed_nonce = b"\x02" * SecretBox.NONCE_SIZE  # 24 bytes of 0x02
    encrypted_blob_with_nonce = blob_box.encrypt(seed, blob_fixed_nonce)
    encrypted_blob_b64 = base64.b64encode(encrypted_blob_with_nonce).decode("ascii")

    vectors = {
        "seed_hex": seed.hex(),
        "curve25519_private_hex": curve25519_private.hex(),
        "symmetric_key_hex": symmetric_key.hex(),
        "plaintext": plaintext,
        "fixed_nonce_ciphertext_b64": ciphertext_b64,
        "random_nonce_ciphertext_b64": random_ciphertext_b64,
        "token_hex": token.hex(),
        "token_hash_hex": token_hash,
        "encrypted_blob_b64": encrypted_blob_b64,
        "blob_fixed_nonce_hex": blob_fixed_nonce.hex(),
    }

    print(json.dumps(vectors, indent=2))


if __name__ == "__main__":
    generate_vectors()
