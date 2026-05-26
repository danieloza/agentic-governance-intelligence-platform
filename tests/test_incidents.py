def _register_approve_issue(client, scopes):
    registration = client.post(
        "/agent-auth/register",
        json={
            "tenant_id": "tenant-incidents",
            "agent_name": "Incident Agent",
            "agent_type": "business_agent",
            "requested_scopes": scopes,
            "reason": "Incident creation test",
            "owner_user_id": "owner-incidents",
        },
    ).json()
    client.post(
        f"/agent-auth/approve/{registration['agent_id']}",
        json={"approved_scopes": scopes, "approved_by": "admin-incidents", "expires_in_hours": 8},
    )
    token = client.post("/agent-auth/token", json={"agent_id": registration["agent_id"]}).json()["access_token"]
    return token


def test_denied_tool_call_creates_incident(client):
    token = _register_approve_issue(client, ["ops:report:create"])

    denied = client.post(
        "/tools/finance/get_invoice_summary",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-incidents"},
        json={"invoice_id": "INV-INC-001"},
    )
    assert denied.status_code == 403

    incidents = client.get("/incidents?tenant_id=tenant-incidents")
    assert incidents.status_code == 200
    rows = incidents.json()
    assert len(rows) == 1
    assert rows[0]["status"] == "open"
    assert "Denied tool call" in rows[0]["title"]


def test_resolve_incident(client):
    token = _register_approve_issue(client, ["ops:report:create"])
    client.post(
        "/tools/finance/get_invoice_summary",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-incidents"},
        json={"invoice_id": "INV-INC-002"},
    )
    incident_id = client.get("/incidents").json()[0]["id"]

    resolved = client.post(
        f"/incidents/{incident_id}/resolve",
        json={"resolved_by": "operator", "resolution_note": "Scope issue reviewed"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
