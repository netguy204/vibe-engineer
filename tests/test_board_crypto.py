# Chunk: docs/chunks/leader_board_cli - Leader Board CLI client
"""Tests for board.crypto — key generation, encryption, signing."""

import pytest
from board.crypto import (
    decrypt,
    derive_swarm_id,
    derive_symmetric_key,
    encrypt,
    generate_keypair,
    sign,
)


def test_generate_keypair():
    """generate_keypair returns 32-byte seed and 32-byte public key."""
    seed, public_key = generate_keypair()
    assert isinstance(seed, bytes)
    assert isinstance(public_key, bytes)
    assert len(seed) == 32
    assert len(public_key) == 32


def test_generate_keypair_unique():
    """Each call produces a different key pair."""
    seed1, _ = generate_keypair()
    seed2, _ = generate_keypair()
    assert seed1 != seed2


def test_derive_swarm_id():
    """Swarm ID is base58 of first 16 bytes of public key, deterministic."""
    _, public_key = generate_keypair()
    id1 = derive_swarm_id(public_key)
    id2 = derive_swarm_id(public_key)
    assert id1 == id2
    assert isinstance(id1, str)
    assert len(id1) >= 1  # base58 of 16 bytes


def test_derive_symmetric_key():
    """Symmetric key derivation is deterministic for same seed."""
    seed, _ = generate_keypair()
    key1 = derive_symmetric_key(seed)
    key2 = derive_symmetric_key(seed)
    assert key1 == key2
    assert isinstance(key1, bytes)
    assert len(key1) == 32


def test_derive_symmetric_key_different_seeds():
    """Different seeds produce different symmetric keys."""
    seed1, _ = generate_keypair()
    seed2, _ = generate_keypair()
    assert derive_symmetric_key(seed1) != derive_symmetric_key(seed2)


def test_encrypt_decrypt_roundtrip():
    """Encrypt then decrypt recovers original plaintext."""
    seed, _ = generate_keypair()
    sym_key = derive_symmetric_key(seed)
    plaintext = "Hello, leader board!"
    ciphertext = encrypt(plaintext, sym_key)
    recovered = decrypt(ciphertext, sym_key)
    assert recovered == plaintext


def test_decrypt_wrong_key_fails():
    """Decrypting with a different key raises an exception."""
    seed1, _ = generate_keypair()
    seed2, _ = generate_keypair()
    key1 = derive_symmetric_key(seed1)
    key2 = derive_symmetric_key(seed2)
    ciphertext = encrypt("secret", key1)
    with pytest.raises(Exception):
        decrypt(ciphertext, key2)


def test_ciphertext_format():
    """Base64-decoded ciphertext starts with 24-byte nonce prefix."""
    import base64

    seed, _ = generate_keypair()
    sym_key = derive_symmetric_key(seed)
    ciphertext_b64 = encrypt("test message", sym_key)
    raw = base64.b64decode(ciphertext_b64)
    # nonce is 24 bytes, followed by at least some ciphertext + 16-byte tag
    assert len(raw) >= 24 + 16 + 1


def test_sign():
    """sign produces a valid Ed25519 signature verifiable with the public key."""
    from nacl.signing import VerifyKey

    seed, public_key = generate_keypair()
    message = b"challenge-nonce-data"
    signature = sign(message, seed)
    assert isinstance(signature, bytes)
    assert len(signature) == 64  # Ed25519 signature is 64 bytes
    # Verify with the public key
    verify_key = VerifyKey(public_key)
    verify_key.verify(message, signature)  # Should not raise
