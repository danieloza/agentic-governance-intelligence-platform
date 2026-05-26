def test_enterprise_layers_are_exposed(client):
    response = client.get("/enterprise/layers")

    assert response.status_code == 200
    payload = response.json()
    keys = {layer["key"] for layer in payload["layers"]}
    assert "policy-simulation-studio" in keys
    assert "agent-memory-governance" in keys
    assert "sandbox-execution-layer" in keys
    assert "context-governance-layer" in keys
    assert payload["summary"]["total_layers"] == 10


def test_policy_simulation_denies_missing_scope(client):
    register = client.post(
        "/agent-auth/register",
        json={
            "tenant_id": "enterprise-sim",
            "agent_name": "Simulation Agent",
            "agent_type": "workflow_agent",
            "requested_scopes": ["finance:invoice:read"],
            "reason": "Dry-run policy checks before rollout",
            "owner_user_id": "operator",
        },
    )
    agent_id = register.json()["agent_id"]
    client.post(
        f"/agent-auth/approve/{agent_id}",
        json={"approved_scopes": ["finance:invoice:read"], "approved_by": "admin", "expires_in_hours": 4},
    )

    response = client.post(
        "/enterprise/policy/simulate",
        json={
            "agent_id": agent_id,
            "tenant_id": "enterprise-sim",
            "tool_name": "finance.get_invoice_summary",
            "token_scopes": [],
            "dry_run": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "denied"
    assert payload["required_scope"] == "finance:invoice:read"
    assert "add scope" in payload["approval_preview"]


def test_policy_simulation_allows_approved_scope(client):
    register = client.post(
        "/agent-auth/register",
        json={
            "tenant_id": "enterprise-sim-allowed",
            "agent_name": "Allowed Simulation Agent",
            "agent_type": "workflow_agent",
            "requested_scopes": ["hr:policy:read"],
            "reason": "Dry-run allowed policy checks",
            "owner_user_id": "operator",
        },
    )
    agent_id = register.json()["agent_id"]
    client.post(
        f"/agent-auth/approve/{agent_id}",
        json={"approved_scopes": ["hr:policy:read"], "approved_by": "admin", "expires_in_hours": 4},
    )

    response = client.post(
        "/enterprise/policy/simulate",
        json={
            "agent_id": agent_id,
            "tenant_id": "enterprise-sim-allowed",
            "tool_name": "hr.search_employee_policy",
            "token_scopes": ["hr:policy:read"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "allowed"
    assert payload["blast_radius"]["affected_tool"] == "hr.search_employee_policy"
