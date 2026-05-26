def test_regression_case_passes(client):
    created = client.post(
        "/regression/cases",
        json={
            "tenant_id": "tenant-regression",
            "name": "Finance scope allows invoice summary",
            "agent_type": "business_agent",
            "requested_tool": "finance.get_invoice_summary",
            "token_scopes": ["finance:invoice:read"],
            "expected_decision": "allowed",
            "expected_reason_contains": "allowed",
        },
    )
    assert created.status_code == 201

    run = client.post("/regression/run", json={"tenant_id": "tenant-regression"})
    assert run.status_code == 200
    data = run.json()
    assert data["total_cases"] == 1
    assert data["passed"] == 1
    assert data["failed"] == 0


def test_regression_case_fails_when_expectation_is_wrong(client):
    client.post(
        "/regression/cases",
        json={
            "tenant_id": "tenant-regression",
            "name": "Missing finance scope should deny",
            "agent_type": "business_agent",
            "requested_tool": "finance.get_invoice_summary",
            "token_scopes": ["ops:report:create"],
            "expected_decision": "allowed",
            "expected_reason_contains": "allowed",
        },
    )

    run = client.post("/regression/run", json={"tenant_id": "tenant-regression"})
    assert run.status_code == 200
    assert run.json()["failed"] == 1
