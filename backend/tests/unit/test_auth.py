""" Unit tests for ``services.auth`` cryptographic helpers. """

from __future__ import annotations

from services.auth import (
    BCRYPT_MAX_BYTES,
    hash_password,
    hash_token,
    to_bcrypt_bytes,
    verify_password,
)


def test_hash_password_round_trips_via_verify():
    """A password hashed with ``hash_password`` verifies against the same plaintext 
    via ``verify_password``. Bcrypt's salt is randomized, so calling hash twice on 
    the same input yields different digests."""

    plain = "TestPass!23"
    h1 = hash_password(plain)
    h2 = hash_password(plain)
    assert h1 != h2 
    assert verify_password(plain, h1)
    assert verify_password(plain, h2)


def test_verify_password_rejects_wrong_password():
    """Wrong plaintext against a valid hash returns False, not True and
    not an exception."""

    h = hash_password("CorrectHorseBatteryStaple")
    assert verify_password("definitely-not-it", h) is False


def test_verify_password_handles_none_hash():
    """``verify_password`` is called with ``hashed=None``. 
    Must return False, not crash."""

    assert verify_password("anything", None) is False


def test_verify_password_handles_malformed_hash():
    """ Given a garbage hash, ``verify_password`` must return False and
    gracefully handle the bcrypt exception."""

    assert verify_password("anything", "not-a-real-bcrypt-hash") is False


def test_to_bcrypt_bytes_truncates_to_72_bytes():
    """ Ensuring that ``to_bcrypt_bytes`` truncates to 72 bytes to
    respect bcrypt hard 72-byte input limit."""

    assert BCRYPT_MAX_BYTES == 72
    assert to_bcrypt_bytes("hello") == b"hello"
    assert to_bcrypt_bytes("a" * 100) == b"a" * 72
    #  edge case (exactly at the limit) is preserved unchanged.
    assert to_bcrypt_bytes("x" * 72) == b"x" * 72


def test_two_passwords_sharing_72_byte_prefix_are_equivalent():
    """Direct consequence of the truncation contract: two passwords that
    differ only after byte 72 hash to the same digest — i.e. they're
    indistinguishable to bcrypt. Documents the security limit explicitly
    so a future change to the truncation behaviour breaks here loudly."""

    short = "a" * 72
    long_with_same_prefix = ("a" * 72) + "extra-suffix-content"
    h = hash_password(short)
    assert verify_password(long_with_same_prefix, h)


def test_hash_token_is_deterministic_sha256():
    """``hash_token`` is a sha256 hex digest — same input, same output,
    every time."""

    out1 = hash_token("some-raw-token")
    out2 = hash_token("some-raw-token")
    assert out1 == out2
    # sha256 produces a 64-char hex string.
    assert len(out1) == 64
    assert all(c in "0123456789abcdef" for c in out1)


def test_hash_token_distinguishes_different_inputs():
    """Distinct inputs produce distinct digests."""
    
    assert hash_token("token-a") != hash_token("token-b")
