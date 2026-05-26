from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.config import get_settings


BASE_SENSITIVE_KEYS = {
    "email",
    "phone",
    "personal_id",
    "pesel",
    "salary",
    "bank_account",
    "address",
    "api_key",
    "access_token",
    "secret",
    "password",
    "authorization",
}


def redact_pii(data: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    sensitive_keys = set(BASE_SENSITIVE_KEYS)
    if settings.redact_full_name:
        sensitive_keys.add("full_name")

    def _redact(value: Any) -> Any:
        if isinstance(value, Mapping):
            redacted: dict[str, Any] = {}
            for key, inner_value in value.items():
                lowered = key.lower()
                if lowered in sensitive_keys:
                    redacted[key] = "[REDACTED]"
                else:
                    redacted[key] = _redact(inner_value)
            return redacted
        if isinstance(value, list):
            return [_redact(item) for item in value]
        return value

    return _redact(data)
