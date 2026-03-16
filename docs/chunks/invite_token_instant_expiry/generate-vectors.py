#!/usr/bin/env python3
"""Generate correct cross-language test vectors for invite token crypto.

This script generates vectors using the CORRECT Python crypto logic:
- Token hash: SHA-256 of raw token bytes (not hex string)
- Token key: HKDF-SHA256 derived from raw token bytes (not raw token as key)

These vectors replace the broken ones in the original gateway_cleartext_api
vector script which hashed the hex string and used the raw token as the
secretbox key.
"""
import base64
import hashlib
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.board.crypto import derive_token_key
from nacl.secret import SecretBox


def generate_vectors():
    # Same deterministic inputs as original vectors
    seed_hex = "aa" * 32  # 32 bytes of 0xaa
    token_hex = "bb" * 32  # 32 bytes of 0xbb

    token_bytes = bytes.fromhex(token_hex)
    seed_bytes = bytes.fromhex(seed_hex)

    # Bug 1 fix: hash raw bytes, not hex string
    token_hash = hashlib.sha256(token_bytes).hexdigest()

    # Bug 2 fix: derive key via HKDF, not use raw token
    token_key = derive_token_key(token_bytes)

    # Encrypt the seed hex string (matching CLI: encrypt(seed.hex(), sym_key))
    blob_box = SecretBox(token_key)
    blob_fixed_nonce = b"\x02" * SecretBox.NONCE_SIZE  # 24 bytes of 0x02
    encrypted_blob_with_nonce = blob_box.encrypt(
        seed_hex.encode("utf-8"), blob_fixed_nonce
    )
    encrypted_blob_b64 = base64.b64encode(encrypted_blob_with_nonce).decode("ascii")

    vectors = {
        "token_hex": token_hex,
        "token_hash_hex": token_hash,
        "token_key_hex": token_key.hex(),
        "seed_hex": seed_hex,
        "encrypted_blob_b64": encrypted_blob_b64,
        "blob_fixed_nonce_hex": blob_fixed_nonce.hex(),
    }

    print(json.dumps(vectors, indent=2))


if __name__ == "__main__":
    generate_vectors()
