from app.redaction import redact_pii


def test_redact_pii():
    payload = {
        "email": "person@example.com",
        "nested": {"phone": "+48 123 456 789", "salary": 20000},
        "items": [{"bank_account": "123"}, {"ok": "value"}],
    }
    result = redact_pii(payload)
    assert result["email"] == "[REDACTED]"
    assert result["nested"]["phone"] == "[REDACTED]"
    assert result["nested"]["salary"] == "[REDACTED]"
    assert result["items"][0]["bank_account"] == "[REDACTED]"
    assert result["items"][1]["ok"] == "value"

