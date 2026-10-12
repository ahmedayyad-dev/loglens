"""Best-effort redaction of sensitive values from log records.

Redaction happens in two places:

* **Keys** - any mapping value whose key looks sensitive (``password``,
  ``token``, ``authorization`` ...) is replaced with :data:`REDACTED`.
* **Patterns** - known secret shapes (bearer/basic credentials, JWTs, private
  keys, credit-card-like numbers, ``password=...`` pairs) are masked inside
  free-form strings.

It is intentionally conservative and meant as a safety net, never a guarantee.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

__all__ = ["DEFAULT_PATTERNS", "DEFAULT_SENSITIVE_KEYS", "REDACTED", "Redactor"]

REDACTED = "***"

DEFAULT_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "pwd",
        "passphrase",
        "secret",
        "clientsecret",
        "token",
        "accesstoken",
        "refreshtoken",
        "idtoken",
        "authtoken",
        "apikey",
        "authorization",
        "auth",
        "cookie",
        "setcookie",
        "session",
        "sessionid",
        "privatekey",
        "secretkey",
        "creditcard",
        "cardnumber",
        "cvv",
        "cvc",
        "ssn",
    }
)

_DEFAULT_PATTERN_SPECS: tuple[tuple[str, str], ...] = (
    (r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]+", r"\1 " + REDACTED),
    (r"(?i)\b(basic)\s+[A-Za-z0-9+/]+=*", r"\1 " + REDACTED),
    (r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b", REDACTED),
    (
        r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key)\b(\s*[:=]\s*)\S+",
        r"\1\2" + REDACTED,
    ),
    (r"\b(?:\d[ -]?){13,19}\b", REDACTED),
    (
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        REDACTED,
    ),
)

DEFAULT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.DOTALL) for pattern, _ in _DEFAULT_PATTERN_SPECS
)


def _normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


class Redactor:
    """Configurable recursive redactor.

    Args:
        sensitive_keys: extra key names to treat as sensitive, merged with the
            :data:`DEFAULT_SENSITIVE_KEYS` set.
        patterns: iterable of ``(regex, replacement)`` pairs replacing the
            default pattern set when provided. ``replacement`` may use
            ``\\1``-style backreferences.
        mask: the replacement string used for masked values.
        max_depth: recursion guard for nested containers.
    """

    def __init__(
        self,
        sensitive_keys: Iterable[str] | None = None,
        patterns: Iterable[tuple[str, str]] | None = None,
        *,
        mask: str = REDACTED,
        max_depth: int = 10,
    ) -> None:
        self.mask = mask
        self.max_depth = max_depth

        normalized = {_normalize_key(key) for key in DEFAULT_SENSITIVE_KEYS}
        if sensitive_keys is not None:
            normalized |= {_normalize_key(key) for key in sensitive_keys}
        # ``auth`` is normalised from ``authorization`` too; drop empties.
        normalized.discard("")
        self._sensitive_keys = frozenset(normalized)

        specs = _DEFAULT_PATTERN_SPECS if patterns is None else tuple(patterns)
        self._patterns = tuple(
            (re.compile(pattern, re.DOTALL), replacement) for pattern, replacement in specs
        )

    def is_sensitive_key(self, key: object) -> bool:
        """Return ``True`` when ``key`` looks like it holds a secret."""
        if not isinstance(key, str):
            return False
        normalized = _normalize_key(key)
        if not normalized:
            return False
        if normalized in self._sensitive_keys:
            return True
        return any(token in normalized for token in self._sensitive_keys)

    def redact_text(self, text: str) -> str:
        """Mask known secret shapes inside a free-form string."""
        for pattern, replacement in self._patterns:
            text = pattern.sub(replacement, text)
        return text

    def redact(self, value: Any, *, _depth: int = 0) -> Any:
        """Return a redacted copy of ``value`` (mappings/sequences recursed)."""
        if _depth > self.max_depth:
            return value
        if isinstance(value, str):
            return self.redact_text(value)
        if isinstance(value, Mapping):
            return {
                key: (
                    self.mask
                    if self.is_sensitive_key(key)
                    else self.redact(item, _depth=_depth + 1)
                )
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self.redact(item, _depth=_depth + 1) for item in value]
        if isinstance(value, tuple):
            return tuple(self.redact(item, _depth=_depth + 1) for item in value)
        if isinstance(value, (set, frozenset)):
            return {self.redact(item, _depth=_depth + 1) for item in value}
        return value
