# Chunk: docs/chunks/leader_board_cli - Leader Board CLI client
"""Cryptographic primitives for Leader Board.

Key generation (Ed25519), key derivation (Ed25519 → Curve25519 → HKDF),
symmetric encryption (XChaCha20-Poly1305 / NaCl secretbox), and signing.

Spec reference: docs/trunk/SPEC.md §End-to-End Encryption
"""

from __future__ import annotations

import base64
import hashlib
import hmac

import base58
import nacl.bindings
import nacl.signing
import nacl.utils
from nacl.secret import SecretBox


def generate_keypair() -> tuple[bytes, bytes]:
    """Generate an Ed25519 key pair.

    Returns:
        (seed, public_key) where both are 32-byte values.
        The seed is the private key material used for signing and key derivation.
    """
    signing_key = nacl.signing.SigningKey.generate()
    seed = signing_key.encode()  # 32-byte seed
    public_key = signing_key.verify_key.encode()  # 32-byte public key
    return seed, public_key


def derive_swarm_id(public_key: bytes) -> str:
    """Derive a swarm ID from a public key.

    The swarm ID is the base58 encoding of the first 16 bytes of the public key,
    yielding a 22-44 character identifier.

    Spec reference: docs/trunk/SPEC.md §Swarm Model
    """
    return base58.b58encode(public_key[:16]).decode("ascii")


def _hkdf_sha256(ikm: bytes, length: int, salt: bytes = b"", info: bytes = b"") -> bytes:
    """HKDF-SHA256 key derivation (RFC 5869).

    Minimal implementation using hmac + hashlib to avoid pulling in
    the full `cryptography` package.
    """
    # Extract
    if not salt:
        salt = b"\x00" * 32
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    # Expand
    t = b""
    okm = b""
    for i in range(1, (length + 31) // 32 + 1):
        t = hmac.new(prk, t + info + bytes([i]), hashlib.sha256).digest()
        okm += t
    return okm[:length]


def derive_symmetric_key(seed: bytes) -> bytes:
    """Derive the 32-byte symmetric encryption key from an Ed25519 seed.

    Steps (per SPEC.md §End-to-End Encryption):
    1. Reconstruct the 64-byte Ed25519 secret key from the 32-byte seed
    2. Convert Ed25519 secret key → Curve25519 private key (32 bytes)
    3. HKDF-SHA256 with empty salt and info="leader-board-message-encryption"
    """
    # Reconstruct the full 64-byte Ed25519 secret key from seed
    signing_key = nacl.signing.SigningKey(seed)
    sk_bytes = signing_key.encode() + signing_key.verify_key.encode()  # 64-byte combined key

    # Convert to Curve25519
    curve25519_private = nacl.bindings.crypto_sign_ed25519_sk_to_curve25519(sk_bytes)

    # HKDF
    return _hkdf_sha256(
        ikm=curve25519_private,
        length=32,
        salt=b"",
        info=b"leader-board-message-encryption",
    )


def encrypt(plaintext: str, symmetric_key: bytes) -> str:
    """Encrypt plaintext using XChaCha20-Poly1305 (NaCl secretbox).

    Returns base64-encoded nonce (24 bytes) || ciphertext.

    Spec reference: docs/trunk/SPEC.md §Ciphertext Format
    """
    box = SecretBox(symmetric_key)
    nonce = nacl.utils.random(SecretBox.NONCE_SIZE)  # 24 bytes
    encrypted = box.encrypt(plaintext.encode("utf-8"), nonce)
    # nacl.secret.SecretBox.encrypt returns nonce || ciphertext by default
    return base64.b64encode(encrypted).decode("ascii")


def decrypt(ciphertext_b64: str, symmetric_key: bytes) -> str:
    """Decrypt a base64-encoded ciphertext (nonce || ciphertext).

    Returns the plaintext string.
    """
    raw = base64.b64decode(ciphertext_b64)
    box = SecretBox(symmetric_key)
    plaintext_bytes = box.decrypt(raw)
    return plaintext_bytes.decode("utf-8")


def sign(message: bytes, seed: bytes) -> bytes:
    """Sign a message with the Ed25519 private key (seed).

    Returns the 64-byte signature.
    """
    signing_key = nacl.signing.SigningKey(seed)
    signed = signing_key.sign(message)
    return signed.signature
