"""Redaction of sensitive values."""

from __future__ import annotations

from loglens.redaction import Redactor


def test_masks_known_keys() -> None:
    redactor = Redactor()
    result = redactor.redact({"password": "my secret", "user": "alice"})
    assert result == {"password": "***", "user": "alice"}


def test_masks_nested_structures() -> None:
    redactor = Redactor()
    payload = {
        "user": {"email": "a@b.c"},
        "request": {"headers": {"authorization": "Bearer xyz", "counter": 3}},
    }
    result = redactor.redact(payload)
    assert result["request"]["headers"]["authorization"] == "***"
    assert result["request"]["headers"]["counter"] == 3
    assert result["user"]["email"] == "a@b.c"


def test_masks_lists_and_tuples() -> None:
    redactor = Redactor()
    assert redactor.redact([{"token": "x"}, "plain"]) == [{"token": "***"}, "plain"]
    assert redactor.redact(("x", {"token": "y"})) == ("x", {"token": "***"})


def test_does_not_mutate_input() -> None:
    original = {"password": "secret"}
    snapshot = dict(original)
    Redactor().redact(original)
    assert original == snapshot


def test_custom_sensitive_keys() -> None:
    redactor = Redactor(sensitive_keys=["my_secret_field"])
    assert redactor.is_sensitive_key("my-secret-field")
    assert redactor.redact({"my_secret_field": 1}) == {"my_secret_field": "***"}


def test_bearer_token_in_text() -> None:
    redactor = Redactor()
    masked = redactor.redact_text("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.token.signature")
    assert "eyJhbGciOiJIUzI1NiJ9" not in masked


def test_key_value_leak_in_text() -> None:
    redactor = Redactor()
    masked = redactor.redact_text("password=hunter2")
    assert "***" in masked
    assert "hunter2" not in masked


def test_private_key_block() -> None:
    redactor = Redactor()
    key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n-----END RSA PRIVATE KEY-----"
    masked = redactor.redact_text(key)
    assert "MIIEowIBAAKCAQEA" not in masked


def test_scalars_left_intact() -> None:
    redactor = Redactor()
    assert redactor.redact(42) == 42
    assert redactor.redact(3.4) == 3.4
    assert redactor.redact(b"bytes") == b"bytes"
    assert redactor.redact(None) is None