def _register_approve_issue(client, scopes):
    registration = client.post(
        "/agent-auth/register",
        json={
            "tenant_id": "tenant-shared",
            "agent_name": "Scoped Tool Bot",
            "agent_type": "finance-agent",
            "requested_scopes": scopes,
            "reason": "Tool policy checks",
            "owner_user_id": "owner-6",
        },
    ).json()
    client.post(
        f"/agent-auth/approve/{registration['agent_id']}",
        json={"approved_scopes": scopes, "approved_by": "admin-3", "expires_in_hours": 8},
    )
    token = client.post("/agent-auth/token", json={"agent_id": registration["agent_id"]}).json()["access_token"]
    return registration["agent_id"], token


def test_allow_tool_call_with_correct_scope(client):
    _, token = _register_approve_issue(client, ["finance:invoice:read"])
    response = client.post(
        "/tools/finance/get_invoice_summary",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-shared"},
        json={"invoice_id": "INV-2026-010"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["scope_used"] == "finance:invoice:read"
    assert data["data"]["approver"]["email"] == "[REDACTED]"


def test_deny_tool_call_without_required_scope(client):
    _, token = _register_approve_issue(client, ["ops:report:create"])
    response = client.post(
        "/tools/finance/get_invoice_summary",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-shared"},
        json={"invoice_id": "INV-2026-011"},
    )
    assert response.status_code == 403
    assert "required scope missing from token" in response.json()["detail"]


def test_audit_log_created_for_tool_call(client):
    agent_id, token = _register_approve_issue(client, ["hr:policy:read"])
    client.post(
        "/tools/hr/search_employee_policy",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-shared"},
        json={"employee_query": "remote work"},
    )
    audit_response = client.get(f"/agent-auth/audit?agent_id={agent_id}&tool_name=hr.search_employee_policy")
    assert audit_response.status_code == 200
    logs = audit_response.json()
    assert any(log["action"] == "allowed_tool_call" for log in logs)


def test_deny_tool_call_for_tenant_mismatch(client):
    _, token = _register_approve_issue(client, ["finance:invoice:read"])
    response = client.post(
        "/tools/finance/get_invoice_summary",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-other"},
        json={"invoice_id": "INV-2026-013"},
    )
    assert response.status_code == 403
    assert "tenant" in response.json()["detail"]
