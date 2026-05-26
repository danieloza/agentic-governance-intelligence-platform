def test_deny_tool_call_after_revocation(client):
    registration = client.post(
        "/agent-auth/register",
        json={
            "tenant_id": "tenant-finance",
            "agent_name": "Revoked Bot",
            "agent_type": "finance-agent",
            "requested_scopes": ["finance:invoice:read"],
            "reason": "Revocation test",
            "owner_user_id": "owner-7",
        },
    ).json()
    client.post(
        f"/agent-auth/approve/{registration['agent_id']}",
        json={"approved_scopes": ["finance:invoice:read"], "approved_by": "admin-4", "expires_in_hours": 8},
    )
    token = client.post("/agent-auth/token", json={"agent_id": registration["agent_id"]}).json()["access_token"]
    revoke_response = client.post(
        f"/agent-auth/revoke/{registration['agent_id']}",
        json={"revoked_by": "admin-4", "reason": "Workflow disabled"},
    )
    assert revoke_response.status_code == 200

    response = client.post(
        "/tools/finance/get_invoice_summary",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-finance"},
        json={"invoice_id": "INV-2026-012"},
    )
    assert response.status_code == 403
    assert "revoked" in response.json()["detail"]
