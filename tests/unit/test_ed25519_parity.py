"""Cryptographic verification test: Parity between RFC 8032 and cryptography library."""

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from driving_eval.licensing.ed25519 import (
    generate_keypair,
    publickey_from_private,
    sign,
    verify,
)


def test_cryptography_ed25519_vector_parity():
    # Test vector: deterministic 32-byte seed
    seed = bytes.fromhex("9d61b19deffd5a60ba844c0f831e3600552f05a07418006112008cb372277d50")
    message = b"DrivingEvalSystem Offline Tamper Proof Licensing Test 2026"

    # Cryptography library
    crypto_priv = Ed25519PrivateKey.from_private_bytes(seed)
    crypto_pub = crypto_priv.public_key()
    crypto_pub_bytes = crypto_pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    crypto_sig = crypto_priv.sign(message)

    # ed25519 module
    mod_pub = publickey_from_private(seed)
    mod_sig = sign(message, seed)

    # 1. Public keys must be bit-for-bit identical
    assert mod_pub == crypto_pub_bytes

    # 2. Signatures must be bit-for-bit identical
    assert mod_sig == crypto_sig

    # 3. Cross-verification
    assert verify(crypto_sig, message, crypto_pub_bytes) is True
    crypto_pub.verify(mod_sig, message)  # Must not raise InvalidSignature


def test_cryptography_random_keypair_verification():
    for _ in range(5):
        priv, pub = generate_keypair()
        msg = b"Cross check random keypair payload"
        sig = sign(msg, priv)
        assert verify(sig, msg, pub) is True
        assert verify(sig, b"tampered", pub) is False
